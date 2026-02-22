import asyncio
import logging
import os
import subprocess
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy.orm import Session
from ..database import get_db_context
from ..models.user import User, UserStatus, ConnectionLog
from ..services.openvpn_mgmt import openvpn_mgmt

logger = logging.getLogger(__name__)

class TrafficMonitor:
    """
    Background service to monitor VPN traffic (OpenVPN)
    and enforce user limits (Data & Expiry).
    """
    
    OPENVPN_STATUS_LOG = "/var/log/openvpn/openvpn-status.log"
    OPENVPN_LOG = "/var/log/openvpn/openvpn.log"
    SYNC_INTERVAL = 60  # seconds

    def __init__(self):
        self.running = False
        # Cache to track last seen bytes for delta calculation
        # Format: { "username_protocol": { "rx": int, "tx": int } }
        self._traffic_cache: Dict[str, Dict[str, int]] = {}
        
        # Track active sessions for connection logging
        # Format: { "username_protocol": { "start_time": datetime, "ip": str, "last_seen": datetime } }
        self._active_sessions: Dict[str, Dict] = {}

    async def start(self):
        """Start the monitoring loop"""
        if self.running:
            return
        
        self.running = True
        logger.info("🚀 Traffic Monitor started")
        
        while self.running:
            try:
                await self.sync_traffic()
            except Exception as e:
                logger.error(f"Error in traffic sync loop: {e}")
            
            await asyncio.sleep(self.SYNC_INTERVAL)

    async def stop(self):
        """Stop the monitoring loop"""
        self.running = False
        logger.info("🛑 Traffic Monitor stopped")

    async def sync_traffic(self):
        """Main synchronization logic"""
        # 1. Gather stats from OpenVPN
        # F1: Try Management Interface first
        ovpn_stats = {}
        if openvpn_mgmt.is_available():
            try:
                mgmt_conns = openvpn_mgmt.get_active_connections()
                for conn in mgmt_conns:
                    # Map mgmt format to our stats format
                    # { "username": { "rx": bytes, "tx": bytes, "ip": str } }
                    if conn['username'] == "UNDEF": continue
                    ovpn_stats[conn['username']] = {
                        "rx": conn['bytes_rx'],
                        "tx": conn['bytes_tx'],
                        "ip": conn['real_ip']
                    }
            except Exception as e:
                logger.error(f"Mgmt sync failed: {e}")
                
        # Fallback to Status Log if Mgmt failed or returned empty (and log exists)
        if not ovpn_stats:
            ovpn_stats = self._parse_openvpn_status()
        
        # 2. Update Database
        with get_db_context() as db:
            # NOTE: Lite edition does not have a DELETED state in UserStatus.
            # Querying all users avoids AttributeError("DELETED") and keeps the
            # monitor resilient across schema changes.
            users = db.query(User).all()
            
            # Set of current active sessions in this cycle (username_protocol)
            current_active_keys = set()

            for user in users:
                # --- OpenVPN Traffic ---
                if user.username in ovpn_stats:
                    self._update_usage(db, user, "openvpn", ovpn_stats[user.username])
                    self._handle_connection_status(db, user, "openvpn", ovpn_stats[user.username]['ip'])
                    current_active_keys.add(f"{user.username}_openvpn")

                # --- Check Limits (Data & Expiry) ---
                self._check_limits(db, user)

            # 3. Detect Disconnections
            # Any session in _active_sessions NOT in current_active_keys has disconnected
            for session_key in list(self._active_sessions.keys()):
                if session_key not in current_active_keys:
                    # Mark as disconnected
                    self._log_disconnection(db, session_key)

            db.commit()

    def _parse_openvpn_status(self) -> Dict[str, Dict]:
        """
        Parse OpenVPN status log (Supports Version 1 and 2).
        Returns: { "username": { "rx": bytes, "tx": bytes, "ip": str } }
        """
        stats = {}
        if not os.path.exists(self.OPENVPN_STATUS_LOG):
            return stats
            
        try:
            with open(self.OPENVPN_STATUS_LOG, 'r') as f:
                content = f.read()
                
            lines = content.splitlines()
            
            # Version 2 Parser (Comma separated, starts with HEADER/CLIENT_LIST)
            # HEADER,CLIENT_LIST,Common Name,Real Address,Virtual Address,Bytes Received,Bytes Sent,Connected Since,Connected Since (time_t),Username,Client ID,Peer ID
            # CLIENT_LIST,user1,1.2.3.4:1234,10.8.0.2,1000,2000,...
            
            is_v2 = any("CLIENT_LIST" in line for line in lines[:5])
            
            for line in lines:
                parts = line.split(',')
                
                if is_v2:
                    if line.startswith("CLIENT_LIST") and "Common Name" not in line:
                         # parts[1]=username (Common Name), parts[2]=real_addr
                         # parts[5]=bytes_rx, parts[6]=bytes_tx
                         if len(parts) > 6:
                             try:
                                 username = parts[1]
                                 if username == "UNDEF": continue
                                 stats[username] = {
                                     "rx": int(parts[5] or 0),
                                     "tx": int(parts[6] or 0),
                                     "ip": parts[2].split(':')[0]
                                 }
                             except (ValueError, IndexError):
                                 continue
                else:
                    # Version 1 Parser (Comma separated, Header: Common Name,...)
                    # Common Name,Real Address,Bytes Received,Bytes Sent,Connected Since
                    parts = line.split(',')
                    if len(parts) < 5 or parts[0] == "Common Name" or parts[0] == "ROUTING_TABLE":
                        continue
                    
                    try:
                        username = parts[0]
                        if username == "UNDEF": continue
                        stats[username] = {
                            "rx": int(parts[2]),
                            "tx": int(parts[3]),
                            "ip": parts[1].split(':')[0]
                        }
                    except (ValueError, IndexError):
                        continue
                        
        except Exception as e:
            logger.error(f"Failed to parse OpenVPN status: {e}")
            
        return stats

    def _update_usage(self, db: Session, user: User, protocol: str, current_stats: Dict):
        """
        Calculate delta and update user totals.
        Handles counter resets (server restart).
        """
        cache_key = f"{user.username}_{protocol}"
        last_stats = self._traffic_cache.get(cache_key, {"rx": 0, "tx": 0})
        
        # Calculate Deltas
        # OpenVPN stats are cumulative counters.
        curr_rx = current_stats["rx"]
        curr_tx = current_stats["tx"]
        
        last_rx = last_stats["rx"]
        last_tx = last_stats["tx"]
        
        delta_rx = 0
        delta_tx = 0
        
        if curr_rx >= last_rx:
            delta_rx = curr_rx - last_rx
        else:
            # Counter reset (service restarted)
            delta_rx = curr_rx
            
        if curr_tx >= last_tx:
            delta_tx = curr_tx - last_tx
        else:
            # Counter reset
            delta_tx = curr_tx
            
        # Update DB if there is traffic
        if delta_rx > 0 or delta_tx > 0:
            user.total_upload_bytes += delta_rx
            user.total_download_bytes += delta_tx
            # We don't commit here, outer loop does
            
        # Update Cache
        self._traffic_cache[cache_key] = {"rx": curr_rx, "tx": curr_tx}
        
    def _handle_connection_status(self, db: Session, user: User, protocol: str, ip: str):
        """Handle Log On event and update Active Sessions"""
        session_key = f"{user.username}_{protocol}"
        
        if session_key not in self._active_sessions:
            # New Connection detected
            logger.info(f"User {user.username} connected via {protocol} from {ip}")
            
            # Log to DB
            log = ConnectionLog(
                user_id=user.id,
                protocol=protocol, # openvpn
                client_ip=ip, # Fixed: ip_address -> client_ip
                connected_at=datetime.utcnow()
            )
            db.add(log)
            # We need to flush to get the ID if we wanted to update it later, 
            # but for now we just log start. We can log duration on disconnect.
            
            # Update User last_connection
            user.last_connection = datetime.utcnow()
            
            # Add to local active sessions
            self._active_sessions[session_key] = {
                "start_time": datetime.utcnow(),
                "ip": ip,
                "user_id": user.id
            }
        else:
            # Existing connection, just update heartbeat/last_seen locally if needed
            user.last_connection = datetime.utcnow()

    def _log_disconnection(self, db: Session, session_key: str):
        """Handle Disconnect event"""
        if session_key in self._active_sessions:
            session_data = self._active_sessions.pop(session_key)
            username = session_key.split('_')[0]
            
            logger.info(f"User {username} disconnected (Session duration: {datetime.utcnow() - session_data['start_time']})")
            
            # In a more advanced system, we might update the specific ConnectionLog entry with 'disconnected_at'
            # For now, we just remove it from active tracking. 
            # If we want to log disconnection time, we'd need to fetch the last log entry or keep track of Log ID.
            # Let's keep it simple for now: We have the 'connected_at' log.
            # We could add a "Disconnection" log or update the existing one.
            # Updating is better for clean history.
            
            try:
                # Find the latest open connection log for this user/protocol
                last_log = db.query(ConnectionLog).filter(
                    ConnectionLog.user_id == session_data['user_id'],
                    ConnectionLog.protocol == session_key.split('_')[1],
                    ConnectionLog.disconnected_at == None
                ).order_by(ConnectionLog.connected_at.desc()).first()
                
                if last_log:
                    last_log.disconnected_at = datetime.utcnow()
            except Exception as e:
                logger.error(f"Error updating disconnect log: {e}")

    def parse_openvpn_log_events(self):
        """Parse connect/disconnect events from OpenVPN log (F8)"""
        import re
        if not os.path.exists(self.OPENVPN_LOG):
            return

        # Regex patterns
        # DST 12-13 10:00:00 ... or Dec 13 10:00:00 ...
        # Matching: (Timestamp) (Hostname/IP) (Event) (VirtualIP)
        # Example: Dec 13 10:00:00 server/1.2.3.4:1234 MULTI: Learn: 10.8.0.2
        connect_pattern = re.compile(
            r"^([A-Z][a-z]{2} +\d+ \d+:\d+:\d+|\d+-\d+-\d+ \d+:\d+:\d+) " # Timestamp
            r".*?(\S+)/(\d+\.\d+\.\d+\.\d+):\d+ " # Username / RealIP
            r"MULTI: Learn: (\d+\.\d+\.\d+\.\d+)" # VPN IP
        )

        try:
            # Efficiently read last 1000 lines to catch recent events without full scan
            # In production, use file seeking/state persistence.
            lines = []
            with open(self.OPENVPN_LOG, "r") as f:
                # Simple tail
                for line in f:
                    lines.append(line)
                lines = lines[-1000:] # Last 1000 lines

            for line in lines:
                # New Connection
                m = connect_pattern.search(line)
                if m:
                    ts_str, username, real_ip, vpn_ip = m.groups()
                    self._record_connection(username, real_ip, vpn_ip, ts_str)

        except Exception as e:
            logger.error(f"Log parser error: {e}")

    def _record_connection(self, username: str, real_ip: str, vpn_ip: str, ts_str: str):
        """Record connection from log if not exists (F8)"""
        if username == "UNDEF": return
        
        with get_db_context() as db:
            user = db.query(User).filter(User.username == username).first()
            if not user:
                return

            # Parse Timestamp (Assume current year, handle rollover)
            try:
                # Try standard syslog format: Dec 13 10:00:00
                dt = datetime.strptime(ts_str, "%b %d %H:%M:%S")
                now = datetime.now()
                dt = dt.replace(year=now.year)
                if dt > now: # Future? Must be last year (Dec in Jan)
                    dt = dt.replace(year=now.year - 1)
            except ValueError:
                # Fallback or other formats
                dt = datetime.utcnow()

            # Duplicate Check:
            # Check if we have a log for this user within tight window (e.g. 5 sec)
            exists = db.query(ConnectionLog).filter(
                ConnectionLog.user_id == user.id,
                ConnectionLog.protocol == "openvpn",
                ConnectionLog.connected_at >= dt - timedelta(seconds=5),
                ConnectionLog.connected_at <= dt + timedelta(seconds=5)
            ).first()

            if not exists:
                log = ConnectionLog(
                    user_id=user.id,
                    protocol="openvpn",
                    client_ip=real_ip,
                    connected_at=dt,
                    server_ip=vpn_ip # Using server_ip column for VPN IP temporarily or extend model
                )
                db.add(log)
                user.last_connection = dt
                db.commit()

    def _check_limits(self, db: Session, user: User):
        """Check Data Limit and Expiry"""
        if user.status != UserStatus.ACTIVE:
            return

        modified = False
        
        # 1. Check Expiry
        if user.expiry_date and datetime.utcnow() > user.expiry_date:
            logger.info(f"User {user.username} expired. Disabling...")
            user.status = UserStatus.EXPIRED
            modified = True
            
        # 2. Check Data Limit
        # data_limit_gb is float. 0 means unlimited.
        if user.data_limit_gb > 0:
            if user.data_usage_gb >= user.data_limit_gb:
                logger.info(f"User {user.username} exceeded data limit. Disabling...")
                user.status = UserStatus.SUSPENDED
                modified = True
                
        if modified:
            # Terminate connections if possible (Optional enhancement)
            # For now, just marking as suspended will prevent new auths
            # But existing connections might persist until re-auth.
            pass

traffic_monitor = TrafficMonitor()
