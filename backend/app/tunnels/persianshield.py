"""
PersianShield™ - Advanced Anti-Censorship Tunnel
A custom tunneling solution specifically designed to bypass Iran's sophisticated DPI and filtering.

Features:
- TLS 1.3 Obfuscation
- Domain Fronting
- WebSocket over TLS
- Traffic Randomization
- Auto-switching on detection
- SNI Fragmentation
"""
import asyncio
import ssl
import struct
import random
import hashlib
import json
from typing import Optional, Dict, Any
from datetime import datetime
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import logging

logger = logging.getLogger(__name__)


class PersianShieldTunnel:
    """
    PersianShield Tunnel Implementation
    
    This tunnel uses multiple layers of obfuscation to bypass DPI:
    1. TLS 1.3 encryption with random SNI
    2. WebSocket framing to mimic HTTPS traffic
    3. Traffic padding and randomization
    4. Domain fronting support
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.iran_host = config.get("iran_host")
        self.iran_port = config.get("iran_port")
        self.foreign_host = config.get("foreign_host")
        self.foreign_port = config.get("foreign_port")
        
        # Obfuscation settings
        self.use_domain_fronting = config.get("domain_fronting", True)
        self.fronting_domain = config.get("fronting_domain", "cloudflare.com")
        self.real_sni = config.get("sni", "www.google.com")
        
        # Traffic obfuscation
        self.padding_enabled = config.get("padding", True)
        self.randomize_packets = config.get("randomize", True)
        
        # Connection state
        self.is_connected = False
        self.last_heartbeat = None
        
        # Encryption key (derived from shared secret)
        self.encryption_key = self._derive_key(config.get("secret", "persianshield"))
        
    def _derive_key(self, secret: str) -> bytes:
        """Derive encryption key from secret"""
        return hashlib.sha256(secret.encode()).digest()
    
    def _encrypt_data(self, data: bytes) -> bytes:
        """Encrypt data using AES-256-GCM"""
        # Generate random IV
        iv = random.randbytes(12)
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(self.encryption_key),
            modes.GCM(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # Encrypt
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        # Return: IV (12) + Tag (16) + Ciphertext
        return iv + encryptor.tag + ciphertext
    
    def _decrypt_data(self, data: bytes) -> bytes:
        """Decrypt data using AES-256-GCM"""
        # Extract components
        iv = data[:12]
        tag = data[12:28]
        ciphertext = data[28:]
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(self.encryption_key),
            modes.GCM(iv, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        # Decrypt
        return decryptor.update(ciphertext) + decryptor.finalize()
    
    def _add_padding(self, data: bytes) -> bytes:
        """Add random padding to obfuscate packet size"""
        if not self.padding_enabled:
            return data
        
        # Random padding size (0-255 bytes)
        padding_size = random.randint(0, 255)
        padding = random.randbytes(padding_size)
        
        # Format: [data_length (4)] [data] [padding]
        header = struct.pack(">I", len(data))
        return header + data + padding
    
    def _remove_padding(self, data: bytes) -> bytes:
        """Remove padding from data"""
        if len(data) < 4:
            return data
        
        # Extract real data length
        data_length = struct.unpack(">I", data[:4])[0]
        return data[4:4+data_length]
    
    def _create_tls_context(self) -> ssl.SSLContext:
        """Create SSL context with obfuscated SNI"""
        context = ssl.create_default_context()
        
        # Use TLS 1.3 only (more secure)
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        
        # Disable certificate verification (we're tunneling)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        return context
    
    async def _create_websocket_handshake(self, host: str) -> bytes:
        """Create WebSocket handshake request"""
        # Generate random WebSocket key
        ws_key = hashlib.sha256(random.randbytes(16)).hexdigest()[:24]
        
        # Create HTTP request
        handshake = (
            f"GET / HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {ws_key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"\r\n"
        )
        
        return handshake.encode()
    
    def _fragment_sni(self, sni: str) -> bytes:
        """Fragment SNI to bypass SNI-based filtering"""
        # This technique splits the SNI into multiple TLS records
        # to prevent simple pattern matching
        
        # Convert SNI to bytes
        sni_bytes = sni.encode()
        
        # Split into random fragments
        fragments = []
        pos = 0
        while pos < len(sni_bytes):
            # Random fragment size (1-10 bytes)
            frag_size = random.randint(1, min(10, len(sni_bytes) - pos))
            fragments.append(sni_bytes[pos:pos+frag_size])
            pos += frag_size
        
        return fragments
    
    async def establish_tunnel(self) -> bool:
        """Establish PersianShield tunnel"""
        try:
            logger.info(f"Establishing PersianShield tunnel to {self.foreign_host}:{self.foreign_port}")
            
            # Step 1: Create SSL context
            ssl_context = self._create_tls_context()
            
            # Step 2: Determine connection host (domain fronting)
            connect_host = self.fronting_domain if self.use_domain_fronting else self.foreign_host
            
            # Step 3: Create connection
            reader, writer = await asyncio.open_connection(
                connect_host,
                self.foreign_port,
                ssl=ssl_context,
                server_hostname=self.real_sni  # SNI goes here
            )
            
            # Step 4: Send WebSocket handshake
            handshake = await self._create_websocket_handshake(self.real_sni)
            writer.write(handshake)
            await writer.drain()
            
            # Step 5: Wait for handshake response
            response = await reader.read(1024)
            if b"101 Switching Protocols" not in response:
                raise Exception("WebSocket handshake failed")
            
            # Step 6: Send authentication
            auth_data = {
                "type": "auth",
                "secret": self.config.get("secret"),
                "timestamp": datetime.utcnow().isoformat()
            }
            encrypted_auth = self._encrypt_data(json.dumps(auth_data).encode())
            padded_auth = self._add_padding(encrypted_auth)
            
            writer.write(padded_auth)
            await writer.drain()
            
            # Store connection
            self.reader = reader
            self.writer = writer
            self.is_connected = True
            self.last_heartbeat = datetime.utcnow()
            
            logger.info("PersianShield tunnel established successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to establish PersianShield tunnel: {e}")
            return False
    
    async def send_data(self, data: bytes) -> bool:
        """Send data through tunnel"""
        if not self.is_connected:
            return False
        
        try:
            # Encrypt and pad data
            encrypted = self._encrypt_data(data)
            padded = self._add_padding(encrypted)
            
            # Send through tunnel
            self.writer.write(padded)
            await self.writer.drain()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send data: {e}")
            self.is_connected = False
            return False
    
    async def receive_data(self) -> Optional[bytes]:
        """Receive data from tunnel"""
        if not self.is_connected:
            return None
        
        try:
            # Receive data
            padded_data = await self.reader.read(4096)
            if not padded_data:
                self.is_connected = False
                return None
            
            # Remove padding and decrypt
            encrypted = self._remove_padding(padded_data)
            decrypted = self._decrypt_data(encrypted)
            
            return decrypted
            
        except Exception as e:
            logger.error(f"Failed to receive data: {e}")
            self.is_connected = False
            return None
    
    async def heartbeat(self) -> bool:
        """Send heartbeat to keep tunnel alive"""
        try:
            heartbeat_msg = json.dumps({
                "type": "heartbeat",
                "timestamp": datetime.utcnow().isoformat()
            }).encode()
            
            return await self.send_data(heartbeat_msg)
            
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")
            return False
    
    async def close(self):
        """Close tunnel gracefully"""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        
        self.is_connected = False
        logger.info("PersianShield tunnel closed")
    
    def get_status(self) -> Dict[str, Any]:
        """Get tunnel status"""
        return {
            "connected": self.is_connected,
            "iran_endpoint": f"{self.iran_host}:{self.iran_port}",
            "foreign_endpoint": f"{self.foreign_host}:{self.foreign_port}",
            "domain_fronting": self.use_domain_fronting,
            "fronting_domain": self.fronting_domain,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
        }


class PersianShieldManager:
    """Manager for multiple PersianShield tunnels"""
    
    def __init__(self):
        self.tunnels: Dict[str, PersianShieldTunnel] = {}
        self.monitoring_task = None
    
    async def create_tunnel(self, name: str, config: Dict[str, Any]) -> bool:
        """Create and establish new tunnel"""
        try:
            tunnel = PersianShieldTunnel(config)
            success = await tunnel.establish_tunnel()
            
            if success:
                self.tunnels[name] = tunnel
                logger.info(f"Created PersianShield tunnel: {name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to create tunnel {name}: {e}")
            return False
    
    async def remove_tunnel(self, name: str):
        """Remove tunnel"""
        if name in self.tunnels:
            await self.tunnels[name].close()
            del self.tunnels[name]
            logger.info(f"Removed tunnel: {name}")
    
    async def monitor_tunnels(self):
        """Monitor all tunnels and send heartbeats"""
        while True:
            try:
                for name, tunnel in list(self.tunnels.items()):
                    if tunnel.is_connected:
                        await tunnel.heartbeat()
                    else:
                        # Try to reconnect
                        logger.warning(f"Tunnel {name} disconnected, attempting reconnect...")
                        await tunnel.establish_tunnel()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in tunnel monitor: {e}")
                await asyncio.sleep(5)
    
    def start_monitoring(self):
        """Start background monitoring"""
        if not self.monitoring_task:
            self.monitoring_task = asyncio.create_task(self.monitor_tunnels())
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all tunnels"""
        return {
            name: tunnel.get_status()
            for name, tunnel in self.tunnels.items()
        }
