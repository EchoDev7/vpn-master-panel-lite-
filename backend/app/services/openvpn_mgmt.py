import socket
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class OpenVPNManagementService:
    def __init__(self, host="127.0.0.1", port=7505):
        self.host = host
        self.port = port

    def _send_command(self, cmd: str) -> str:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(3)
                s.connect((self.host, self.port))
                
                # Consume banner
                s.recv(1024) 
                
                s.sendall(f"{cmd}\n".encode())
                resp = b""
                while True:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    resp += chunk
                    if b"END" in resp or b"SUCCESS" in resp or b"ERROR" in resp:
                        break
                s.sendall(b"quit\n")
                return resp.decode(errors="ignore")
        except ConnectionRefusedError:
            # logger.warning(f"Management interface not reachable at {self.host}:{self.port}")
            return ""
        except Exception as e:
            logger.error(f"Management socket error: {e}")
            return ""

    def get_active_connections(self) -> List[Dict]:
        """Real-time list of connected users"""
        try:
            raw = self._send_command("status 2")
            connections = []
            if not raw:
                return []
                
            for line in raw.split("\n"):
                if line.startswith("CLIENT_LIST,") and "Common Name" not in line:
                    parts = line.split(",")
                    if len(parts) >= 8:
                        # Format: CLIENT_LIST,CommonName,RealAddress,VirtualAddress,BytesReceived,BytesSent,ConnectedSince,ConnectedSince(time_t),Username
                        connections.append({
                            "username": parts[1],
                            "real_ip": parts[2].split(":")[0],
                            "vpn_ip": parts[3],
                            "bytes_rx": int(parts[5] or 0),
                            "bytes_tx": int(parts[6] or 0),
                            "connected_since": parts[7],
                        })
            return connections
        except Exception as e:
            logger.error(f"Error parsing management status: {e}")
            return []

    def kill_session(self, username: str) -> bool:
        """Disconnect a specific user"""
        try:
            resp = self._send_command(f"kill {username}")
            return "SUCCESS" in resp
        except Exception as e:
            logger.error(f"Kill session error: {e}")
            return False

    def is_available(self) -> bool:
        try:
            resp = self._send_command("bytecount 1")
            return bool(resp)
        except:
            return False

# Singleton instance
openvpn_mgmt = OpenVPNManagementService()
