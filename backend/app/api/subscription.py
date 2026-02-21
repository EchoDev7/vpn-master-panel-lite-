from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.setting import Setting
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
<html lang="en" dir="ltr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Subscription Portal</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            --bg: #0b1020;
            --bg-soft: #111833;
            --card: #131d3d;
            --card-alt: #172447;
            --text: #e6ebff;
            --muted: #97a3cc;
            --border: #2b3b71;
            --primary: #4f9cff;
            --primary-2: #2662ff;
            --success: #18c08f;
            --warning: #f5a524;
            --danger: #ff5d7b;
            --ovpn: #f97316;
            --wg: #38bdf8;
        }

        * { box-sizing: border-box; }
        body {
            margin: 0;
            font-family: "Inter", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background:
                radial-gradient(1200px 500px at 20% -10%, #1f3f92 0%, transparent 60%),
                radial-gradient(900px 400px at 90% -20%, #4a1f8f 0%, transparent 58%),
                var(--bg);
            color: var(--text);
            line-height: 1.55;
            padding: 14px;
        }

        .shell { max-width: 940px; margin: 0 auto; }

        .panel {
            background: linear-gradient(160deg, rgba(19,29,61,0.95), rgba(17,24,51,0.95));
            border: 1px solid var(--border);
            border-radius: 24px;
            box-shadow: 0 22px 50px rgba(5, 9, 24, 0.55);
            overflow: hidden;
        }

        .hero {
            padding: 24px;
            border-bottom: 1px solid var(--border);
            background: linear-gradient(140deg, rgba(79,156,255,0.2), rgba(38,98,255,0.08));
        }

        .title { margin: 0; font-size: 1.5rem; letter-spacing: 0.2px; }
        .subtitle { margin: 8px 0 0; color: var(--muted); font-size: 0.95rem; }

        .hero-meta { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }
        .chip {
            display: inline-flex; align-items: center; gap: 8px;
            background: rgba(18, 27, 56, 0.8);
            border: 1px solid var(--border);
            border-radius: 999px;
            color: #d5ddff;
            padding: 6px 12px;
            font-size: 0.84rem;
            font-weight: 600;
        }
        .status-active { color: #9af3d4; border-color: rgba(24,192,143,.45); }
        .status-expired { color: #ffc4d0; border-color: rgba(255,93,123,.45); }

        .content { padding: 22px; display: grid; gap: 16px; }

        .stats {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
        }
        .stat {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 14px;
        }
        .stat .label { color: var(--muted); font-size: 0.77rem; text-transform: uppercase; letter-spacing: .06em; }
        .stat .value { margin-top: 6px; font-size: 1.1rem; font-weight: 700; }

        .progress-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 14px;
        }
        .progress-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; color: var(--muted); font-size: .9rem; }
        .progress {
            width: 100%; height: 12px;
            border-radius: 999px;
            background: #0f1730;
            border: 1px solid #24376a;
            overflow: hidden;
        }
        .fill { height: 100%; width: 0%; background: linear-gradient(90deg, #2ec5ff, #18c08f); transition: width .4s ease; }

        .notice {
            border-radius: 12px;
            border: 1px solid;
            padding: 12px;
            font-size: .9rem;
        }
        .notice.warn { border-color: rgba(245,165,36,.5); background: rgba(245,165,36,.12); }
        .notice.danger { border-color: rgba(255,93,123,.55); background: rgba(255,93,123,.14); }

        .grid-2 { display: grid; grid-template-columns: 1.2fr 1fr; gap: 12px; }

        .section {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 14px;
        }
        .section h3 {
            margin: 0 0 10px;
            font-size: 1rem;
            display: flex; align-items: center; gap: 8px;
        }
        .section p { margin: 0; color: var(--muted); font-size: .9rem; }

        .btn-row { display: grid; gap: 10px; }
        .btn {
            appearance: none;
            border: 0;
            width: 100%;
            border-radius: 11px;
            padding: 11px 12px;
            color: white;
            cursor: pointer;
            font-weight: 700;
            font-size: .92rem;
            text-decoration: none;
            display: inline-flex; align-items: center; justify-content: center; gap: 8px;
            transition: transform .08s ease, opacity .18s ease;
        }
        .btn:active { transform: translateY(1px); }
        .btn.ovpn { background: linear-gradient(120deg, #f97316, #ea580c); }
        .btn.wg { background: linear-gradient(120deg, #38bdf8, #2563eb); }
        .btn.ghost {
            background: transparent;
            border: 1px solid var(--border);
            color: #d3deff;
            font-weight: 600;
        }
        .btn.disabled { opacity: .45; pointer-events: none; }

        .link-list { margin-top: 10px; display: grid; gap: 8px; }
        .link-item {
            display: flex; justify-content: space-between; align-items: center; gap: 8px;
            background: var(--card-alt);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 8px 10px;
            font-size: .82rem;
        }
        .link-item code { color: #9bd4ff; word-break: break-all; }

        .os-tabs { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
        .os-tab {
            border: 1px solid var(--border);
            background: #111b39;
            color: #bfd0ff;
            border-radius: 999px;
            padding: 6px 12px;
            font-size: .82rem;
            cursor: pointer;
        }
        .os-tab.active { background: #255cf5; border-color: #4f9cff; color: white; }

        .app-grid { display: grid; gap: 8px; }
        .app-item {
            background: var(--card-alt);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 10px;
            display: flex; justify-content: space-between; align-items: center; gap: 8px;
        }
        .app-item .meta { font-size: .84rem; color: var(--muted); }

        .guide {
            margin-top: 10px;
            background: #101a36;
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 12px;
            font-size: .9rem;
        }
        .guide ol { margin: 6px 0 0 18px; padding: 0; }
        .guide li { margin-bottom: 5px; color: #cfdbff; }

        .qr-wrap { margin-top: 12px; text-align: center; display: none; }
        #qrcode {
            display: inline-block;
            padding: 10px;
            border-radius: 12px;
            background: white;
            border: 1px solid #d8e4ff;
        }

        .footer-note {
            margin-top: 4px;
            color: var(--muted);
            font-size: .8rem;
            text-align: center;
        }

        @media (max-width: 900px) {
            .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .grid-2 { grid-template-columns: 1fr; }
        }
        @media (max-width: 560px) {
            .hero { padding: 18px; }
            .content { padding: 14px; }
            .stats { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="shell">
        <div class="panel">
            <div class="hero">
                <h1 class="title"><i class="fa-solid fa-shield-halved"></i> Secure Subscription Portal</h1>
                <p class="subtitle">Download your VPN profiles, install client apps, and follow guided setup for your device.</p>
                <div class="hero-meta">
                    <span class="chip" id="chip-user"><i class="fa-regular fa-user"></i> User</span>
                    <span class="chip" id="chip-expiry"><i class="fa-regular fa-calendar"></i> --</span>
                    <span class="chip" id="chip-status"><i class="fa-solid fa-wave-square"></i> Loading...</span>
                    <span class="chip" id="chip-os"><i class="fa-solid fa-laptop-code"></i> Detecting device...</span>
                </div>
            </div>

            <div class="content">
                <div class="stats">
                    <div class="stat"><div class="label">Days Remaining</div><div id="days" class="value">--</div></div>
                    <div class="stat"><div class="label">Data Used</div><div id="usage" class="value">-- GB</div></div>
                    <div class="stat"><div class="label">Data Limit</div><div id="limit" class="value">--</div></div>
                    <div class="stat"><div class="label">Usage</div><div id="percent" class="value">0%</div></div>
                </div>

                <div class="progress-card">
                    <div class="progress-row">
                        <span>Traffic Usage</span>
                        <strong id="usage-inline">0%</strong>
                    </div>
                    <div class="progress"><div id="progress" class="fill"></div></div>
                </div>

                <div id="notice-expired" class="notice danger" style="display:none;">
                    <i class="fa-solid fa-triangle-exclamation"></i>
                    Your subscription is expired. Downloads may still be available, but access can be blocked by server policy.
                </div>
                <div id="notice-traffic" class="notice warn" style="display:none;">
                    <i class="fa-solid fa-circle-exclamation"></i>
                    You are near your data limit. Expect throttling or suspension based on provider policy.
                </div>

                <div class="grid-2">
                    <section class="section">
                        <h3><i class="fa-solid fa-download"></i> Config Downloads</h3>
                        <p>Use separate direct links for each protocol. Download and import manually for best reliability.</p>

                        <div class="btn-row" style="margin-top:10px;">
                            <a id="btn-ovpn-ios" class="btn ovpn" href="#" download>
                                <i class="fa-solid fa-file-arrow-down"></i> Download iOS OpenVPN (.ovpn)
                            </a>
                            <a id="btn-ovpn-android" class="btn ovpn" href="#" download>
                                <i class="fa-solid fa-file-arrow-down"></i> Download Android OpenVPN (.ovpn)
                            </a>
                            <a id="btn-wg" class="btn wg" href="#" download>
                                <i class="fa-solid fa-file-arrow-down"></i> Download WireGuard (.conf)
                            </a>
                            <button id="btn-wg-qr" class="btn ghost" type="button">
                                <i class="fa-solid fa-qrcode"></i> Show WireGuard QR
                            </button>
                        </div>

                        <div class="link-list">
                            <div class="link-item">
                                <code id="ovpn-link-ios">/sub/token/openvpn?platform=ios</code>
                                <button class="btn ghost" style="padding:6px 10px; width:auto;" type="button" onclick="copyText('ovpn-link-ios')">Copy iOS link</button>
                            </div>
                            <div class="link-item">
                                <code id="ovpn-link-android">/sub/token/openvpn?platform=android</code>
                                <button class="btn ghost" style="padding:6px 10px; width:auto;" type="button" onclick="copyText('ovpn-link-android')">Copy Android link</button>
                            </div>
                            <div class="link-item">
                                <code id="wg-link">/sub/token/wireguard</code>
                                <button class="btn ghost" style="padding:6px 10px; width:auto;" type="button" onclick="copyText('wg-link')">Copy</button>
                            </div>
                        </div>

                        <div class="qr-wrap" id="qr-wrap">
                            <div id="qrcode"></div>
                            <div class="footer-note">Scan this QR in the WireGuard app</div>
                        </div>
                    </section>

                    <section class="section">
                        <h3><i class="fa-solid fa-mobile-screen-button"></i> Client Apps</h3>
                        <p>Recommended apps for your detected OS. You can switch platform tabs manually.</p>

                        <div class="os-tabs" id="os-tabs"></div>
                        <div class="app-grid" id="app-grid"></div>
                    </section>
                </div>

                <section class="section">
                    <h3><i class="fa-solid fa-book-open"></i> Setup Guide</h3>
                    <p>Follow steps for your platform. Import one file per protocol in the chosen app.</p>
                    <div class="guide" id="guide-box"></div>
                </section>

                <section class="section">
                    <h3><i class="fa-solid fa-circle-info"></i> Important Notes</h3>
                    <ul style="margin:8px 0 0 18px; color:var(--muted);">
                        <li>Never share this subscription URL with others.</li>
                        <li>Keep your client apps up to date for better compatibility and security.</li>
                        <li>If connection fails, re-download config first, then reconnect.</li>
                        <li>WireGuard QR is available only when a server-side config is generated.</li>
                    </ul>
                </section>
            </div>
        </div>
    </div>

    <script>
        const DATA = {{DATA_JSON}};
        const APPS_BY_OS = {
            android: [
                { name: 'WireGuard (Recommended)', protocol: 'WireGuard', url: 'https://play.google.com/store/apps/details?id=com.wireguard.android' },
                { name: 'OpenVPN Connect', protocol: 'OpenVPN', url: 'https://play.google.com/store/apps/details?id=net.openvpn.openvpn' }
            ],
            ios: [
                { name: 'WireGuard', protocol: 'WireGuard', url: 'https://apps.apple.com/app/wireguard/id1441195209' },
                { name: 'OpenVPN Connect', protocol: 'OpenVPN', url: 'https://apps.apple.com/app/openvpn-connect/id590379981' }
            ],
            windows: [
                { name: 'WireGuard for Windows', protocol: 'WireGuard', url: 'https://www.wireguard.com/install/' },
                { name: 'OpenVPN Connect', protocol: 'OpenVPN', url: 'https://openvpn.net/client-connect-vpn-for-windows/' }
            ],
            macos: [
                { name: 'WireGuard for macOS', protocol: 'WireGuard', url: 'https://apps.apple.com/app/wireguard/id1451685025' },
                { name: 'OpenVPN Connect', protocol: 'OpenVPN', url: 'https://openvpn.net/client-connect-vpn-for-mac-os/' }
            ],
            linux: [
                { name: 'WireGuard Tools', protocol: 'WireGuard', url: 'https://www.wireguard.com/install/' },
                { name: 'OpenVPN Community', protocol: 'OpenVPN', url: 'https://openvpn.net/community-downloads/' }
            ]
        };

        const GUIDES = {
            android: [
                'Install WireGuard or OpenVPN Connect from Google Play.',
                'Tap the matching config download button above.',
                'Open the app and import the downloaded file.',
                'Connect and approve VPN permission when prompted.'
            ],
            ios: [
                'Install WireGuard or OpenVPN Connect from App Store.',
                'Download your config file from this page.',
                'Use Share/Open In to import into the selected app.',
                'Tap connect and allow VPN profile installation.'
            ],
            windows: [
                'Install OpenVPN Connect or WireGuard for Windows.',
                'Download your .ovpn or .conf file from this page.',
                'Open app > Import profile/tunnel from file.',
                'Activate the profile and test connection.'
            ],
            macos: [
                'Install OpenVPN Connect or WireGuard.',
                'Download config file from this portal.',
                'Import the file into the app.',
                'Enable VPN connection and verify internet access.'
            ],
            linux: [
                'Install client tools from official sources.',
                'Download config file from this portal.',
                'Import using GUI app or CLI based on distro.',
                'Bring tunnel up and verify routing/DNS.'
            ]
        };

        function detectOS() {
            const ua = navigator.userAgent || '';
            if (/android/i.test(ua)) return 'android';
            if (/iPhone|iPad|iPod/i.test(ua)) return 'ios';
            if (/Windows/i.test(ua)) return 'windows';
            if (/Macintosh|Mac OS X/i.test(ua)) return 'macos';
            if (/Linux/i.test(ua)) return 'linux';
            return 'windows';
        }

        let selectedOS = detectOS();

        function osLabel(key) {
            return { android: 'Android', ios: 'iOS', windows: 'Windows', macos: 'macOS', linux: 'Linux' }[key] || key;
        }

        function copyText(id) {
            const el = document.getElementById(id);
            if (!el) return;
            navigator.clipboard.writeText(el.textContent || '').then(() => {
                alert('Copied');
            }).catch(() => {
                alert('Copy failed');
            });
        }

        function renderOsTabs() {
            const tabs = document.getElementById('os-tabs');
            tabs.innerHTML = '';
            Object.keys(APPS_BY_OS).forEach((key) => {
                const btn = document.createElement('button');
                btn.className = `os-tab ${key === selectedOS ? 'active' : ''}`;
                btn.type = 'button';
                btn.textContent = osLabel(key);
                btn.onclick = () => {
                    selectedOS = key;
                    renderOsTabs();
                    renderApps();
                    renderGuide();
                };
                tabs.appendChild(btn);
            });
        }

        function renderApps() {
            const grid = document.getElementById('app-grid');
            const apps = APPS_BY_OS[selectedOS] || [];
            grid.innerHTML = '';
            apps.forEach((app) => {
                const item = document.createElement('div');
                item.className = 'app-item';
                item.innerHTML = `
                    <div>
                        <div><strong>${app.name}</strong></div>
                        <div class="meta">${app.protocol} client</div>
                    </div>
                    <a class="btn ghost" style="width:auto; padding:7px 10px;" target="_blank" rel="noopener noreferrer" href="${app.url}">
                        <i class="fa-solid fa-arrow-up-right-from-square"></i> Get App
                    </a>
                `;
                grid.appendChild(item);
            });
        }

        function renderGuide() {
            const box = document.getElementById('guide-box');
            const steps = GUIDES[selectedOS] || [];
            box.innerHTML = `<strong>${osLabel(selectedOS)} setup</strong><ol>${steps.map((s) => `<li>${s}</li>`).join('')}</ol>`;
        }

        function setupQrButton() {
            const qrWrap = document.getElementById('qr-wrap');
            const qrBtn = document.getElementById('btn-wg-qr');
            qrBtn.onclick = () => {
                if (!DATA.wg_config) {
                    alert('WireGuard config is not available for this account.');
                    return;
                }
                qrWrap.style.display = qrWrap.style.display === 'none' || !qrWrap.style.display ? 'block' : 'none';
                const qrNode = document.getElementById('qrcode');
                if (!qrNode.querySelector('canvas') && !qrNode.querySelector('img')) {
                    new QRCode(qrNode, { text: DATA.wg_config, width: 190, height: 190 });
                }
            };
        }

        function hydrate() {
            const ovpnUrl = window.location.origin + DATA.ovpn_url;
            const ovpnUrlIos = `${ovpnUrl}?platform=ios`;
            const ovpnUrlAndroid = `${ovpnUrl}?platform=android`;
            const wgUrl = window.location.origin + DATA.wg_url;
            const isActive = DATA.status === 'active';
            const usagePercent = Math.round(DATA.data_percent || 0);

            document.getElementById('chip-user').innerHTML = `<i class="fa-regular fa-user"></i> ${DATA.username}`;
            document.getElementById('chip-expiry').innerHTML = `<i class="fa-regular fa-calendar"></i> Expires: ${DATA.expiry_date}`;
            document.getElementById('chip-status').innerHTML = `<i class="fa-solid fa-wave-square"></i> ${isActive ? 'Active' : 'Expired'}`;
            document.getElementById('chip-status').classList.add(isActive ? 'status-active' : 'status-expired');
            document.getElementById('chip-os').innerHTML = `<i class="fa-solid fa-laptop-code"></i> Detected: ${osLabel(selectedOS)}`;

            document.getElementById('days').textContent = DATA.days_remaining;
            document.getElementById('usage').textContent = `${DATA.data_used_gb} GB`;
            document.getElementById('limit').textContent = DATA.data_limit_gb === 'Unlimited' ? 'Unlimited' : `${DATA.data_limit_gb} GB`;
            document.getElementById('percent').textContent = `${usagePercent}%`;
            document.getElementById('usage-inline').textContent = `${usagePercent}%`;

            const fill = document.getElementById('progress');
            fill.style.width = `${usagePercent}%`;
            if (usagePercent >= 90) fill.style.background = 'linear-gradient(90deg,#ff5d7b,#e11d48)';
            else if (usagePercent >= 70) fill.style.background = 'linear-gradient(90deg,#f5a524,#fb923c)';

            if (!isActive) document.getElementById('notice-expired').style.display = 'block';
            if (usagePercent >= 80) document.getElementById('notice-traffic').style.display = 'block';

            const ovpnBtnIos = document.getElementById('btn-ovpn-ios');
            const ovpnBtnAndroid = document.getElementById('btn-ovpn-android');
            const wgBtn = document.getElementById('btn-wg');

            ovpnBtnIos.href = ovpnUrlIos;
            ovpnBtnAndroid.href = ovpnUrlAndroid;
            wgBtn.href = wgUrl;

            if (!DATA.openvpn_enabled) {
                ovpnBtnIos.classList.add('disabled');
                ovpnBtnIos.removeAttribute('href');
                ovpnBtnIos.textContent = 'OpenVPN not enabled';
                ovpnBtnAndroid.classList.add('disabled');
                ovpnBtnAndroid.removeAttribute('href');
                ovpnBtnAndroid.textContent = 'OpenVPN not enabled';
            }
            if (!DATA.wireguard_enabled) {
                wgBtn.classList.add('disabled');
                wgBtn.removeAttribute('href');
                wgBtn.textContent = 'WireGuard not enabled for your account';
                document.getElementById('btn-wg-qr').classList.add('disabled');
            }

            document.getElementById('ovpn-link-ios').textContent = ovpnUrlIos;
            document.getElementById('ovpn-link-android').textContent = ovpnUrlAndroid;
            document.getElementById('wg-link').textContent = wgUrl;

            renderOsTabs();
            renderApps();
            renderGuide();
            setupQrButton();
        }

        hydrate();
    </script>
</body>
</html>
"""


def _get_user_by_token(db: Session, token: str) -> User:
    user = db.query(User).filter(User.subscription_token == token).first()
    if not user:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return user


def _ensure_subscription_enabled(db: Session) -> None:
    setting = db.query(Setting).filter(Setting.key == "subscription_enabled").first()
    if setting and str(setting.value).strip() == "0":
        raise HTTPException(status_code=403, detail="Subscription links are disabled")


def _is_user_subscription_active(user: User) -> bool:
    if getattr(user, "status", None) and user.status.value != "active":
        return False
    if user.expiry_date:
        expiry = user.expiry_date
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expiry:
            return False
    return True


def _ensure_wireguard_material(user: User, db: Session) -> bool:
    if not user.wireguard_enabled:
        return False

    updated = False
    if not user.wireguard_private_key or not user.wireguard_public_key:
        keys = wireguard_service.generate_keypair()
        user.wireguard_private_key = keys["private_key"]
        user.wireguard_public_key = keys["public_key"]
        updated = True

    if not user.wireguard_ip:
        user.wireguard_ip = wireguard_service.allocate_ip()
        updated = True

    if not user.wireguard_preshared_key:
        try:
            user.wireguard_preshared_key = wireguard_service.generate_preshared_key()
            updated = True
        except Exception:
            # Preshared key is optional for client config generation.
            pass

    if updated:
        db.commit()
        db.refresh(user)

    return True

@router.get("/{token}", response_class=HTMLResponse)
async def get_subscription_page(token: str, db: Session = Depends(get_db)):
    _ensure_subscription_enabled(db)
    user = _get_user_by_token(db, token)

    import json
    
    now = datetime.now(timezone.utc)
    remaining = 999
    if user.expiry_date:
        expiry = user.expiry_date
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        remaining = max(0, (expiry - now).days)
        
    limit_gb = user.data_limit_gb if user.data_limit_gb > 0 else "Unlimited"
    percent = 0
    if user.data_limit_gb > 0:
        percent = min(100, (user.data_usage_gb / user.data_limit_gb * 100))
        
    context = {
        "username": user.username,
        "status": "active" if _is_user_subscription_active(user) else "expired",
        "openvpn_enabled": bool(user.openvpn_enabled),
        "wireguard_enabled": bool(user.wireguard_enabled),
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
    
    # Pre-generate WG config for QR code when available.
    if _ensure_wireguard_material(user, db):
         try:
             context["wg_config"] = wireguard_service.generate_client_config(
                 user.wireguard_private_key, 
                 user.wireguard_ip, 
                 user.wireguard_preshared_key
             )
         except Exception:
             pass

    # Inject JSON into template (simple hydration).
    # json.dumps() is used with ensure_ascii=False for Persian text support.
    # We escape </script> sequences to prevent XSS via script tag injection.
    safe_json = json.dumps(context, ensure_ascii=False).replace(
        "</", "<\\/"
    )
    html = HTML_TEMPLATE.replace("{{DATA_JSON}}", safe_json)
    return html

@router.get("/{token}/openvpn", response_class=PlainTextResponse)
async def get_openvpn_config(
    token: str,
    platform: str = Query("generic", description="OpenVPN profile platform: generic|ios|android"),
    db: Session = Depends(get_db),
):
    _ensure_subscription_enabled(db)
    user = _get_user_by_token(db, token)
        
    if not user.openvpn_enabled:
        raise HTTPException(status_code=400, detail="OpenVPN disabled for this user")
        
    config = openvpn_service.generate_client_config(user.username, platform=platform, db=db)
    platform_suffix = ""
    if platform in ("ios", "android"):
        platform_suffix = f"-{platform}"
    return PlainTextResponse(
        content=config,
        media_type="application/x-openvpn-profile",
        headers={"Content-Disposition": f"attachment; filename={user.username}{platform_suffix}.ovpn"},
    )

@router.get("/{token}/wireguard", response_class=PlainTextResponse)
async def get_wireguard_config(token: str, db: Session = Depends(get_db)):
    _ensure_subscription_enabled(db)
    user = _get_user_by_token(db, token)
        
    if not user.wireguard_enabled:
        raise HTTPException(status_code=400, detail="WireGuard disabled for this user")

    _ensure_wireguard_material(user, db)
        
    config = wireguard_service.generate_client_config(
        user.wireguard_private_key,
        user.wireguard_ip,
        user.wireguard_preshared_key
    )
    return PlainTextResponse(
        content=config,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename={user.username}.conf"},
    )
