from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy.orm import Session
from datetime import datetime
import os

from ..database import get_db
from ..models.user import User
from ..services.openvpn import openvpn_service
from ..services.wireguard import wireguard_service

router = APIRouter()

# Simple HTML Template for F2 Self-Service Portal
# Note: In a real app this might be a React page, but the user requested a specific context structure
# and implied a server-side rendered approach or at least an endpoint to serve this data.
# We'll serve a simple HTML page that hydrates itself or displays this info.

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VPN Subscription</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 20px; }
        .status-badge { padding: 5px 10px; border-radius: 20px; font-size: 0.9em; }
        .status-active { background: #d1fae5; color: #065f46; }
        .status-expired { background: #fee2e2; color: #991b1b; }
        .card { background: #f9fafb; padding: 15px; border-radius: 8px; margin-bottom: 10px; }
        .btn { display: block; width: 100%; padding: 12px; margin: 10px 0; border: none; border-radius: 8px; font-size: 1.1em; cursor: pointer; text-align: center; text-decoration: none; color: white; transition: opacity 0.2s; }
        .btn-ovpn { background: #ea580c; }
        .btn-wg { background: #2563eb; }
        .btn:hover { opacity: 0.9; }
        .qr-code { text-align: center; margin: 20px 0; }
        .progress-bar { width: 100%; height: 10px; background: #e5e7eb; border-radius: 5px; overflow: hidden; }
        .progress-fill { height: 100%; background: #10b981; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>پنل کاربری</h2>
            <p id="username">User</p>
            <span id="status" class="status-badge">Loading...</span>
        </div>

        <div class="card">
            <p>📅 انقضا: <span id="expiry">--</span> (<span id="days">--</span> روز باقی‌مانده)</p>
            <p>📊 مصرف: <span id="usage">--</span> / <span id="limit">--</span> GB</p>
            <div class="progress-bar">
                <div id="progress" class="progress-fill" style="width: 0%"></div>
            </div>
        </div>

        <div id="actions">
            <button class="btn btn-ovpn" onclick="installConfig('openvpn')">📱 نصب OpenVPN</button>
            <button class="btn btn-wg" onclick="installConfig('wireguard')">⚡ نصب WireGuard</button>
        </div>

        <div id="wg-qr" class="qr-code" style="display:none">
            <h3>WireGuard QR Code</h3>
            <div id="qrcode"></div>
        </div>
    </div>

    <script>
        // Data populated from backend
        const DATA = {{DATA_JSON}};

        document.getElementById('username').innerText = DATA.username;
        document.getElementById('status').innerText = DATA.status;
        document.getElementById('status').className = 'status-badge status-' + DATA.status.toLowerCase();
        document.getElementById('expiry').innerText = DATA.expiry_date;
        document.getElementById('days').innerText = DATA.days_remaining;
        document.getElementById('usage').innerText = DATA.data_used_gb;
        document.getElementById('limit').innerText = DATA.data_limit_gb;
        document.getElementById('progress').style.width = DATA.data_percent + '%';

        function getInstallLink(protocol) {
            const configUrl = window.location.origin + DATA.subscription_url + '/' + protocol;
            const ua = navigator.userAgent;
            
            if (protocol === 'openvpn') {
                if (/iPhone|iPad|iPod|Macintosh/.test(ua)) {
                    return `openvpn://import-profile/${configUrl}`;
                }
                return configUrl;
            }
            if (protocol === 'wireguard') {
                return `wireguard://${configUrl}`; // Deep link
            }
            return configUrl;
        }

        function installConfig(protocol) {
            const link = getInstallLink(protocol);
            if (protocol === 'openvpn' && /iPhone|iPad|Mac/.test(ua)) {
                 window.location.href = link;
                 setTimeout(() => { window.location.href = 'https://apps.apple.com/app/openvpn-connect/id590379981'; }, 2000);
            } else {
                 if (protocol === 'wireguard') {
                     // Toggle QR for WG on desktop
                     const qrDiv = document.getElementById('wg-qr');
                     qrDiv.style.display = 'block';
                     if (!qrDiv.hasChildNodes()) {
                         new QRCode(document.getElementById("qrcode"), {
                             text: DATA.wg_config || link,
                             width: 200,
                             height: 200
                         });
                     }
                 }
                 // Also download file
                 const a = document.createElement('a');
                 a.href = link;
                 a.download = `vpn-config.${protocol === 'openvpn' ? 'ovpn' : 'conf'}`;
                 a.click();
            }
        }
    </script>
</body>
</html>
"""

@router.get("/{token}", response_class=HTMLResponse)
async def get_subscription_page(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.subscription_token == token).first()
    if not user:
        raise HTTPException(status_code=404, detail="Subscription not found")

    import json
    
    # Calculate stats
    remaining = 999
    if user.expiry_date:
        remaining = (user.expiry_date - datetime.utcnow()).days
        
    limit_gb = user.data_limit_gb if user.data_limit_gb > 0 else "Unlimited"
    percent = 0
    if user.data_limit_gb > 0:
        percent = min(100, (user.data_usage_gb / user.data_limit_gb * 100))
        
    context = {
        "username": user.username,
        "status": user.status.value,
        "data_used_gb": round(user.data_usage_gb, 2),
        "data_limit_gb": limit_gb,
        "data_percent": percent,
        "expiry_date": user.expiry_date.strftime("%Y-%m-%d") if user.expiry_date else "Never",
        "days_remaining": remaining,
        "ovpn_url": f"/sub/{token}/openvpn",
        "wg_url": f"/sub/{token}/wireguard",
        "subscription_url": f"/sub/{token}",
        # Need WG config for QR
        "wg_config": "" 
    }
    
    # Pre-generate WG config for QR code if requested
    if user.wireguard_enabled and user.wireguard_private_key:
         try:
             # We generate client config text here for the QR code
             context["wg_config"] = wireguard_service.generate_client_config(
                 user.wireguard_private_key, 
                 user.wireguard_ip, 
                 user.wireguard_preshared_key
             )
         except:
             pass

    # Inject JSON into template (simple hydration)
    html = HTML_TEMPLATE.replace("{{DATA_JSON}}", json.dumps(context))
    return html

@router.get("/{token}/openvpn", response_class=PlainTextResponse)
async def get_openvpn_config(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.subscription_token == token).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not user.openvpn_enabled:
        raise HTTPException(status_code=400, detail="OpenVPN disabled for this user")
        
    config = openvpn_service.generate_client_config(user.username)
    return PlainTextResponse(content=config, media_type="application/x-openvpn-profile")

@router.get("/{token}/wireguard", response_class=PlainTextResponse)
async def get_wireguard_config(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.subscription_token == token).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not user.wireguard_enabled:
        raise HTTPException(status_code=400, detail="WireGuard disabled for this user")
        
    config = wireguard_service.generate_client_config(
        user.wireguard_private_key,
        user.wireguard_ip,
        user.wireguard_preshared_key
    )
    return PlainTextResponse(content=config, media_type="text/plain")
