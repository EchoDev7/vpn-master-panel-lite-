"""
Tunnels API Endpoints - Manage Iran-Foreign tunnels
Supports: Backhaul, Rathole, PersianShield, Gost, Chisel
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import os

from ..database import get_db
from ..models.user import User
from ..models.vpn_server import Tunnel
from ..utils.security import get_current_admin
from ..tunnels.backhaul import BackhaulManager, BackhaulTunnel
from ..tunnels.persianshield import PersianShieldManager
from ..tunnels.rathole import RatholeManager, RatholeTunnel
from ..tunnels.gost import GostManager, GostTunnel
from ..tunnels.chisel import ChiselManager, ChiselTunnel

router = APIRouter()

# Global tunnel managers
backhaul_manager = BackhaulManager()
shield_manager = PersianShieldManager()
rathole_manager = RatholeManager()
gost_manager = GostManager()
chisel_manager = ChiselManager()

MANAGERS = {
    "backhaul": backhaul_manager,
    "rathole": rathole_manager,
    "persianshield": shield_manager,
    "gost": gost_manager,
    "chisel": chisel_manager,
}

# ===== Tunnel Type Catalog =====
TUNNEL_CATALOG = {
    "backhaul": {
        "name": "Backhaul",
        "description": "Lightning-fast reverse tunneling with TCP/WS/WSS/UDP support",
        "language": "Go",
        "author": "Musixal",
        "repo": "https://github.com/Musixal/Backhaul",
        "protocols": ["tcp", "tcpmux", "udp", "ws", "wsmux", "wss", "wssmux"],
        "binary": BackhaulTunnel.BACKHAUL_BINARY,
        "iran_recommended": True,
        "features": ["Multiplexing", "WebSocket", "TLS", "Web UI", "Hot Reload"],
    },
    "rathole": {
        "name": "Rathole",
        "description": "Secure, stable reverse proxy for NAT traversal (Rust-based)",
        "language": "Rust",
        "author": "Musixal/rapiz1",
        "repo": "https://github.com/Musixal/Rathole-Tunnel",
        "protocols": ["tcp", "udp"],
        "binary": RatholeTunnel.RATHOLE_BINARY,
        "iran_recommended": True,
        "features": ["Low Latency", "Noise Protocol", "Heartbeat", "Token Auth"],
    },
    "persianshield": {
        "name": "PersianShield™",
        "description": "Custom anti-censorship tunnel with TLS 1.3, Domain Fronting, WebSocket",
        "language": "Python",
        "author": "VPN Master Panel",
        "repo": "Built-in",
        "protocols": ["tls+ws"],
        "binary": None,  # Python-based, always available
        "iran_recommended": True,
        "features": ["AES-256-GCM", "Domain Fronting", "SNI Fragmentation", "Traffic Padding"],
    },
    "gost": {
        "name": "Gost (GO Simple Tunnel)",
        "description": "Multi-protocol tunnel: HTTP/SOCKS5/WS/WSS/QUIC/KCP relay chains",
        "language": "Go",
        "author": "go-gost",
        "repo": "https://github.com/go-gost/gost",
        "protocols": ["tcp", "udp", "ws", "wss", "quic", "kcp", "http", "socks5"],
        "binary": GostTunnel.GOST_BINARY,
        "iran_recommended": True,
        "features": ["Multi-hop Chains", "Web API", "Relay", "Shadowsocks", "QUIC"],
    },
    "chisel": {
        "name": "Chisel",
        "description": "Fast TCP/UDP tunnel over HTTP with SSH encryption",
        "language": "Go",
        "author": "jpillora",
        "repo": "https://github.com/jpillora/chisel",
        "protocols": ["http", "ws", "wss"],
        "binary": ChiselTunnel.CHISEL_BINARY,
        "iran_recommended": True,
        "features": ["Reverse Tunnel", "SOCKS5 Proxy", "TLS", "Fingerprint Auth"],
    },
}


# ===== Schemas =====

class TunnelCreate(BaseModel):
    name: str
    tunnel_type: str  # backhaul, rathole, persianshield, gost, chisel
    protocol: str = "tcp"
    mode: str = "server"  # server (Iran) or client (Foreign)
    
    server_id: int = 0
    iran_server_ip: str
    iran_server_port: int
    foreign_server_ip: str
    foreign_server_port: int
    
    forwarded_ports: Optional[List[int]] = []
    config: Optional[Dict[str, Any]] = {}
    
    domain_fronting_enabled: bool = False
    domain_fronting_domain: Optional[str] = None
    tls_obfuscation: bool = False


class TunnelResponse(BaseModel):
    id: int
    name: str
    tunnel_type: str
    protocol: str
    status: str
    is_active: bool
    
    iran_server_ip: str
    iran_server_port: int
    foreign_server_ip: str
    foreign_server_port: int
    
    forwarded_ports: Optional[List[int]]
    domain_fronting_enabled: bool
    
    created_at: datetime
    
    class Config:
        from_attributes = True


# ===== Available Tunnels =====

@router.get("/available")
async def get_available_tunnels(
    current_admin: User = Depends(get_current_admin)
):
    """List all available tunnel types with install status"""
    result = []
    for key, info in TUNNEL_CATALOG.items():
        installed = True
        if info["binary"]:
            installed = os.path.exists(info["binary"])
        
        result.append({
            "id": key,
            "name": info["name"],
            "description": info["description"],
            "language": info["language"],
            "author": info["author"],
            "repo": info["repo"],
            "protocols": info["protocols"],
            "features": info["features"],
            "iran_recommended": info["iran_recommended"],
            "installed": installed,
        })
    
    return result


# ===== Install / Uninstall =====

@router.post("/install/{tunnel_type}")
async def install_tunnel_binary(
    tunnel_type: str,
    current_admin: User = Depends(get_current_admin)
):
    """Install tunnel binary on server"""
    if tunnel_type not in TUNNEL_CATALOG:
        raise HTTPException(status_code=400, detail=f"Unknown tunnel type: {tunnel_type}")
    
    info = TUNNEL_CATALOG[tunnel_type]
    
    if info["binary"] is None:
        return {"status": "ok", "message": f"{info['name']} is Python-based, no binary needed"}
    
    if os.path.exists(info["binary"]):
        return {"status": "ok", "message": f"{info['name']} is already installed"}
    
    try:
        # Create a temporary tunnel instance to use its install method
        if tunnel_type == "backhaul":
            t = BackhaulTunnel("_install", {})
            success = await t.install_backhaul()
        elif tunnel_type == "rathole":
            t = RatholeTunnel("_install", {})
            success = await t.install_rathole()
        elif tunnel_type == "gost":
            t = GostTunnel("_install", {})
            success = await t.install_gost()
        elif tunnel_type == "chisel":
            t = ChiselTunnel("_install", {})
            success = await t.install_chisel()
        else:
            raise HTTPException(status_code=400, detail="Cannot install this type")
        
        if success:
            return {"status": "ok", "message": f"{info['name']} installed successfully"}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to install {info['name']}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/uninstall/{tunnel_type}")
async def uninstall_tunnel_binary(
    tunnel_type: str,
    current_admin: User = Depends(get_current_admin)
):
    """Uninstall tunnel binary from server"""
    if tunnel_type not in TUNNEL_CATALOG:
        raise HTTPException(status_code=400, detail=f"Unknown tunnel type: {tunnel_type}")
    
    info = TUNNEL_CATALOG[tunnel_type]
    
    if info["binary"] is None:
        return {"status": "ok", "message": "Python-based tunnel, nothing to uninstall"}
    
    if os.path.exists(info["binary"]):
        os.remove(info["binary"])
        return {"status": "ok", "message": f"{info['name']} uninstalled"}
    
    return {"status": "ok", "message": "Not installed"}


# ===== CRUD =====

@router.post("/", response_model=TunnelResponse, status_code=status.HTTP_201_CREATED)
async def create_tunnel(
    tunnel_data: TunnelCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Create and establish new tunnel"""
    if tunnel_data.tunnel_type not in MANAGERS:
        raise HTTPException(status_code=400, detail=f"Unknown tunnel type: {tunnel_data.tunnel_type}")
    
    existing = db.query(Tunnel).filter(Tunnel.name == tunnel_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tunnel name already exists")
    
    # Create DB record
    tunnel = Tunnel(
        name=tunnel_data.name,
        tunnel_type=tunnel_data.tunnel_type,
        protocol=tunnel_data.protocol,
        server_id=tunnel_data.server_id or 0,
        iran_server_ip=tunnel_data.iran_server_ip,
        iran_server_port=tunnel_data.iran_server_port,
        foreign_server_ip=tunnel_data.foreign_server_ip,
        foreign_server_port=tunnel_data.foreign_server_port,
        forwarded_ports=tunnel_data.forwarded_ports,
        config=tunnel_data.config,
        domain_fronting_enabled=tunnel_data.domain_fronting_enabled,
        domain_fronting_domain=tunnel_data.domain_fronting_domain,
        tls_obfuscation=tunnel_data.tls_obfuscation,
    )
    db.add(tunnel)
    db.commit()
    db.refresh(tunnel)
    
    # Build config for the manager
    mgr_config = {
        "iran_ip": tunnel_data.iran_server_ip,
        "iran_port": tunnel_data.iran_server_port,
        "foreign_ip": tunnel_data.foreign_server_ip,
        "foreign_port": tunnel_data.foreign_server_port,
        "protocol": tunnel_data.protocol,
        "forward_ports": tunnel_data.forwarded_ports or [],
        "token": tunnel_data.config.get("token", "vpnmaster-secret") if tunnel_data.config else "vpnmaster-secret",
        "domain_fronting": tunnel_data.domain_fronting_enabled,
        "fronting_domain": tunnel_data.domain_fronting_domain or "cloudflare.com",
        "secret": tunnel_data.config.get("secret", "vpnmaster") if tunnel_data.config else "vpnmaster",
        "tls_enabled": tunnel_data.tls_obfuscation,
        "auth": tunnel_data.config.get("auth", "") if tunnel_data.config else "",
    }
    
    try:
        manager = MANAGERS[tunnel_data.tunnel_type]
        
        if tunnel_data.tunnel_type == "persianshield":
            # PersianShield uses different config keys
            ps_config = {
                "iran_host": tunnel_data.iran_server_ip,
                "iran_port": tunnel_data.iran_server_port,
                "foreign_host": tunnel_data.foreign_server_ip,
                "foreign_port": tunnel_data.foreign_server_port,
                "domain_fronting": tunnel_data.domain_fronting_enabled,
                "fronting_domain": tunnel_data.domain_fronting_domain or "cloudflare.com",
                "secret": mgr_config["secret"],
            }
            success = await manager.create_tunnel(tunnel_data.name, ps_config)
        else:
            success = await manager.create_tunnel(
                tunnel_data.name, mgr_config, mode=tunnel_data.mode
            )
        
        if success:
            tunnel.is_active = True
            tunnel.status = "connected"
        else:
            tunnel.status = "error"
        
        db.commit()
        db.refresh(tunnel)
        
    except Exception as e:
        tunnel.status = "error"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to start tunnel: {str(e)}")
    
    return tunnel


@router.get("/", response_model=List[TunnelResponse])
async def list_tunnels(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """List all tunnels"""
    return db.query(Tunnel).all()


@router.get("/{tunnel_id}", response_model=TunnelResponse)
async def get_tunnel(
    tunnel_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get tunnel by ID"""
    tunnel = db.query(Tunnel).filter(Tunnel.id == tunnel_id).first()
    if not tunnel:
        raise HTTPException(status_code=404, detail="Tunnel not found")
    return tunnel


@router.get("/{tunnel_id}/status")
async def get_tunnel_status(
    tunnel_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get real-time tunnel status"""
    tunnel = db.query(Tunnel).filter(Tunnel.id == tunnel_id).first()
    if not tunnel:
        raise HTTPException(status_code=404, detail="Tunnel not found")
    
    manager = MANAGERS.get(tunnel.tunnel_type)
    if not manager:
        return {"status": "unknown", "tunnel": tunnel.name}
    
    if tunnel.tunnel_type == "persianshield":
        status_dict = manager.get_all_status()
        if tunnel.name in status_dict:
            return status_dict[tunnel.name]
    else:
        t = manager.get_tunnel(tunnel.name)
        if t:
            return await t.get_status()
    
    return {"status": "unknown", "tunnel": tunnel.name}


# ===== Start / Stop / Restart =====

@router.post("/{tunnel_id}/start")
async def start_tunnel(
    tunnel_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Start a stopped tunnel"""
    tunnel = db.query(Tunnel).filter(Tunnel.id == tunnel_id).first()
    if not tunnel:
        raise HTTPException(status_code=404, detail="Tunnel not found")
    
    manager = MANAGERS.get(tunnel.tunnel_type)
    if not manager:
        raise HTTPException(status_code=400, detail="Unknown tunnel type")
    
    t = manager.get_tunnel(tunnel.name)
    if t:
        success = await t.start()
    else:
        # Recreate from DB config
        config = {
            "iran_ip": tunnel.iran_server_ip,
            "iran_port": tunnel.iran_server_port,
            "foreign_ip": tunnel.foreign_server_ip,
            "foreign_port": tunnel.foreign_server_port,
            "protocol": tunnel.protocol,
            "forward_ports": tunnel.forwarded_ports or [],
        }
        success = await manager.create_tunnel(tunnel.name, config)
    
    if success:
        tunnel.is_active = True
        tunnel.status = "connected"
        db.commit()
        return {"status": "ok", "message": f"Tunnel {tunnel.name} started"}
    else:
        raise HTTPException(status_code=500, detail="Failed to start tunnel")


@router.post("/{tunnel_id}/stop")
async def stop_tunnel(
    tunnel_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Stop a running tunnel"""
    tunnel = db.query(Tunnel).filter(Tunnel.id == tunnel_id).first()
    if not tunnel:
        raise HTTPException(status_code=404, detail="Tunnel not found")
    
    manager = MANAGERS.get(tunnel.tunnel_type)
    if manager:
        t = manager.get_tunnel(tunnel.name)
        if t:
            await t.stop()
    
    tunnel.is_active = False
    tunnel.status = "disconnected"
    db.commit()
    return {"status": "ok", "message": f"Tunnel {tunnel.name} stopped"}


@router.post("/{tunnel_id}/restart")
async def restart_tunnel(
    tunnel_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Restart a tunnel"""
    tunnel = db.query(Tunnel).filter(Tunnel.id == tunnel_id).first()
    if not tunnel:
        raise HTTPException(status_code=404, detail="Tunnel not found")
    
    manager = MANAGERS.get(tunnel.tunnel_type)
    if manager:
        success = await manager.restart_tunnel(tunnel.name)
        if success:
            tunnel.is_active = True
            tunnel.status = "connected"
            db.commit()
            return {"status": "ok", "message": f"Tunnel {tunnel.name} restarted"}
    
    raise HTTPException(status_code=500, detail="Failed to restart tunnel")


@router.delete("/{tunnel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tunnel(
    tunnel_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Delete tunnel"""
    tunnel = db.query(Tunnel).filter(Tunnel.id == tunnel_id).first()
    if not tunnel:
        raise HTTPException(status_code=404, detail="Tunnel not found")
    
    # Stop and remove from manager
    manager = MANAGERS.get(tunnel.tunnel_type)
    if manager:
        await manager.remove_tunnel(tunnel.name)
    
    db.delete(tunnel)
    db.commit()
    return None
