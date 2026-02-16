"""
Chisel Tunnel Implementation
Fast TCP/UDP tunnel over HTTP with SSH encryption
Based on: https://github.com/jpillora/chisel
"""
import asyncio
import subprocess
import os
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ChiselTunnel:
    """
    Chisel tunnel - HTTP-based reverse tunnel
    Perfect for bypassing firewalls since it uses standard HTTP/WS
    """
    
    CHISEL_BINARY = "/usr/local/bin/chisel"
    CONFIG_DIR = "/etc/chisel"
    SERVICE_DIR = "/etc/systemd/system"
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        
        Path(self.CONFIG_DIR).mkdir(parents=True, exist_ok=True)
    
    def _build_server_cmd(self) -> list:
        """Build Chisel server command"""
        port = self.config.get("iran_port", 8080)
        cmd = [
            self.CHISEL_BINARY, "server",
            "--port", str(port),
            "--reverse",
        ]
        
        # TLS
        if self.config.get("tls_enabled"):
            key = self.config.get("tls_key", "")
            cert = self.config.get("tls_cert", "")
            if key and cert:
                cmd.extend(["--tls-key", key, "--tls-cert", cert])
        
        # Auth
        auth = self.config.get("auth", "")
        if auth:
            cmd.extend(["--auth", auth])
        
        # Keep alive
        keepalive = self.config.get("keepalive", "25s")
        cmd.extend(["--keepalive", keepalive])
        
        return cmd
    
    def _build_client_cmd(self) -> list:
        """Build Chisel client command"""
        iran_ip = self.config.get("iran_ip", "")
        iran_port = self.config.get("iran_port", 8080)
        forward_ports = self.config.get("forward_ports", [])
        
        scheme = "https" if self.config.get("tls_enabled") else "http"
        server_url = f"{scheme}://{iran_ip}:{iran_port}"
        
        cmd = [
            self.CHISEL_BINARY, "client",
            server_url,
        ]
        
        # Auth
        auth = self.config.get("auth", "")
        if auth:
            cmd.extend(["--auth", auth])
        
        # Keep alive
        keepalive = self.config.get("keepalive", "25s")
        cmd.extend(["--keepalive", keepalive])
        
        # Fingerprint for TLS verification
        fingerprint = self.config.get("fingerprint", "")
        if fingerprint:
            cmd.extend(["--fingerprint", fingerprint])
        
        # Port forwarding: R:remote_port:local_host:local_port (reverse)
        for port in forward_ports:
            local_port = self.config.get("local_ports", {}).get(str(port), port)
            cmd.append(f"R:{port}:127.0.0.1:{local_port}")
        
        # If no specific ports, forward all
        if not forward_ports:
            cmd.append(f"R:0.0.0.0:socks")
        
        return cmd
    
    async def install_chisel(self) -> bool:
        """Download and install Chisel binary"""
        if os.path.exists(self.CHISEL_BINARY):
            logger.info("Chisel already installed")
            return True
        
        try:
            logger.info("Downloading Chisel...")
            
            download_url = "https://github.com/jpillora/chisel/releases/latest/download/chisel_linux_amd64.gz"
            
            cmds = [
                ["wget", "-q", "-O", "/tmp/chisel.gz", download_url],
                ["gunzip", "-f", "/tmp/chisel.gz"],
                ["mv", "/tmp/chisel", self.CHISEL_BINARY],
                ["chmod", "+x", self.CHISEL_BINARY],
            ]
            
            for cmd in cmds:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    raise Exception(f"Command failed: {' '.join(cmd)}: {result.stderr}")
            
            logger.info("Chisel installed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to install Chisel: {e}")
            return False
    
    def _create_systemd_service(self, mode: str):
        """Create systemd service for persistence"""
        cmd = self._build_server_cmd() if mode == "server" else self._build_client_cmd()
        exec_start = " ".join(cmd)
        
        service_content = f"""[Unit]
Description=Chisel Tunnel - {self.name}
After=network.target

[Service]
Type=simple
ExecStart={exec_start}
Restart=always
RestartSec=5
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
"""
        service_file = f"{self.SERVICE_DIR}/chisel-{self.name}.service"
        try:
            with open(service_file, 'w') as f:
                f.write(service_content)
            subprocess.run(["systemctl", "daemon-reload"], capture_output=True)
            subprocess.run(["systemctl", "enable", f"chisel-{self.name}"], capture_output=True)
            logger.info(f"Systemd service created: chisel-{self.name}")
        except Exception as e:
            logger.warning(f"Could not create systemd service: {e}")
    
    async def start(self, mode: str = "server") -> bool:
        """Start Chisel tunnel"""
        try:
            if not os.path.exists(self.CHISEL_BINARY):
                if not await self.install_chisel():
                    return False
            
            # Create systemd service
            self._create_systemd_service(mode)
            
            logger.info(f"Starting Chisel tunnel: {self.name} (mode: {mode})")
            
            # Build command
            cmd = self._build_server_cmd() if mode == "server" else self._build_client_cmd()
            
            # Try systemd first
            result = subprocess.run(
                ["systemctl", "start", f"chisel-{self.name}"],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                # Fallback: start directly
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                await asyncio.sleep(2)
                if self.process.poll() is not None:
                    stderr = self.process.stderr.read()
                    raise Exception(f"Chisel failed to start: {stderr}")
            
            logger.info(f"Chisel tunnel {self.name} started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Chisel tunnel {self.name}: {e}")
            return False
    
    async def stop(self):
        """Stop Chisel tunnel"""
        try:
            subprocess.run(["systemctl", "stop", f"chisel-{self.name}"], capture_output=True)
            
            if self.process:
                self.process.terminate()
                await asyncio.sleep(1)
                if self.process.poll() is None:
                    self.process.kill()
            
            logger.info(f"Chisel tunnel {self.name} stopped")
        except Exception as e:
            logger.error(f"Error stopping tunnel {self.name}: {e}")
    
    def is_running(self) -> bool:
        """Check if tunnel is running"""
        result = subprocess.run(
            ["systemctl", "is-active", f"chisel-{self.name}"],
            capture_output=True, text=True
        )
        if result.stdout.strip() == "active":
            return True
        if self.process and self.process.poll() is None:
            return True
        return False
    
    async def get_status(self) -> Dict[str, Any]:
        """Get tunnel status"""
        return {
            "name": self.name,
            "type": "chisel",
            "running": self.is_running(),
            "config": self.config,
            "pid": self.process.pid if self.process else None
        }
    
    async def restart(self, mode: str = "server") -> bool:
        """Restart tunnel"""
        await self.stop()
        await asyncio.sleep(1)
        return await self.start(mode)


class ChiselManager:
    """Manager for multiple Chisel tunnels"""
    
    def __init__(self):
        self.tunnels: Dict[str, ChiselTunnel] = {}
    
    async def create_tunnel(self, name: str, config: Dict[str, Any], mode: str = "server") -> bool:
        if name in self.tunnels:
            logger.warning(f"Tunnel {name} already exists")
            return False
        
        tunnel = ChiselTunnel(name, config)
        success = await tunnel.start(mode)
        
        if success:
            self.tunnels[name] = tunnel
            return True
        return False
    
    async def remove_tunnel(self, name: str) -> bool:
        if name not in self.tunnels:
            return False
        
        await self.tunnels[name].stop()
        del self.tunnels[name]
        
        # Remove service
        service_file = f"{ChiselTunnel.SERVICE_DIR}/chisel-{name}.service"
        if os.path.exists(service_file):
            os.remove(service_file)
        subprocess.run(["systemctl", "daemon-reload"], capture_output=True)
        return True
    
    async def restart_tunnel(self, name: str, mode: str = "server") -> bool:
        if name not in self.tunnels:
            return False
        return await self.tunnels[name].restart(mode)
    
    def get_tunnel(self, name: str) -> Optional[ChiselTunnel]:
        return self.tunnels.get(name)
    
    async def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        statuses = {}
        for name, tunnel in self.tunnels.items():
            statuses[name] = await tunnel.get_status()
        return statuses
    
    async def stop_all(self):
        for tunnel in self.tunnels.values():
            await tunnel.stop()
    
    @staticmethod
    def is_installed() -> bool:
        return os.path.exists(ChiselTunnel.CHISEL_BINARY)
