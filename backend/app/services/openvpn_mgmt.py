import asyncio
import socket
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class OpenVPNManagementService:
    def __init__(self, host='127.0.0.1', port=7505):
        self.host = host
        self.port = port

    def _send_command(self, cmd: str) -> str:
        """Send a command to the OpenVPN management interface via raw TCP socket."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(3)
                s.connect((self.host, self.port))
                
                # Receive banner
                s.recv(1024) 
                
                # Send command
                s.sendall(f'{cmd}\n'.encode())
                
                resp = b''
                while True:
                    chunk = s.recv(4096)
                    if not chunk: break
                    resp += chunk
                    if b'END' in resp or b'SUCCESS' in resp: break
                    
                s.sendall(b'quit\n')
                return resp.decode(errors='ignore')
        except ConnectionRefusedError:
            logger.error(f"Could not connect to OpenVPN Management Interface at {self.host}:{self.port}")
            return ""
        except Exception as e:
            logger.error(f"OpenVPN Management Interface Error: {e}")
            return ""

    def get_active_connections(self) -> List[Dict]:
        """
        Get real-time list of connected users using 'status 2' command.
        Parses the machine-readable output.
        """
        raw = self._send_command('status 2')
        if not raw:
            return []

        connections = []
        # Format of status 2:
        # HEADER,CLIENT_LIST,Common Name,Real Address,Virtual Address,Bytes Received,Bytes Sent,Connected Since,Connected Since (time_t),Username,Client ID,Peer ID
        # CLIENT_LIST,user1,1.2.3.4:1234,10.8.0.2,1000,2000,2023-01-01 00:00:00,1672531200,user1,0,0
        
        for line in raw.splitlines():
            if line.startswith('CLIENT_LIST'):
                parts = line.split(',')
                if len(parts) > 8:
                    try:
                        conn = {
                            "common_name": parts[1],
                            "real_address": parts[2],
                            "virtual_address": parts[3],
                            "bytes_received": int(parts[4]),
                            "bytes_sent": int(parts[5]),
                            "connected_since": parts[6],
                            "connected_timestamp": int(parts[7]),
                            "username": parts[8] if len(parts) > 8 else parts[1],
                            "client_id": parts[9] if len(parts) > 9 else None
                        }
                        connections.append(conn)
                    except (ValueError, IndexError):
                        continue
                        
        return connections

    def kill_client(self, common_name: str) -> bool:
        """Kill a specific client connection"""
        resp = self._send_command(f'kill {common_name}')
        return "SUCCESS" in resp

openvpn_mgmt = OpenVPNManagementService()
