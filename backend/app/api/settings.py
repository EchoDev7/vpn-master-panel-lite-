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
        # =============================================
        # OpenVPN — Iran Anti-Censorship Defaults
        # =============================================

        # --- Network & Server ---
        "ovpn_protocol": "udp",
        "ovpn_port": "1194",
        "ovpn_dev": "tun",
        "ovpn_dev_type": "tun",
        "ovpn_topology": "subnet",
        "ovpn_server_subnet": "10.8.0.0",
        "ovpn_server_netmask": "255.255.255.0",
        "ovpn_max_clients": "100",
        "ovpn_server_ip": "",                # Override public IP

        # --- Connectivity & Reliability ---
        "ovpn_keepalive_interval": "10",
        "ovpn_keepalive_timeout": "60",
        "ovpn_float": "1",                   # Allow client IP float
        "ovpn_comp_lzo": "no",               # Deprecated but kept for legacy
        "ovpn_compress": "",                 # "lzo", "lz4", "lz4-v2" or empty to disable
        "ovpn_allow_compression": "no",      # Security: disable checking compression
        "ovpn_pers_tun": "1",
        "ovpn_pers_key": "1",
        "ovpn_user": "nobody",
        "ovpn_group": "nogroup",

        # --- Interaction & Timeouts ---
        "ovpn_reneg_sec": "3600",            # TLS renegotiation
        "ovpn_hand_window": "60",            # Handshake window
        "ovpn_tran_window": "3600",          # Transition window
        "ovpn_tls_timeout": "2",             # Packet retransmit timeout
        "ovpn_connect_retry": "5",
        "ovpn_connect_retry_max": "0",
        "ovpn_server_poll_timeout": "10",
        "ovpn_explicit_exit_notify": "1",    # Notify server on disconnect (UDP)

        # --- Cryptography & Security ---
        "ovpn_cipher": "AES-256-GCM",        # Main cipher (NCP)
        "ovpn_data_ciphers": "AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305",
        "ovpn_data_ciphers_fallback": "AES-256-GCM",
        "ovpn_auth_digest": "SHA256",
        "ovpn_tls_version_min": "1.2",
        "ovpn_tls_cert_profile": "preferred",
        "ovpn_tls_ciphers": "TLS-ECDHE-ECDSA-WITH-AES-256-GCM-SHA384:TLS-ECDHE-RSA-WITH-AES-256-GCM-SHA384",
        "ovpn_tls_cipher_suites": "TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256",
        "ovpn_ecdh_curve": "secp384r1",      # Strong curve
        "ovpn_dh_file": "none",              # Disable DH (use ECDH)
        "ovpn_crl_verify": "crl.pem",        # Certificate Revocation List

        # --- TLS Control Channel Obfuscation ---
        "ovpn_tls_control_channel": "tls-crypt", # none, tls-auth, tls-crypt, tls-crypt-v2
        "ovpn_auth_nocache": "1",            # Don't cache passwords in memory

        # --- Anti-Censorship & DPI Evasion ---
        "ovpn_scramble": "1",                # XOR Scramble (Unofficial patch)
        "ovpn_scramble_password": "vpnmaster", 
        "ovpn_fragment": "0",                # Fragment packets
        "ovpn_mssfix": "1360",               # Adjust based on MTU
        "ovpn_tun_mtu": "1400",
        "ovpn_mtu_disc": "yes",              # MTU discovery

        # --- Routing & DNS (Push Options) ---
        "ovpn_redirect_gateway": "1",        # def1 bypass-dhcp
        "ovpn_dns": "1.1.1.1,8.8.8.8",
        "ovpn_block_outside_dns": "0",       # Windows leak protection
        "ovpn_client_to_client": "0",
        "ovpn_push_routes": "",              # e.g. "192.168.1.0 255.255.255.0"
        "ovpn_push_remove_routes": "",       # Remove specific routes

        # --- Logging & Management ---
        "ovpn_verb": "3",                    # 0-9
        "ovpn_mute": "20",                   # Silence repeating messages
        "ovpn_status_log": "/var/log/openvpn/openvpn-status.log",
        "ovpn_status_version": "2",          # Status file format version
        "ovpn_management": "127.0.0.1 7505", # Management interface
        
        # --- Proxy Configuration ---
        "ovpn_proxy_type": "none",           # none / socks / http
        "ovpn_proxy_address": "",
        "ovpn_proxy_port": "",
        
        # --- Multi-Remote (Failover) ---
        "ovpn_remote_servers": "",           # ip:port:proto, ip:port:proto
        
        # --- Advanced Custom Config ---
        "ovpn_custom_client_config": "",     # Raw text
        "ovpn_custom_server_config": "",     # Raw text

        # =============================================
        # WireGuard — Iran Anti-Censorship Defaults
        # =============================================

        # Network
        "wg_port": "51820",
        "wg_mtu": "1380",
        "wg_interface": "wg0",
        "wg_subnet": "10.66.66.0",
        "wg_subnet_mask": "24",

        # DNS
        "wg_dns": "1.1.1.1,8.8.8.8",

        # Security
        "wg_preshared_key_enabled": "1",
        "wg_fwmark": "",

        # Connection
        "wg_persistent_keepalive": "25",
        "wg_save_config": "1",

        # Routing
        "wg_allowed_ips": "0.0.0.0/0,::/0",
        "wg_table": "auto",
        "wg_post_up": "",
        "wg_post_down": "",

        # Anti-Censorship / Obfuscation
        "wg_obfuscation_type": "none",
        "wg_obfuscation_port": "443",
        "wg_obfuscation_domain": "",

        # WARP Integration
        "wg_warp_enabled": "0",
        "wg_warp_mode": "proxy",
        "wg_block_iran_ips": "0",

        # Server
        "wg_endpoint_ip": "",

        # Advanced
        "wg_custom_client_config": "",
        "wg_custom_server_config": "",

        # =============================================
        # General — Panel Features
        # =============================================
        "admin_contact": "",

        # Subscription Links (3x-ui/Marzban/Hiddify-style)
        "subscription_enabled": "0",
        "subscription_base_url": "",
        "subscription_format": "v2ray",
        "subscription_update_interval": "24",
        "config_export_qr": "1",
        "config_export_uri": "1",

        # Telegram Bot Integration
        "telegram_enabled": "0",
        "telegram_bot_token": "",
        "telegram_admin_chat_id": "",
        "telegram_notify_user_created": "1",
        "telegram_notify_user_expired": "1",
        "telegram_notify_traffic_warning": "1",
        "telegram_notify_server_down": "1",
        "telegram_auto_backup": "0",

        # Smart Proxy (Hiddify-style)
        "smart_proxy_enabled": "0",
        "smart_proxy_mode": "bypass_iran",
        "smart_proxy_bypass_domains": "",
        "smart_proxy_bypass_ips": "",

        # Periodic Traffic Limits (Marzban-style)
        "periodic_traffic_enabled": "0",
        "periodic_traffic_type": "monthly",
        "periodic_traffic_reset_day": "1",
        "traffic_exceed_action": "suspend",
        "traffic_warning_percent": "80",
    }
    
    for key, value in defaults.items():
        if not db.query(Setting).filter(Setting.key == key).first():
            category = "general"
            if key.startswith("ovpn_"): category = "openvpn"
            elif key.startswith("wg_"): category = "wireguard"
            db.add(Setting(key=key, value=value, category=category))
    db.commit()


