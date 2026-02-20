"""
OpenVPN Management Interface Client
====================================
Communicates with the OpenVPN management socket (TCP 127.0.0.1:7505).

Status v2 CLIENT_LIST column layout (0-indexed):
  0  CLIENT_LIST
  1  Common Name            ← cert CN (= username when username-as-common-name)
  2  Real Address           ← client_ip:port
  3  Virtual Address        ← VPN IP (IPv4)
  4  Virtual IPv6 Address   ← may be empty
  5  Bytes Received
  6  Bytes Sent
  7  Connected Since        ← human readable
  8  Connected Since (time_t)
  9  Username               ← auth-user-pass name (same as CN with u-a-c-n)
 10  Client ID
 11  Peer ID
 12  Data Channel Cipher    ← OpenVPN 2.5+ optional
"""
import socket
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class OpenVPNManagementService:
    def __init__(self, host: str = "127.0.0.1", port: int = 7505):
        self.host = host
        self.port = port

    # ------------------------------------------------------------------
    # Low-level socket command
    # ------------------------------------------------------------------

    def _send_command(self, cmd: str) -> str:
        """Send a single management command and return the full response."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((self.host, self.port))

                # Consume the welcome banner (">INFO:..." line)
                s.recv(1024)

                s.sendall(f"{cmd}\n".encode())

                resp = b""
                while True:
                    chunk = s.recv(8192)
                    if not chunk:
                        break
                    resp += chunk
                    # Management protocol terminates responses with END, SUCCESS or ERROR
                    decoded = resp.decode(errors="ignore")
                    if "\nEND" in decoded or "SUCCESS:" in decoded or "ERROR:" in decoded:
                        break

                # Politely close the session
                try:
                    s.sendall(b"quit\n")
                except OSError:
                    pass

                return resp.decode(errors="ignore")

        except ConnectionRefusedError:
            # Management interface not running — silent, checked via is_available()
            return ""
        except socket.timeout:
            logger.warning("Management socket timed out")
            return ""
        except Exception as exc:
            logger.error(f"Management socket error: {exc}")
            return ""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_active_connections(self) -> List[Dict]:
        """
        Return list of currently connected clients.

        Each dict contains:
          username, common_name, real_ip, real_port,
          vpn_ip, bytes_rx, bytes_tx, connected_since
        """
        raw = self._send_command("status 2")
        connections: List[Dict] = []
        if not raw:
            return []

        for line in raw.splitlines():
            if not line.startswith("CLIENT_LIST,"):
                continue
            # Skip the header row OpenVPN emits
            if "Common Name" in line:
                continue

            parts = line.split(",")
            # Need at least columns 0–8 (9 fields minimum)
            if len(parts) < 9:
                continue

            common_name = parts[1].strip()
            if common_name in ("", "UNDEF"):
                continue

            try:
                real_addr   = parts[2].strip()
                vpn_ip      = parts[3].strip()
                bytes_rx    = int(parts[5] or 0)
                bytes_tx    = int(parts[6] or 0)
                conn_since  = parts[7].strip()
                # Prefer the auth username (col 9); fall back to Common Name
                username    = (
                    parts[9].strip()
                    if len(parts) > 9 and parts[9].strip()
                    else common_name
                )

                connections.append({
                    "username":        username,
                    "common_name":     common_name,
                    "real_ip":         real_addr.rsplit(":", 1)[0],  # strip port (IPv6-safe)
                    "real_port":       real_addr.rsplit(":", 1)[1] if ":" in real_addr else "",
                    "vpn_ip":          vpn_ip,
                    "bytes_rx":        bytes_rx,
                    "bytes_tx":        bytes_tx,
                    "connected_since": conn_since,
                })
            except (ValueError, IndexError) as err:
                logger.debug(f"Skipping malformed CLIENT_LIST line ({err}): {line!r}")

        return connections

    def kill_session(self, username: str) -> bool:
        """
        Disconnect a user by Common Name (which equals username when
        username-as-common-name is set on the server).
        """
        try:
            resp = self._send_command(f"kill {username}")
            success = "SUCCESS:" in resp
            if not success:
                logger.warning(f"Kill session for {username!r} returned: {resp.strip()!r}")
            return success
        except Exception as exc:
            logger.error(f"Kill session error: {exc}")
            return False

    def is_available(self) -> bool:
        """Check if the management interface is reachable."""
        try:
            resp = self._send_command("version")
            return bool(resp and "OpenVPN" in resp)
        except Exception:
            return False


# Module-level singleton
openvpn_mgmt = OpenVPNManagementService()
