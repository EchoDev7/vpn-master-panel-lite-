import asyncio
import logging
import os
import subprocess
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy.orm import Session
from ..database import get_db_context
from ..models.user import User, UserStatus
from ..services.wireguard import wireguard_service

logger = logging.getLogger(__name__)

class TrafficMonitor:
    """
    Background service to monitor VPN traffic (OpenVPN & WireGuard)
    and enforce user limits (Data & Expiry).
    """
    
    OPENVPN_STATUS_LOG = "/var/log/openvpn/openvpn-status.log"
    SYNC_INTERVAL = 60  # seconds

    def __init__(self):
        self.running = False
        # Cache to track last seen bytes for delta calculation
        # Format: { "username_protocol": { "rx": int, "tx": int } }
        self._traffic_cache: Dict[str, Dict[str, int]] = {}
        self._online_users: Dict[str, datetime] = {} # username -> last_seen

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
        # 1. Gather stats from OpenVPN & WireGuard
        ovpn_stats = self._parse_openvpn_status()
        wg_stats = self._parse_wireguard_stats()
        
        # 2. Update Database
        with get_db_context() as db:
            users = db.query(User).filter(User.status != UserStatus.DELETED).all()
            
            for user in users:
                # --- OpenVPN Traffic ---
                if user.username in ovpn_stats:
                    self._update_usage(db, user, "openvpn", ovpn_stats[user.username])
                    self._mark_online(user)
                
                # --- WireGuard Traffic ---
                # Check by Public Key
                if user.wireguard_public_key and user.wireguard_public_key in wg_stats:
                    self._update_usage(db, user, "wireguard", wg_stats[user.wireguard_public_key])
                    # WireGuard is stateless, check latest handshake for "online" status
                    if wg_stats[user.wireguard_public_key].get('is_online'):
                        self._mark_online(user)

                # --- Check Limits (Data & Expiry) ---
                self._check_limits(db, user)

            db.commit()

    def _parse_openvpn_status(self) -> Dict[str, Dict[str, int]]:
        """
        Parse OpenVPN status log.
        Returns: { "username": { "rx": bytes, "tx": bytes } }
        """
        stats = {}
        if not os.path.exists(self.OPENVPN_STATUS_LOG):
            return stats
            
        try:
            with open(self.OPENVPN_STATUS_LOG, 'r') as f:
                content = f.read()
                
            # Parse CLIENT_LIST
            # Common Name,Real Address,Bytes Received,Bytes Sent,Connected Since
            lines = content.split('\n')
            for line in lines:
                parts = line.split(',')
                if len(lines) < 5 or parts[0] == "Common Name":
                    continue
                
                if parts[0] == "ROUTING_TABLE":
                    break
                    
                username = parts[0]
                try:
                    stats[username] = {
                        "rx": int(parts[2]), # Bytes Received by Server (Upload from User)
                        "tx": int(parts[3])  # Bytes Sent by Server (Download to User)
                    }
                except (ValueError, IndexError):
                    continue
        except Exception as e:
            logger.error(f"Failed to parse OpenVPN status: {e}")
            
        return stats

    def _parse_wireguard_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Parse WireGuard stats from `wg show`.
        Returns: { "public_key": { "rx": bytes, "tx": bytes, "is_online": bool } }
        """
        stats = {}
        try:
            # We can use the existing service to get raw stats
            status = wireguard_service.get_interface_status()
            if not status.get("running"):
                return stats
                
            for peer in status.get("peers", []):
                stats[peer["public_key"]] = {
                    "rx": peer["transfer_rx"], # Received by Interface (Upload from User)
                    "tx": peer["transfer_tx"], # Sent by Interface (Download to User)
                    "is_online": peer.get("is_online", False)
                }
        except Exception as e:
            logger.error(f"Failed to parse WireGuard stats: {e}")
            
        return stats

    def _update_usage(self, db: Session, user: User, protocol: str, current_stats: Dict[str, int]):
        """
        Calculate delta and update user totals.
        Handles counter resets (server restart).
        """
        cache_key = f"{user.username}_{protocol}"
        last_stats = self._traffic_cache.get(cache_key, {"rx": 0, "tx": 0})
        
        # Calculate Deltas
        # OpenVPN/WG stats are cumulative counters.
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
        
    def _mark_online(self, user: User):
        """Update last_connection timestamp"""
        user.last_connection = datetime.utcnow()

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
