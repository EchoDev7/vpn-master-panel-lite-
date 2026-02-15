"""
Backhaul Tunnel Implementation
Based on: https://github.com/Musixal/Backhaul
"""
import asyncio
import subprocess
import os
import json
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class BackhaulTunnel:
    """
    Backhaul tunnel implementation for Iran-Foreign server connection
    Supports both TCP and UDP protocols
    """
    
    BACKHAUL_BINARY = "/usr/local/bin/backhaul"
    CONFIG_DIR = "/etc/backhaul"
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.config_file = f"{self.CONFIG_DIR}/{name}.toml"
        
        # Ensure config directory exists
        Path(self.CONFIG_DIR).mkdir(parents=True, exist_ok=True)
    
    def _generate_config(self, mode: str) -> str:
        """
        Generate Backhaul TOML configuration
        mode: 'server' (Iran) or 'client' (Foreign)
        """
        if mode == "server":
            # Iran server configuration
            ports_str = ",".join(map(str, self.config.get("forward_ports", [])))
            
            config = f"""
[server]
bind_addr = "0.0.0.0:{self.config['iran_port']}"
transport = "{self.config.get('protocol', 'tcp')}"
token = "{self.config.get('token', 'backhaul-secret')}"
heartbeat = 30
channel_size = 2048

[server.options]
nodelay = true
keepalive = 90

[server.ports]
ports = [{ports_str}]

[server.web]
enable = true
web_port = {self.config.get('web_port', 2060)}
"""
        else:
            # Foreign server configuration
            config = f"""
[client]
remote_addr = "{self.config['iran_ip']}:{self.config['iran_port']}"
transport = "{self.config.get('protocol', 'tcp')}"
token = "{self.config.get('token', 'backhaul-secret')}"
connection_pool = 8
retry_interval = 3

[client.options]
nodelay = true
keepalive = 90

[client.web]
enable = true
web_port = {self.config.get('web_port', 2061)}
"""
        
        return config.strip()
    
    async def install_backhaul(self) -> bool:
        """Download and install Backhaul binary"""
        if os.path.exists(self.BACKHAUL_BINARY):
            logger.info("Backhaul already installed")
            return True
        
        try:
            logger.info("Downloading Backhaul...")
            
            # Download latest release
            download_cmd = [
                "wget",
                "-q",
                "-O",
                "/tmp/backhaul.tar.gz",
                "https://github.com/Musixal/Backhaul/releases/download/v0.6.5/backhaul_linux_amd64.tar.gz"
            ]
            
            result = subprocess.run(download_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Failed to download: {result.stderr}")
            
            # Extract
            subprocess.run(["tar", "-xzf", "/tmp/backhaul.tar.gz", "-C", "/tmp"], check=True)
            
            # Move to bin
            subprocess.run(["mv", "/tmp/backhaul", self.BACKHAUL_BINARY], check=True)
            subprocess.run(["chmod", "+x", self.BACKHAUL_BINARY], check=True)
            
            logger.info("Backhaul installed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to install Backhaul: {e}")
            return False
    
    async def start(self, mode: str = "client") -> bool:
        """Start Backhaul tunnel"""
        try:
            # Ensure Backhaul is installed
            if not os.path.exists(self.BACKHAUL_BINARY):
                if not await self.install_backhaul():
                    return False
            
            # Generate config file
            config_content = self._generate_config(mode)
            with open(self.config_file, 'w') as f:
                f.write(config_content)
            
            logger.info(f"Starting Backhaul tunnel: {self.name} (mode: {mode})")
            
            # Start process
            self.process = subprocess.Popen(
                [self.BACKHAUL_BINARY, "-c", self.config_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait a bit to check if it started successfully
            await asyncio.sleep(2)
            
            if self.process.poll() is None:
                logger.info(f"Backhaul tunnel {self.name} started successfully")
                return True
            else:
                stderr = self.process.stderr.read()
                raise Exception(f"Backhaul failed to start: {stderr}")
            
        except Exception as e:
            logger.error(f"Failed to start Backhaul tunnel {self.name}: {e}")
            return False
    
    async def stop(self):
        """Stop Backhaul tunnel"""
        if self.process:
            try:
                self.process.terminate()
                await asyncio.sleep(1)
                
                if self.process.poll() is None:
                    self.process.kill()
                
                logger.info(f"Backhaul tunnel {self.name} stopped")
                
            except Exception as e:
                logger.error(f"Error stopping tunnel {self.name}: {e}")
    
    def is_running(self) -> bool:
        """Check if tunnel is running"""
        if not self.process:
            return False
        return self.process.poll() is None
    
    async def get_status(self) -> Dict[str, Any]:
        """Get tunnel status"""
        return {
            "name": self.name,
            "type": "backhaul",
            "running": self.is_running(),
            "config": self.config,
            "pid": self.process.pid if self.process else None
        }
    
    async def restart(self, mode: str = "client") -> bool:
        """Restart tunnel"""
        await self.stop()
        await asyncio.sleep(1)
        return await self.start(mode)


class BackhaulManager:
    """Manager for multiple Backhaul tunnels"""
    
    def __init__(self):
        self.tunnels: Dict[str, BackhaulTunnel] = {}
    
    async def create_tunnel(self, name: str, config: Dict[str, Any], mode: str = "client") -> bool:
        """Create and start new Backhaul tunnel"""
        if name in self.tunnels:
            logger.warning(f"Tunnel {name} already exists")
            return False
        
        tunnel = BackhaulTunnel(name, config)
        success = await tunnel.start(mode)
        
        if success:
            self.tunnels[name] = tunnel
            return True
        
        return False
    
    async def remove_tunnel(self, name: str) -> bool:
        """Remove tunnel"""
        if name not in self.tunnels:
            return False
        
        await self.tunnels[name].stop()
        del self.tunnels[name]
        
        # Remove config file
        config_file = f"{BackhaulTunnel.CONFIG_DIR}/{name}.toml"
        if os.path.exists(config_file):
            os.remove(config_file)
        
        return True
    
    async def restart_tunnel(self, name: str, mode: str = "client") -> bool:
        """Restart specific tunnel"""
        if name not in self.tunnels:
            return False
        
        return await self.tunnels[name].restart(mode)
    
    def get_tunnel(self, name: str) -> Optional[BackhaulTunnel]:
        """Get tunnel by name"""
        return self.tunnels.get(name)
    
    async def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all tunnels"""
        statuses = {}
        for name, tunnel in self.tunnels.items():
            statuses[name] = await tunnel.get_status()
        return statuses
    
    async def stop_all(self):
        """Stop all tunnels"""
        for tunnel in self.tunnels.values():
            await tunnel.stop()
