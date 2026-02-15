"""
VPN Server and Node Models
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from ..database import Base


class ServerType(str, enum.Enum):
    """Type of VPN server"""
    MAIN = "main"      # Main panel server
    NODE = "node"      # Slave/node server


class ServerStatus(str, enum.Enum):
    """Server health status"""
    ONLINE = "online"
    OFFLINE = "offline"
    WARNING = "warning"
    ERROR = "error"


class VPNServer(Base):
    """VPN Server/Node configuration"""
    __tablename__ = "vpn_servers"
    
    # Identity
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    hostname = Column(String(255), nullable=False)
    public_ip = Column(String(50), nullable=False)
    
    # Type & Location
    server_type = Column(String(20), default=ServerType.NODE)
    location = Column(String(100))  # e.g., "Germany", "Iran"
    
    # SSH Access (for node management)
    ssh_host = Column(String(255))
    ssh_port = Column(Integer, default=22)
    ssh_username = Column(String(100))
    ssh_password = Column(String(255))
    ssh_private_key = Column(Text)
    
    # Status
    status = Column(String(20), default=ServerStatus.OFFLINE)
    last_health_check = Column(DateTime(timezone=True))
    
    # System Stats
    cpu_usage = Column(Float, default=0.0)
    ram_usage = Column(Float, default=0.0)
    disk_usage = Column(Float, default=0.0)
    bandwidth_in = Column(Integer, default=0)  # Mbps
    bandwidth_out = Column(Integer, default=0)  # Mbps
    
    # VPN Protocol Support
    openvpn_enabled = Column(Boolean, default=True)
    openvpn_port = Column(Integer, default=1194)
    openvpn_protocol = Column(String(10), default="udp")  # udp/tcp
    
    wireguard_enabled = Column(Boolean, default=True)
    wireguard_port = Column(Integer, default=51820)
    wireguard_public_key = Column(String(255))
    
    l2tp_enabled = Column(Boolean, default=False)
    l2tp_psk = Column(String(255), default="vpnmaster")
    
    cisco_enabled = Column(Boolean, default=False)
    cisco_port = Column(Integer, default=4443)
    
    # Visibility Settings
    show_in_client = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    
    # Additional Config
    custom_config = Column(JSON)  # Store custom settings as JSON
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tunnels = relationship("Tunnel", back_populates="server")
    
    def __repr__(self):
        return f"<VPNServer(name='{self.name}', ip='{self.public_ip}', status='{self.status}')>"
    
    @property
    def is_healthy(self) -> bool:
        """Check if server is healthy"""
        return self.status == ServerStatus.ONLINE


class Tunnel(Base):
    """Tunnel configuration between Iran and Foreign servers"""
    __tablename__ = "tunnels"
    
    # Identity
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    
    # Tunnel Type
    tunnel_type = Column(String(50), nullable=False)  # backhaul, rathole, frp, chisel, persianshield
    protocol = Column(String(20), default="tcp")  # tcp/udp
    
    # Server References
    server_id = Column(Integer, ForeignKey("vpn_servers.id"), nullable=False)  # Foreign server ID
    iran_server_ip = Column(String(50), nullable=False)
    iran_server_port = Column(Integer, nullable=False)
    
    foreign_server_ip = Column(String(50), nullable=False)
    foreign_server_port = Column(Integer, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=False)
    status = Column(String(20), default="disconnected")  # connected, disconnected, error
    last_check = Column(DateTime(timezone=True))
    
    # Configuration
    config = Column(JSON)  # Store tunnel-specific config
    
    # Ports to Forward
    forwarded_ports = Column(JSON)  # List of ports to forward
    
    # Iran Bypass Features
    domain_fronting_enabled = Column(Boolean, default=False)
    domain_fronting_domain = Column(String(255))
    tls_obfuscation = Column(Boolean, default=False)
    sni_override = Column(String(255))
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    server = relationship("VPNServer", back_populates="tunnels")
    
    def __repr__(self):
        return f"<Tunnel(name='{self.name}', type='{self.tunnel_type}', status='{self.status}')>"
