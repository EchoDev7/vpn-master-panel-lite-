"""
Rathole Tunnel Implementation
A secure, stable and high-performance reverse proxy for NAT traversal
Based on: https://github.com/rapiz1/rathole
"""
import asyncio
import subprocess
import os
import toml
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class RatholeTunnel:
    """
    Rathole tunnel - Fast, secure, Rust-based reverse proxy
    Perfect for bypassing NAT and firewalls
    """
    
    RATHOLE_BINARY = "/usr/local/bin/rathole"
    CONFIG_DIR = "/etc/rathole"
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.config_file = f"{self.CONFIG_DIR}/{name}.toml"
        
        Path(self.CONFIG_DIR).mkdir(parents=True, exist_ok=True)
    
    def _generate_server_config(self) -> Dict[str, Any]:
        """Generate Rathole server config (Iran side)"""
        config = {
            "server": {
                "bind_addr": f"0.0.0.0:{self.config['iran_port']}",
                "default_token": self.config.get("token", "rathole-secret"),
                "heartbeat_interval": 30,
                "services": {}
            }
        }
        
        # Add services for each forwarded port
        for port in self.config.get("forward_ports", []):
            service_name = f"service_{port}"
            config["server"]["services"][service_name] = {
                "type": "tcp",
                "bind_addr": f"0.0.0.0:{port}"
            }
        
        return config
    
    def _generate_client_config(self) -> Dict[str, Any]:
        """Generate Rathole client config (Foreign side)"""
        config = {
            "client": {
                "remote_addr": f"{self.config['iran_ip']}:{self.config['iran_port']}",
                "default_token": self.config.get("token", "rathole-secret"),
                "heartbeat_interval": 30,
                "retry_interval": 1,
                "services": {}
            }
        }
        
        # Add services
        for port in self.config.get("forward_ports", []):
            service_name = f"service_{port}"
            local_port = self.config.get("local_ports", {}).get(str(port), port)
            config["client"]["services"][service_name] = {
                "type": "tcp",
                "local_addr": f"127.0.0.1:{local_port}"
            }
        
        return config
    
    async def install_rathole(self) -> bool:
        """Download and install Rathole binary"""
        if os.path.exists(self.RATHOLE_BINARY):
            logger.info("Rathole already installed")
            return True
        
        try:
            logger.info("Downloading Rathole...")
            
            # Download latest release
            download_url = "https://github.com/rapiz1/rathole/releases/latest/download/rathole-x86_64-unknown-linux-gnu.zip"
            
            subprocess.run([
                "wget", "-q", "-O", "/tmp/rathole.zip", download_url
            ], check=True)
            
            # Extract
            subprocess.run([
                "unzip", "-q", "-o", "/tmp/rathole.zip", "-d", "/tmp"
            ], check=True)
            
            # Move to bin
            subprocess.run([
                "mv", "/tmp/rathole", self.RATHOLE_BINARY
            ], check=True)
            
            subprocess.run(["chmod", "+x", self.RATHOLE_BINARY], check=True)
            
            logger.info("Rathole installed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to install Rathole: {e}")
            return False
    
    async def start(self, mode: str = "client") -> bool:
        """Start Rathole tunnel"""
        try:
            if not os.path.exists(self.RATHOLE_BINARY):
                if not await self.install_rathole():
                    return False
            
            # Generate config
            if mode == "server":
                config_dict = self._generate_server_config()
            else:
                config_dict = self._generate_client_config()
            
            # Write config file
            with open(self.config_file, 'w') as f:
                toml.dump(config_dict, f)
            
            logger.info(f"Starting Rathole tunnel: {self.name} (mode: {mode})")
            
            # Start process
            self.process = subprocess.Popen(
                [self.RATHOLE_BINARY, self.config_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            await asyncio.sleep(2)
            
            if self.process.poll() is None:
                logger.info(f"Rathole tunnel {self.name} started successfully")
                return True
            else:
                stderr = self.process.stderr.read()
                raise Exception(f"Rathole failed to start: {stderr}")
            
        except Exception as e:
            logger.error(f"Failed to start Rathole tunnel {self.name}: {e}")
            return False
    
    async def stop(self):
        """Stop Rathole tunnel"""
        if self.process:
            try:
                self.process.terminate()
                await asyncio.sleep(1)
                
                if self.process.poll() is None:
                    self.process.kill()
                
                logger.info(f"Rathole tunnel {self.name} stopped")
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
            "type": "rathole",
            "running": self.is_running(),
            "config": self.config,
            "pid": self.process.pid if self.process else None
        }
    
    async def restart(self, mode: str = "client") -> bool:
        """Restart tunnel"""
        await self.stop()
        await asyncio.sleep(1)
        return await self.start(mode)
