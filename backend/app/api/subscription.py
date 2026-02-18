from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session
from datetime import datetime
import base64

from ..database import get_db
from ..models.user import User, UserStatus
from ..services.wireguard import wireguard_service
from ..config import settings

router = APIRouter()

@router.get("/{token}", response_class=HTMLResponse)
async def get_subscription_page(token: str, db: Session = Depends(get_db)):
    """
    Serve the premium subscription page with QR codes, apps, and credentials.
    """
    user = db.query(User).filter(User.subscription_token == token).first()
    if not user:
        return HTMLResponse(content='''
            <!DOCTYPE html>
            <html>
            <head><title>Invalid Link</title><meta name="viewport" content="width=device-width, initial-scale=1"></head>
            <body style="background:#111;color:#eee;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;">
                <div style="text-align:center;">
                    <h1 style="color:#ef4444;">Invalid Subscription Link</h1>
                    <p>This link is invalid or has been revoked. Please contact support.</p>
                </div>
            </body>
            </html>
        ''', status_code=404)

    if user.status != UserStatus.ACTIVE:
        return HTMLResponse(content=f'''
            <!DOCTYPE html>
            <html>
            <head><title>Account Suspended</title><meta name="viewport" content="width=device-width, initial-scale=1"></head>
            <body style="background:#111;color:#eee;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;">
                <div style="text-align:center;">
                    <h1 style="color:#f59e0b;">Account {user.status.title()}</h1>
                    <p>Your account is currently not active.</p>
                </div>
            </body>
            </html>
        ''', status_code=403)

    # --- Data Preparation ---
    usage_gb = user.data_usage_gb
    limit_gb = user.data_limit_gb if user.data_limit_gb > 0 else "Unlimited"
    expiry = user.expiry_date.strftime("%Y-%m-%d") if user.expiry_date else "Never/Unlimited"
    
    # Generate WireGuard Config for QR Code (Client-side rendering)
    wg_config_text = ""
    if user.wireguard_enabled:
        try:
            # Ensure keys exist
            if not user.wireguard_private_key:
                 keys = wireguard_service.generate_keypair()
                 user.wireguard_private_key = keys['private_key']
                 user.wireguard_public_key = keys['public_key']
                 user.wireguard_ip = wireguard_service.allocate_ip()
                 db.commit()

            # Get PSK
            psk = getattr(user, 'wireguard_preshared_key', None)
            
            wg_config_text = wireguard_service.generate_client_config(
                client_private_key=user.wireguard_private_key,
                client_ip=user.wireguard_ip,
                preshared_key=psk
            )
        except Exception as e:
            wg_config_text = f"Error generating config: {str(e)}"
    
    # --- HTML Template ---
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VPN Access: {user.username}</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
        <style>
            :root {{
                --primary: #3b82f6;
                --primary-dark: #2563eb;
                --bg: #0f172a;
                --card-bg: #1e293b;
                --text: #f8fafc;
                --text-muted: #94a3b8;
                --border: #334155;
                --success: #22c55e;
                --warning: #f59e0b;
                --danger: #ef4444;
            }}
            * {{ box-sizing: border-box; outline: none; }}
            body {{
                font-family: 'Inter', sans-serif;
                background-color: var(--bg);
                color: var(--text);
                margin: 0;
                padding: 0;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
                background-image: radial-gradient(circle at top, #1e293b 0%, #0f172a 100%);
            }}
            .container {{
                width: 100%;
                max-width: 600px;
                padding: 20px;
                margin: 0 auto;
            }}
            .card {{
                background-color: var(--card-bg);
                border-radius: 20px;
                padding: 25px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.3);
                border: 1px solid var(--border);
                backdrop-filter: blur(10px);
                margin-bottom: 20px;
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .header h1 {{
                margin: 0 0 5px 0;
                font-size: 28px;
                background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-weight: 800;
            }}
            .user-badge {{
                display: inline-block;
                background: rgba(59, 130, 246, 0.1);
                color: #60a5fa;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 14px;
                font-weight: 500;
                margin-top: 10px;
            }}
            
            /* Stats Grid */
            .stats-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
                margin-bottom: 25px;
            }}
            .stat-box {{
                background: rgba(0,0,0,0.2);
                border-radius: 12px;
                padding: 15px;
                text-align: center;
                border: 1px solid rgba(255,255,255,0.05);
            }}
            .stat-label {{
                font-size: 12px;
                color: var(--text-muted);
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 5px;
            }}
            .stat-value {{
                font-size: 18px;
                font-weight: 700;
                color: var(--text);
            }}
            
            /* Sections */
            .section-title {{
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 1px;
                color: var(--text-muted);
                margin: 20px 0 10px 0;
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            .section-title::after {{
                content: '';
                flex: 1;
                height: 1px;
                background: var(--border);
            }}
            
            /* Download Buttons */
            .app-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 10px;
                margin-bottom: 20px;
            }}
            .app-btn {{
                background: rgba(255,255,255,0.05);
                border: 1px solid var(--border);
                border-radius: 10px;
                padding: 12px;
                text-align: center;
                text-decoration: none;
                color: var(--text);
                transition: all 0.2s;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                gap: 5px;
            }}
            .app-btn:hover {{
                background: rgba(255,255,255,0.1);
                transform: translateY(-2px);
                border-color: var(--text-muted);
            }}
            .app-icon {{ font-size: 20px; margin-bottom: 2px; }}
            .app-name {{ font-size: 14px; font-weight: 500; }}
            
            /* Protocol Actions */
            .protocol-card {{
                background: rgba(15, 23, 42, 0.6);
                border-radius: 12px;
                padding: 15px;
                margin-bottom: 15px;
                border: 1px solid var(--border);
            }}
            .protocol-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }}
            .protocol-name {{
                font-weight: 600;
                color: var(--text);
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            .dot {{ width: 8px; height: 8px; border-radius: 50%; }}
            .dot-ovpn {{ background: #ea580c; box-shadow: 0 0 8px rgba(234, 88, 12, 0.5); }}
            .dot-wg {{ background: #16a34a; box-shadow: 0 0 8px rgba(22, 163, 74, 0.5); }}
            
            .action-btn {{
                display: inline-block;
                width: 100%;
                padding: 12px;
                background: var(--primary);
                color: white;
                text-decoration: none;
                border-radius: 8px;
                text-align: center;
                font-weight: 600;
                font-size: 14px;
                border: none;
                cursor: pointer;
                transition: opacity 0.2s;
            }}
            .action-btn:hover {{ opacity: 0.9; }}
            .btn-outline {{
                background: transparent;
                border: 1px solid var(--border);
                color: var(--text-muted);
            }}
            .btn-outline:hover {{
                border-color: var(--text);
                color: var(--text);
            }}

            /* QR Code */
            #qrcode {{
                background: white;
                padding: 15px;
                border-radius: 12px;
                margin: 15px auto;
                width: fit-content;
                display: none; /* Hidden by default */
            }}
            
            /* Credentials */
            .cred-box {{
                background: rgba(0,0,0,0.3);
                border-radius: 8px;
                padding: 12px;
                margin-bottom: 8px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 14px;
            }}
            .cred-key {{ color: var(--text-muted); }}
            .cred-val {{ font-family: monospace; color: var(--text); font-weight: 600; }}
            .copy-icon {{ cursor: pointer; opacity: 0.6; padding: 4px; }}
            .copy-icon:hover {{ opacity: 1; color: var(--primary); }}

            /* Tabs */
            .tabs {{
                display: flex;
                gap: 10px;
                margin-bottom: 15px;
                border-bottom: 1px solid var(--border);
                padding-bottom: 10px;
            }}
            .tab {{
                cursor: pointer;
                padding: 5px 10px;
                font-size: 14px;
                font-weight: 500;
                color: var(--text-muted);
                border-radius: 6px;
                transition: all 0.2s;
            }}
            .tab.active {{
                background: rgba(59, 130, 246, 0.1);
                color: var(--primary);
            }}

            /* Responsive */
            @media (max-width: 480px) {{
                .stats-grid {{ grid-template-columns: 1fr; }}
                .app-grid {{ grid-template-columns: 1fr 1fr; }} 
            }}

            /* Instructions Tabs */
            .inst-tabs {{
                display: flex;
                justify-content: center;
                gap: 10px;
                margin-bottom: 20px;
                flex-wrap: wrap;
            }}
            .inst-tab {{
                background: rgba(255,255,255,0.05);
                border: 1px solid var(--border);
                color: var(--text-muted);
                padding: 8px 16px;
                border-radius: 20px;
                cursor: pointer;
                font-size: 13px;
                font-weight: 500;
                transition: all 0.2s;
            }}
            .inst-tab:hover {{ background: rgba(255,255,255,0.1); }}
            .inst-tab.active {{
                background: var(--primary);
                color: white;
                border-color: var(--primary);
            }}
            .inst-content {{
                display: none;
                background: rgba(0,0,0,0.2);
                border-radius: 12px;
                padding: 20px;
                border: 1px solid var(--border);
                font-size: 14px;
                line-height: 1.6;
                color: var(--text-muted);
                margin-bottom: 20px;
            }}
            .inst-content.active {{
                display: block;
                animation: fadeIn 0.3s ease;
            }}
            @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(5px); }} to {{ opacity: 1; transform: translateY(0); }} }}
            .step {{ margin-bottom: 12px; display: flex; gap: 12px; align-items: flex-start; }}
            .step:last-child {{ margin-bottom: 0; }}
            .step-num {{ 
                background: rgba(255,255,255,0.1); 
                width: 24px; height: 24px; 
                border-radius: 50%; 
                display: flex; align-items: center; justify-content: center; 
                font-size: 12px; font-weight: bold; color: var(--text);
                flex-shrink: 0;
                margin-top: 2px;
            }}
            .step strong {{ color: var(--text); font-weight: 600; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <div class="header">
                    <h1>Active VPN</h1>
                    <div class="user-badge">{user.username}</div>
                </div>

                <div class="stats-grid">
                    <div class="stat-box">
                        <div class="stat-label">Data Usage</div>
                        <div class="stat-value" style="color: { '#ef4444' if (user.data_limit_gb > 0 and user.data_usage_gb >= user.data_limit_gb) else '#22c55e' }">
                            {usage_gb:.2f} <span style="font-size:12px; color:var(--text-muted)">/ {limit_gb} GB</span>
                        </div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Expires On</div>
                        <div class="stat-value">{expiry}</div>
                    </div>
                </div>

                <!-- Apps -->
                <div class="section-title">Download Apps</div>
                <div class="app-grid">
                    <a href="https://play.google.com/store/apps/details?id=com.wireguard.android" target="_blank" class="app-btn">
                        <span class="app-icon">🤖</span>
                        <span class="app-name">Android (WG)</span>
                    </a>
                    <a href="https://apps.apple.com/us/app/wireguard/id1441195209" target="_blank" class="app-btn">
                        <span class="app-icon">🍎</span>
                        <span class="app-name">iOS (WG)</span>
                    </a>
                    <a href="https://download.wireguard.com/windows/client/latest.msi" target="_blank" class="app-btn">
                        <span class="app-icon">🪟</span>
                        <span class="app-name">Windows</span>
                    </a>
                    <a href="https://itunes.apple.com/us/app/wireguard/id1451685025" target="_blank" class="app-btn">
                        <span class="app-icon">🍏</span>
                        <span class="app-name">macOS</span>
                    </a>
                </div>

                <!-- OpenVPN -->
                {f'''
                <div class="protocol-card">
                    <div class="protocol-header">
                        <span class="protocol-name"><span class="dot dot-ovpn"></span> OpenVPN</span>
                    </div>
                    <a href="/sub/{token}/openvpn" class="action-btn" style="background: #ea580c;">Download .OVPN Profile</a>
                </div>
                ''' if user.openvpn_enabled else ''}

                <!-- WireGuard -->
                {f'''
                <div class="protocol-card">
                    <div class="protocol-header">
                        <span class="protocol-name"><span class="dot dot-wg"></span> WireGuard</span>
                    </div>
                    <div style="display:flex; gap:10px;">
                        <a href="/sub/{token}/wireguard" class="action-btn" style="background:#16a34a; flex:1">Download Config</a>
                        <button onclick="toggleQR()" class="action-btn btn-outline" style="flex:1">Show QR Code</button>
                    </div>
                    <div id="qrcode"></div>
                    <textarea id="wg-config-raw" style="display:none">{wg_config_text}</textarea>
                </div>
                ''' if user.wireguard_enabled else ''}

                <!-- Setup Instructions -->
                <div class="section-title">Setup Instructions</div>
                <div class="inst-tabs">
                    <div class="inst-tab active" onclick="switchTab('android')">Android</div>
                    <div class="inst-tab" onclick="switchTab('ios')">iOS</div>
                    <div class="inst-tab" onclick="switchTab('windows')">Windows</div>
                    <div class="inst-tab" onclick="switchTab('macos')">macOS</div>
                </div>

                <div id="android" class="inst-content active">
                    <div class="step"><div class="step-num">1</div><div>Download <strong>WireGuard</strong> app from Google Play Store.</div></div>
                    <div class="step"><div class="step-num">2</div><div>Open app and tap the <strong>+</strong> button (bottom right).</div></div>
                    <div class="step"><div class="step-num">3</div><div>Select <strong>Scan from QR code</strong> and scan the code above.</div></div>
                    <div class="step"><div class="step-num">4</div><div>Turn on the switch to connect.</div></div>
                </div>

                <div id="ios" class="inst-content">
                    <div class="step"><div class="step-num">1</div><div>Download <strong>WireGuard</strong> app from App Store.</div></div>
                    <div class="step"><div class="step-num">2</div><div>Open app and tap <strong>Add a tunnel</strong>.</div></div>
                    <div class="step"><div class="step-num">3</div><div>Select <strong>Create from QR code</strong> and scan the code above.</div></div>
                    <div class="step"><div class="step-num">4</div><div>Allow VPN configuration if asked, then tap the switch to connect.</div></div>
                </div>

                <div id="windows" class="inst-content">
                    <div class="step"><div class="step-num">1</div><div>Download and install <strong>WireGuard</strong> for Windows.</div></div>
                    <div class="step"><div class="step-num">2</div><div>Download the <strong>Config File</strong> (Green button above).</div></div>
                    <div class="step"><div class="step-num">3</div><div>Open WireGuard app and click <strong>Import tunnel(s) from file</strong>.</div></div>
                    <div class="step"><div class="step-num">4</div><div>Select the downloaded file and click <strong>Activate</strong>.</div></div>
                </div>

                <div id="macos" class="inst-content">
                    <div class="step"><div class="step-num">1</div><div>Download <strong>WireGuard</strong> from Mac App Store.</div></div>
                    <div class="step"><div class="step-num">2</div><div>Download the <strong>Config File</strong> (Green button above).</div></div>
                    <div class="step"><div class="step-num">3</div><div>Open app, click <strong>Import tunnel(s) from file</strong>.</div></div>
                    <div class="step"><div class="step-num">4</div><div>Select the file, allow permission, and click <strong>Activate</strong>.</div></div>
                </div>

                <!-- Credentials -->
                <div class="section-title" id="cred-toggle" style="cursor:pointer" onclick="toggleCreds()">
                    Credentials <span style="font-size:10px; margin-left:auto; opacity:0.5">▼ </span>
                </div>
                <div id="credentials-area" style="display:none">
                    <div class="cred-box">
                        <span class="cred-key">Username</span>
                        <span class="cred-val">{user.username}</span>
                    </div>
                    {f'''
                    <div class="cred-box">
                        <span class="cred-key">IPsec PSK</span>
                        <span class="cred-val">{settings.L2TP_PSK}</span>
                    </div>
                    ''' if user.l2tp_enabled or user.cisco_enabled else ''}
                    {f'''
                    <div class="cred-box">
                        <span class="cred-key">VPN Password</span>
                        <span class="cred-val">{user.username if not user.l2tp_password else user.l2tp_password}</span>
                    </div>
                    ''' if user.l2tp_enabled or user.cisco_enabled else ''}
                    <div style="font-size:12px; color:var(--text-muted); text-align:center; margin-top:10px;">
                        Use your account password for OpenVPN / SSH
                    </div>
                </div>

                <div style="text-align:center; margin-top:30px; font-size:12px; color:var(--text-muted);">
                    &copy; {datetime.now().year} {settings.APP_NAME}
                </div>
            </div>
        </div>

        <script>
            // QR Code Logic
            let qrGenerated = false;
            function toggleQR() {{
                const qrDiv = document.getElementById('qrcode');
                const config = document.getElementById('wg-config-raw').value;
                
                if (qrDiv.style.display === 'block') {{
                    qrDiv.style.display = 'none';
                }} else {{
                    qrDiv.style.display = 'block';
                    if (!qrGenerated) {{
                        new QRCode(qrDiv, {{
                            text: config,
                            width: 180,
                            height: 180,
                            colorDark : "#000000",
                            colorLight : "#ffffff",
                            correctLevel : QRCode.CorrectLevel.M
                        }});
                        qrGenerated = true;
                    }}
                }}
            }}

            // Credentials Toggle
            function toggleCreds() {{
                const area = document.getElementById('credentials-area');
                area.style.display = area.style.display === 'none' ? 'block' : 'none';
            }}
            
            // Copy to clipboard helper
            function copyToClipboard(text) {{
                navigator.clipboard.writeText(text).then(() => {{
                    alert("Copied!");
                }});
            }}

            // Tab Switcher
            function switchTab(os) {{
                document.querySelectorAll('.inst-tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.inst-content').forEach(c => c.classList.remove('active'));
                
                event.target.classList.add('active');
                document.getElementById(os).classList.add('active');
            }}
        </script>
    </body>
    </html>
    """
    return html_content

@router.get("/{token}/openvpn")
async def get_openvpn_config(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.subscription_token == token).first()
    if not user or user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="Invalid or expired subscription")
        
    from ..services.openvpn import openvpn_service
    config_content = openvpn_service.generate_client_config(username=user.username)
    
    return Response(
        content=config_content, 
        media_type="application/x-openvpn-profile", 
        headers={"Content-Disposition": f"attachment; filename={user.username}.ovpn"}
    )

@router.get("/{token}/wireguard")
async def get_wireguard_config(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.subscription_token == token).first()
    if not user or user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="Invalid or expired subscription")
    
    try:
        # Ensure keys exist (Auto-fix)
        if not user.wireguard_private_key:
             keys = wireguard_service.generate_keypair()
             user.wireguard_private_key = keys['private_key']
             user.wireguard_public_key = keys['public_key']
             user.wireguard_ip = wireguard_service.allocate_ip()
             db.commit()

        psk = getattr(user, 'wireguard_preshared_key', None)
        content = wireguard_service.generate_client_config(
             client_private_key=user.wireguard_private_key,
             client_ip=user.wireguard_ip,
             preshared_key=psk
        )
        return Response(
            content=content, 
            media_type="text/plain", 
            headers={"Content-Disposition": f"attachment; filename={user.username}-wg.conf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate config: {str(e)}")
