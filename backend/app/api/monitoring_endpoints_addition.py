# Add these new endpoints to monitoring.py

@router.get("/protocol-distribution")
async def get_protocol_distribution(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get distribution of users by VPN protocol"""
    openvpn_count = db.query(ConnectionLog).filter(
        ConnectionLog.is_active == True,
        ConnectionLog.protocol == "openvpn"
    ).count()
    
    wireguard_count = db.query(ConnectionLog).filter(
        ConnectionLog.is_active == True,
        ConnectionLog.protocol == "wireguard"
    ).count()
    
    return {
        "openvpn": openvpn_count,
        "wireguard": wireguard_count,
        "total": openvpn_count + wireguard_count
    }
