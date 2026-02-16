"""
Gost (GO Simple Tunnel) Implementation
Multi-protocol tunnel supporting HTTP/SOCKS5/WS/WSS/QUIC/KCP
Based on: https://github.com/go-gost/gost
"""
import asyncio
import subprocess
import os
import json
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class GostTunnel:
    """
    Gost tunnel - Multi-protocol tunnel for censorship bypass
    Supports: HTTP, SOCKS5, Shadowsocks, WS, WSS, QUIC, KCP, relay chains
    """
    
    GOST_BINARY = "/usr/local/bin/gost"
    CONFIG_DIR = "/etc/gost"
    SERVICE_DIR = "/etc/systemd/system"
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.config_file = f"{self.CONFIG_DIR}/{name}.yaml"
        
        Path(self.CONFIG_DIR).mkdir(parents=True, exist_ok=True)
    
    def _generate_config(self, mode: str) -> Dict[str, Any]:
        """
        Generate Gost YAML configuration
        mode: 'server' (Iran) or 'client' (Foreign)
        """
        protocol = self.config.get("protocol", "relay+ws")
        iran_ip = self.config.get("iran_ip", "0.0.0.0")
        iran_port = self.config.get("iran_port", 8443)
        foreign_ip = self.config.get("foreign_ip", "")
        foreign_port = self.config.get("foreign_port", 8443)
        forward_ports = self.config.get("forward_ports", [])
        
        if mode == "server":
            # Iran server: listen and relay to foreign
            config = {
                "services": [{
                    "name": f"gost-{self.name}",
                    "addr": f":{iran_port}",
                    "handler": {
                        "type": protocol.split("+")[0] if "+" in protocol else "relay",
                        "chain": f"chain-{self.name}"
                    },
                    "listener": {
                        "type": protocol.split("+")[1] if "+" in protocol else "tcp"
                    }
                }],
                "chains": [{
                    "name": f"chain-{self.name}",
                    "hops": [{
                        "name": "hop-0",
                        "nodes": [{
                            "name": "node-0",
                            "addr": f"{foreign_ip}:{foreign_port}",
                            "connector": {"type": "relay"},
                            "dialer": {"type": "ws" if "ws" in protocol else "tcp"}
                        }]
                    }]
                }]
            }
            
            # Add port forwarding services
            for port in forward_ports:
                config["services"].append({
                    "name": f"fwd-{port}",
                    "addr": f":{port}",
                    "handler": {"type": "tcp", "chain": f"chain-{self.name}"},
                    "listener": {"type": "tcp"},
                    "forwarder": {"nodes": [{"name": f"target-{port}", "addr": f"127.0.0.1:{port}"}]}
                })
        else:
            # Foreign server: accept relay connections
            config = {
                "services": [{
                    "name": f"gost-{self.name}",
                    "addr": f":{foreign_port}",
                    "handler": {"type": "relay"},
                    "listener": {"type": "ws" if "ws" in protocol else "tcp"}
                }]
            }
            
            # Add port forwarding targets
            for port in forward_ports:
                config["services"].append({
                    "name": f"fwd-{port}",
                    "addr": f":{port}",
                    "handler": {"type": "tcp"},
                    "listener": {"type": "tcp"},
                    "forwarder": {"nodes": [{"name": f"target-{port}", "addr": f"127.0.0.1:{port}"}]}
                })
        
        return config
    
    async def install_gost(self) -> bool:
        """Download and install Gost v3 binary"""
        if os.path.exists(self.GOST_BINARY):
            logger.info("Gost already installed")
            return True
        
        try:
            logger.info("Downloading Gost v3...")
            
            # Get latest release URL
            download_url = "https://github.com/go-gost/gost/releases/latest/download/gost_linux_amd64.tar.gz"
            
            cmds = [
                ["wget", "-q", "-O", "/tmp/gost.tar.gz", download_url],
                ["tar", "-xzf", "/tmp/gost.tar.gz", "-C", "/tmp"],
                ["mv", "/tmp/gost", self.GOST_BINARY],
                ["chmod", "+x", self.GOST_BINARY],
            ]
            
            for cmd in cmds:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    raise Exception(f"Command failed: {' '.join(cmd)}: {result.stderr}")
            
            # Cleanup
            subprocess.run(["rm", "-f", "/tmp/gost.tar.gz"], capture_output=True)
            
            logger.info("Gost installed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to install Gost: {e}")
            return False
    
    def _create_systemd_service(self, mode: str):
        """Create systemd service for persistence"""
        service_content = f"""[Unit]
Description=Gost Tunnel - {self.name}
After=network.target

[Service]
Type=simple
ExecStart={self.GOST_BINARY} -C {self.config_file}
Restart=always
RestartSec=5
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
"""
        service_file = f"{self.SERVICE_DIR}/gost-{self.name}.service"
        try:
            with open(service_file, 'w') as f:
                f.write(service_content)
            subprocess.run(["systemctl", "daemon-reload"], capture_output=True)
            subprocess.run(["systemctl", "enable", f"gost-{self.name}"], capture_output=True)
            logger.info(f"Systemd service created: gost-{self.name}")
        except Exception as e:
            logger.warning(f"Could not create systemd service: {e}")
    
    async def start(self, mode: str = "server") -> bool:
        """Start Gost tunnel"""
        try:
            if not os.path.exists(self.GOST_BINARY):
                if not await self.install_gost():
                    return False
            
            # Generate config
            config_dict = self._generate_config(mode)
            with open(self.config_file, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False)
            
            # Create systemd service
            self._create_systemd_service(mode)
            
            logger.info(f"Starting Gost tunnel: {self.name} (mode: {mode})")
            
            # Start via systemd if available, otherwise direct
            result = subprocess.run(
                ["systemctl", "start", f"gost-{self.name}"],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                # Fallback: start directly
                self.process = subprocess.Popen(
                    [self.GOST_BINARY, "-C", self.config_file],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                await asyncio.sleep(2)
                if self.process.poll() is not None:
                    stderr = self.process.stderr.read()
                    raise Exception(f"Gost failed to start: {stderr}")
            
            logger.info(f"Gost tunnel {self.name} started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Gost tunnel {self.name}: {e}")
            return False
    
    async def stop(self):
        """Stop Gost tunnel"""
        try:
            # Try systemd first
            subprocess.run(["systemctl", "stop", f"gost-{self.name}"], capture_output=True)
            
            # Also kill direct process
            if self.process:
                self.process.terminate()
                await asyncio.sleep(1)
                if self.process.poll() is None:
                    self.process.kill()
            
            logger.info(f"Gost tunnel {self.name} stopped")
        except Exception as e:
            logger.error(f"Error stopping tunnel {self.name}: {e}")
    
    def is_running(self) -> bool:
        """Check if tunnel is running"""
        # Check systemd
        result = subprocess.run(
            ["systemctl", "is-active", f"gost-{self.name}"],
            capture_output=True, text=True
        )
        if result.stdout.strip() == "active":
            return True
        
        # Check direct process
        if self.process and self.process.poll() is None:
            return True
        
        return False
    
    async def get_status(self) -> Dict[str, Any]:
        """Get tunnel status"""
        return {
            "name": self.name,
            "type": "gost",
            "running": self.is_running(),
            "config": self.config,
            "pid": self.process.pid if self.process else None
        }
    
    async def restart(self, mode: str = "server") -> bool:
        """Restart tunnel"""
        await self.stop()
        await asyncio.sleep(1)
        return await self.start(mode)


class GostManager:
    """Manager for multiple Gost tunnels"""
    
    def __init__(self):
        self.tunnels: Dict[str, GostTunnel] = {}
    
    async def create_tunnel(self, name: str, config: Dict[str, Any], mode: str = "server") -> bool:
        """Create and start new Gost tunnel"""
        if name in self.tunnels:
            logger.warning(f"Tunnel {name} already exists")
            return False
        
        tunnel = GostTunnel(name, config)
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
        
        # Remove config and service
        config_file = f"{GostTunnel.CONFIG_DIR}/{name}.yaml"
        service_file = f"{GostTunnel.SERVICE_DIR}/gost-{name}.service"
        for f in [config_file, service_file]:
            if os.path.exists(f):
                os.remove(f)
        
        subprocess.run(["systemctl", "daemon-reload"], capture_output=True)
        return True
    
    async def restart_tunnel(self, name: str, mode: str = "server") -> bool:
        if name not in self.tunnels:
            return False
        return await self.tunnels[name].restart(mode)
    
    def get_tunnel(self, name: str) -> Optional[GostTunnel]:
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
        return os.path.exists(GostTunnel.GOST_BINARY)
