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
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            --primary: #2563eb;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --bg: #f3f4f6;
            --card-bg: #ffffff;
            --text: #1f2937;
        }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 15px; line-height: 1.6; }
        .container { max-width: 500px; margin: 0 auto; background: var(--card-bg); padding: 25px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 25px; border-bottom: 2px solid #f0f0f0; padding-bottom: 15px; }
        .header h2 { margin: 0 0 10px 0; color: var(--primary); }
        .badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.85em; font-weight: bold; }
        .badge-active { background: #d1fae5; color: #065f46; }
        .badge-expired { background: #fee2e2; color: #991b1b; }
        
        .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px; }
        .stat-card { background: #f9fafb; padding: 15px; border-radius: 12px; text-align: center; border: 1px solid #e5e7eb; }
        .stat-val { display: block; font-size: 1.2em; font-weight: bold; margin-bottom: 5px; color: var(--primary); }
        .stat-label { font-size: 0.8em; color: #6b7280; }
        
        .progress-container { margin: 20px 0; }
        .progress-bar { width: 100%; height: 12px; background: #e5e7eb; border-radius: 6px; overflow: hidden; margin-top: 5px; }
        .progress-fill { height: 100%; background: var(--success); transition: width 0.5s ease; }
        
        .actions { display: flex; flex-direction: column; gap: 12px; }
        .btn { display: flex; align-items: center; justify-content: center; width: 100%; padding: 14px; border: none; border-radius: 12px; font-size: 1em; font-weight: 600; cursor: pointer; color: white; transition: transform 0.1s, opacity 0.2s; text-decoration: none; gap: 10px; }
        .btn:active { transform: scale(0.98); }
        .btn-ovpn { background: linear-gradient(135deg, #ea580c, #c2410c); box-shadow: 0 4px 10px rgba(234, 88, 12, 0.3); }
        .btn-wg { background: linear-gradient(135deg, #2563eb, #1d4ed8); box-shadow: 0 4px 10px rgba(37, 99, 235, 0.3); }
        
        .qr-section { margin-top: 25px; border-top: 1px solid #e5e7eb; padding-top: 20px; text-align: center; display: none; }
        #qrcode { display: inline-block; padding: 10px; background: white; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.05); }
        
        .guide-section { margin-top: 25px; background: #f8fafc; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; }
        .guide-title { font-weight: bold; margin-bottom: 10px; display: flex; align-items: center; gap: 8px; cursor: pointer; }
        .guide-content { font-size: 0.9em; color: #475569; display: none; }
        .guide-content.show { display: block; }
        .guide-os-btn { font-size: 0.8em; margin: 2px; padding: 4px 8px; background: #e2e8f0; border-radius: 4px; border: none; cursor: pointer; }
        .guide-os-btn.active { background: var(--primary); color: white; }
        
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2><i class="fas fa-shield-alt"></i> پنل اشتراک</h2>
            <div style="font-size: 1.1em; margin: 10px 0;" id="username">User</div>
            <span id="status" class="badge">Loading...</span>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <span class="stat-val" id="days">--</span>
                <span class="stat-label">روز باقی‌مانده</span>
            </div>
            <div class="stat-card">
                <span class="stat-val" id="usage">--</span>
                <span class="stat-label">گیگابایت مصرف</span>
            </div>
        </div>

        <div class="progress-container">
            <div style="display:flex; justify-content:space-between; font-size:0.85em; margin-bottom:5px;">
                <span>مصرف دیتا</span>
                <span><span id="percent">0</span>%</span>
            </div>
            <div class="progress-bar">
                <div id="progress" class="progress-fill" style="width: 0%"></div>
            </div>
            <div style="text-align:right; font-size:0.8em; color:#666; margin-top:3px;">
                کل اعتبار: <span id="limit">--</span> GB
            </div>
        </div>

        <div class="actions">
            <button class="btn btn-ovpn" onclick="installConfig('openvpn')">
                <i class="fab fa-android"></i> <i class="fab fa-apple"></i> اتصال OpenVPN
            </button>
            <button class="btn btn-wg" onclick="installConfig('wireguard')">
                <i class="fas fa-bolt"></i> اتصال WireGuard
            </button>
        </div>

        <div id="wg-qr" class="qr-section">
            <h3 style="font-size:1em; margin-bottom:15px; color:#444;">اسکن با نرم‌افزار WireGuard</h3>
            <div id="qrcode"></div>
        </div>
        
        <div class="guide-section">
            <div class="guide-title" onclick="toggleGuide()">
                <i class="fas fa-book-reader"></i> راهنمای اتصال
                <span style="margin-right:auto; font-size:0.8em;">▼</span>
            </div>
            <div id="guide-content" class="guide-content">
                <div style="margin-bottom:10px; display:flex; gap:5px; flex-wrap:wrap;">
                    <button class="guide-os-btn active" onclick="showOS('android')">Android</button>
                    <button class="guide-os-btn" onclick="showOS('ios')">iOS</button>
                    <button class="guide-os-btn" onclick="showOS('windows')">Windows</button>
                </div>
                
                <div id="guide-android">
                    1. برنامه <b>OpenVPN Connect</b> را از گوگل پلی دانلود کنید.<br>
                    2. دکمه "اتصال OpenVPN" در بالا را بزنید.<br>
                    3. فایل کانفیگ دانلود شده را در برنامه وارد (Import) کنید.<br>
                    4. دکمه اتصال را بزنید.
                </div>
                <div id="guide-ios" style="display:none">
                    1. برنامه <b>OpenVPN Connect</b> را از اپ استور دانلود کنید.<br>
                    2. دکمه "اتصال OpenVPN" در بالا را بزنید (لینک خودکار باز می‌شود).<br>
                    3. در برنامه گزینه ADD را بزنید.<br>
                    4. دکمه اتصال را بزنید.
                </div>
                <div id="guide-windows" style="display:none">
                    1. برنامه <b>OpenVPN Connect</b> نسخه ویندوز را نصب کنید.<br>
                    2. فایل کانفیگ را با دکمه بالا دانلود کنید.<br>
                    3. فایل را روی آیکون برنامه در Taskbar بکشید یا Import کنید.<br>
                </div>
            </div>
        </div>
    </div>

    <script>
        const DATA = {{DATA_JSON}};

        // Hydrate Data
        document.getElementById('username').innerText = DATA.username + ' خوش آمدید';
        document.getElementById('status').innerText = DATA.status === 'active' ? 'فعال' : 'غیرفعال';
        document.getElementById('status').className = 'badge ' + (DATA.status === 'active' ? 'badge-active' : 'badge-expired');
        document.getElementById('days').innerText = DATA.days_remaining;
        document.getElementById('usage').innerText = DATA.data_used_gb;
        document.getElementById('limit').innerText = DATA.data_limit_gb;
        document.getElementById('percent').innerText = Math.round(DATA.data_percent);
        document.getElementById('progress').style.width = DATA.data_percent + '%';

        // Colorize Progress
        if(DATA.data_percent > 90) document.getElementById('progress').style.background = '#ef4444';
        else if(DATA.data_percent > 70) document.getElementById('progress').style.background = '#f59e0b';

        function getInstallLink(protocol) {
            const configUrl = window.location.origin + DATA.subscription_url + '/' + protocol;
            const ua = navigator.userAgent;
            
            if (protocol === 'openvpn') {
                if (/iPhone|iPad|iPod|Macintosh/.test(ua)) {
                    // Deep Link for OpenVPN Connect on Apple devices
                    return `openvpn://import-profile/${configUrl}`;
                }
                return configUrl;
            }
            if (protocol === 'wireguard') {
                return `wireguard://${configUrl}`; // Deep link attempts
            }
            return configUrl;
        }

        function installConfig(protocol) {
            const link = getInstallLink(protocol);
            const ua = navigator.userAgent;
            
            if (protocol === 'openvpn' && /iPhone|iPad|Mac/.test(ua)) {
                 window.location.href = link;
                 // Fallback to App Store
                 setTimeout(() => { window.location.href = 'https://apps.apple.com/app/openvpn-connect/id590379981'; }, 2500);
            } else {
                 if (protocol === 'wireguard') {
                     // Show QR
                     const qrDiv = document.getElementById('wg-qr');
                     qrDiv.style.display = 'block';
                     if (!qrDiv.querySelector('canvas') && !qrDiv.querySelector('img')) {
                        if(DATA.wg_config) {
                             new QRCode(document.getElementById("qrcode"), {
                                 text: DATA.wg_config,
                                 width: 180,
                                 height: 180
                             });
                        } else {
                            document.getElementById("qrcode").innerText = "کانفیگ وایرگارد موجود نیست";
                        }
                     }
                     // Also download
                     downloadFile(link, `wireguard-${DATA.username}.conf`);
                 } else {
                     downloadFile(link, `openvpn-${DATA.username}.ovpn`);
                 }
            }
        }
        
        function downloadFile(url, filename) {
             const a = document.createElement('a');
             a.href = url;
             a.download = filename;
             document.body.appendChild(a);
             a.click();
             document.body.removeChild(a);
        }
        
        // Guide Logic
        function toggleGuide() {
            document.getElementById('guide-content').classList.toggle('show');
        }
        
        function showOS(os) {
            document.querySelectorAll('.guide-content > div[id^="guide-"]').forEach(el => el.style.display = 'none');
            document.getElementById('guide-' + os).style.display = 'block';
            
            document.querySelectorAll('.guide-os-btn').forEach(el => el.classList.remove('active'));
            event.target.classList.add('active');
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