# =============================================
# PKI Management
# =============================================

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


@router.get("/pki/info")
async def get_pki_info(
    current_admin: User = Depends(get_current_admin)
):
    """Get CA certificate information"""
    from ..services.openvpn import openvpn_service
    return openvpn_service.get_ca_info()


# =============================================
# Server Config Preview & Apply
# =============================================

@router.get("/server-config/preview")
async def preview_server_config(
    current_admin: User = Depends(get_current_admin)
):
    """Preview the generated OpenVPN server.conf"""
    from ..services.openvpn import openvpn_service
    try:
        config = openvpn_service.generate_server_config()
        return {"content": config, "filename": "server.conf"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/server-config/apply")
async def apply_server_config(
    current_admin: User = Depends(get_current_admin)
):
    """Generate and write server.conf to /etc/openvpn/server.conf"""
    from ..services.openvpn import openvpn_service
    import os
    
    try:
        config = openvpn_service.generate_server_config()
        
        # Write to standard OpenVPN location
        config_path = "/etc/openvpn/server.conf"
        
        # Also save a copy in our data dir
        backup_path = os.path.join(openvpn_service.DATA_DIR, "server.conf")
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        with open(backup_path, "w") as f:
            f.write(config)
        
        # Try to write to system path (may need root)
        try:
            # SAFETY CHECK: Ensure we are NOT overwriting keys
            if "BEGIN PRIVATE KEY" in config:
                raise ValueError("Security violation: Attempted to write private key to server.conf")
                
            with open(config_path, "w") as f:
                f.write(config)
            system_written = True
            
            # Auto-Restart Service
            try:
                import subprocess
                subprocess.run(["systemctl", "restart", "openvpn@server"], check=True)
                restart_status = "Service restarted successfully."
            except Exception as e:
                restart_status = f"Service restart failed: {str(e)}"
                
        except PermissionError:
            system_written = False
            restart_status = "Permission denied: Cannot specific system path."
        
        return {
            "message": "Server config generated",
            "system_path": config_path if system_written else None,
            "backup_path": backup_path,
            "system_written": system_written,
            "restart_status": restart_status,
            "hint": "Configuration applied." if system_written else 
                    f"Copy manually: sudo cp {backup_path} {config_path} && sudo systemctl restart openvpn@server"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/openvpn/version")
async def get_openvpn_version(
    current_admin: User = Depends(get_current_admin)
):
    """Get OpenVPN version installed on system"""
    import subprocess
    try:
        cleanup = subprocess.check_output("openvpn --version | head -n 1", shell=True).decode().strip()
        return {"version": cleanup}
    except:
        return {"version": "Not Found / Not Installed"}


# =============================================
# WireGuard Server Config, Keys & Status
# =============================================

@router.get("/wg-server-config/preview")
async def preview_wg_server_config(
    current_admin: User = Depends(get_current_admin)
):
    """Preview the generated WireGuard wg0.conf"""
    from ..services.wireguard import wireguard_service
    try:
        config = wireguard_service.generate_server_config()
        return {"content": config, "filename": "wg0.conf"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/wg-server-config/apply")
async def apply_wg_server_config(
    current_admin: User = Depends(get_current_admin)
):
    """Generate and write wg0.conf to /etc/wireguard/"""
    from ..services.wireguard import wireguard_service
    import os

    try:
        config = wireguard_service.generate_server_config()
        settings = wireguard_service._load_settings()
        interface = settings.get("wg_interface", "wg0")

        config_path = f"/etc/wireguard/{interface}.conf"
        backup_path = os.path.join(wireguard_service.DATA_DIR, f"{interface}.conf")
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)

        with open(backup_path, "w") as f:
            f.write(config)

        try:
            with open(config_path, "w") as f:
                f.write(config)
            system_written = True
        except PermissionError:
            system_written = False

        return {
            "message": "WireGuard server config generated",
            "system_path": config_path if system_written else None,
            "backup_path": backup_path,
            "system_written": system_written,
            "hint": f"Run 'sudo wg-quick down {interface} && sudo wg-quick up {interface}' to apply" if system_written else
                    f"Copy manually: sudo cp {backup_path} {config_path} && sudo wg-quick up {interface}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wg-status")
async def get_wg_status(
    current_admin: User = Depends(get_current_admin)
):
    """Get WireGuard interface status and all peer stats"""
    from ..services.wireguard import wireguard_service
    return wireguard_service.get_interface_status()


@router.post("/wg-keys/regenerate")
async def regenerate_wg_keys(
    current_admin: User = Depends(get_current_admin)
):
    """Regenerate WireGuard server keypair"""
    from ..services.wireguard import wireguard_service
    try:
        keys = wireguard_service.regenerate_server_keys()
        return {
            "message": "WireGuard server keys regenerated",
            "public_key": keys["public_key"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wg-obfuscation/script")
async def get_obfuscation_script(
    current_admin: User = Depends(get_current_admin)
):
    """Get server-side obfuscation setup script"""
    from ..services.wireguard import wireguard_service
    script = wireguard_service.generate_obfuscation_setup_script()
    return {"content": script, "filename": "setup_obfuscation.sh"}
