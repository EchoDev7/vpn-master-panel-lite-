"""
Settings API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict

from ..database import get_db
from ..models.setting import Setting
from ..models.user import User
from ..utils.security import get_current_admin

router = APIRouter()

class SettingUpdate(BaseModel):
    value: str

@router.get("/", response_model=Dict[str, str])
async def get_settings(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get all settings as key-value pairs"""
    query = db.query(Setting)
    if category:
        query = query.filter(Setting.category == category)
    
    settings = query.all()
    return {s.key: s.value for s in settings}

@router.post("/", status_code=status.HTTP_200_OK)
async def update_settings(
    settings_data: Dict[str, str],
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Update multiple settings"""
    for key, value in settings_data.items():
        setting = db.query(Setting).filter(Setting.key == key).first()
        if setting:
            setting.value = value
        else:
            # Create if not exists (auto-register)
            # Determine category based on key prefix
            category = "general"
            if key.startswith("ovpn_"): category = "openvpn"
            elif key.startswith("wg_"): category = "wireguard"
            
            new_setting = Setting(key=key, value=str(value), category=category)
            db.add(new_setting)
            
    db.commit()
    return {"message": "Settings updated successfully"}

# Initialize default settings
def init_default_settings(db: Session):
    defaults = {
        # OpenVPN
        "ovpn_port": "1194",
        "ovpn_protocol": "udp", # udp, tcp, both
        "ovpn_dns": "1.1.1.1,8.8.8.8",
        "ovpn_scramble": "0", # 0=disabled, 1=enabled (xor)
        "ovpn_mtu": "1500",
        
        # WireGuard
        "wg_port": "51820",
        "wg_dns": "1.1.1.1,8.8.8.8",
        "wg_mtu": "1420", # Optimized for Iran
        "wg_endpoint_ip": "", # Empty = auto-detect
        
        # General
        "admin_contact": ""
    }
    
    for key, value in defaults.items():
        if not db.query(Setting).filter(Setting.key == key).first():
            db.add(Setting(key=key, value=value, category="general"))
    db.commit()

@router.post("/pki/regenerate", status_code=status.HTTP_200_OK)
async def regenerate_pki(
    current_admin: User = Depends(get_current_admin)
):
    """Regenerate OpenVPN CA and Server Certificates"""
    from ..services.openvpn import openvpn_service
    try:
        openvpn_service.regenerate_pki()
        return {"message": "PKI regenerated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
