from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from ..services.openvpn_mgmt import openvpn_mgmt
from ..utils.security import get_current_active_user, get_current_admin_user

router = APIRouter()

@router.get("/active", response_model=List[Dict[str, Any]])
async def get_active_connections(
    current_user = Depends(get_current_active_user)
):
    """
    Get real-time list of active OpenVPN connections via Management Interface.
    Replaces the slow log-parsing method.
    """
    try:
        connections = openvpn_mgmt.get_active_connections()
        return connections
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/kill/{common_name}")
async def kill_connection(
    common_name: str,
    admin_user = Depends(get_current_admin_user)
):
    """
    Force kill a client connection (Admin only)
    """
    success = openvpn_mgmt.kill_client(common_name)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to kill connection or user not found")
    return {"status": "success", "message": f"Connection {common_name} killed"}
