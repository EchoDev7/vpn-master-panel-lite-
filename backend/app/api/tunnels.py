"""
Tunnels API Endpoints - Manage Iran-Foreign tunnels
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..database import get_db
from ..models.user import User
from ..models.vpn_server import Tunnel
from ..utils.security import get_current_admin
from ..tunnels.backhaul import BackhaulManager
from ..tunnels.persianshield import PersianShieldManager

router = APIRouter()

# Global tunnel managers
backhaul_manager = BackhaulManager()
shield_manager = PersianShieldManager()


class TunnelCreate(BaseModel):
    name: str
    tunnel_type: str  # backhaul, rathole, frp, chisel, persianshield
    protocol: str = "tcp"
    
    server_id: int
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


@router.post("/", response_model=TunnelResponse, status_code=status.HTTP_201_CREATED)
async def create_tunnel(
    tunnel_data: TunnelCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Create and establish new tunnel"""
    existing = db.query(Tunnel).filter(Tunnel.name == tunnel_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tunnel name already exists"
        )
    
    # Create tunnel record
    tunnel = Tunnel(**tunnel_data.model_dump())
    db.add(tunnel)
    db.commit()
    db.refresh(tunnel)
    
    # Start actual tunnel based on type
    try:
        if tunnel_data.tunnel_type == "backhaul":
            config = {
                "iran_ip": tunnel_data.iran_server_ip,
                "iran_port": tunnel_data.iran_server_port,
                "protocol": tunnel_data.protocol,
                "forward_ports": tunnel_data.forwarded_ports or [],
                "token": tunnel_data.config.get("token", "backhaul-secret")
            }
            success = await backhaul_manager.create_tunnel(tunnel_data.name, config, mode="client")
            
        elif tunnel_data.tunnel_type == "persianshield":
            config = {
                "iran_host": tunnel_data.iran_server_ip,
                "iran_port": tunnel_data.iran_server_port,
                "foreign_host": tunnel_data.foreign_server_ip,
                "foreign_port": tunnel_data.foreign_server_port,
                "domain_fronting": tunnel_data.domain_fronting_enabled,
                "fronting_domain": tunnel_data.domain_fronting_domain or "cloudflare.com",
                "secret": tunnel_data.config.get("secret", "persianshield")
            }
            success = await shield_manager.create_tunnel(tunnel_data.name, config)
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tunnel type '{tunnel_data.tunnel_type}' not yet implemented"
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start tunnel: {str(e)}"
        )
    
    return tunnel


@router.get("/", response_model=List[TunnelResponse])
async def list_tunnels(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """List all tunnels"""
    tunnels = db.query(Tunnel).all()
    return tunnels


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
    
    # Get status from appropriate manager
    if tunnel.tunnel_type == "backhaul":
        bt = backhaul_manager.get_tunnel(tunnel.name)
        if bt:
            return await bt.get_status()
    
    elif tunnel.tunnel_type == "persianshield":
        status_dict = shield_manager.get_all_status()
        if tunnel.name in status_dict:
            return status_dict[tunnel.name]
    
    return {"status": "unknown", "tunnel": tunnel.name}


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
    
    # Stop tunnel
    if tunnel.tunnel_type == "backhaul":
        await backhaul_manager.remove_tunnel(tunnel.name)
    elif tunnel.tunnel_type == "persianshield":
        await shield_manager.remove_tunnel(tunnel.name)
    
    db.delete(tunnel)
    db.commit()
    return None
