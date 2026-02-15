"""
Servers API Endpoints - Manage VPN servers and nodes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from ..database import get_db
from ..models.user import User
from ..models.vpn_server import VPNServer, ServerType, ServerStatus
from ..utils.security import get_current_admin

router = APIRouter()


# Request/Response Models
class ServerCreate(BaseModel):
    name: str
    hostname: str
    public_ip: str
    server_type: ServerType = ServerType.NODE
    location: Optional[str] = None
    
    ssh_host: Optional[str] = None
    ssh_port: int = 22
    ssh_username: Optional[str] = "root"
    ssh_password: Optional[str] = None
    
    openvpn_enabled: bool = True
    openvpn_port: int = 1194
    wireguard_enabled: bool = True
    wireguard_port: int = 51820


class ServerResponse(BaseModel):
    id: int
    name: str
    hostname: str
    public_ip: str
    server_type: str
    location: Optional[str]
    status: str
    
    cpu_usage: float
    ram_usage: float
    disk_usage: float
    
    openvpn_enabled: bool
    wireguard_enabled: bool
    l2tp_enabled: bool
    cisco_enabled: bool
    
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.post("/", response_model=ServerResponse, status_code=status.HTTP_201_CREATED)
async def create_server(
    server_data: ServerCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Create new VPN server/node"""
    existing = db.query(VPNServer).filter(VPNServer.name == server_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Server name already exists"
        )
    
    server = VPNServer(**server_data.model_dump())
    db.add(server)
    db.commit()
    db.refresh(server)
    
    return server


@router.get("/", response_model=List[ServerResponse])
async def list_servers(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """List all servers"""
    servers = db.query(VPNServer).all()
    return servers


@router.get("/{server_id}", response_model=ServerResponse)
async def get_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get server by ID"""
    server = db.query(VPNServer).filter(VPNServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Delete server"""
    server = db.query(VPNServer).filter(VPNServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    db.delete(server)
    db.commit()
    return None
