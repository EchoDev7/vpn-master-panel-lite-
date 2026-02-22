# 🛡️ VPN Master Panel Lite (OpenVPN-only)

Lightweight **OpenVPN-only** management panel for low-resource VPS.

- ✅ Direct server install (no Docker)
- ✅ OpenVPN-only (no WireGuard)
- ✅ FastAPI (backend) + React (frontend)
- ✅ SQLite (simple, file-based DB)

---

## ✅ Supported OS

- **Ubuntu 22.04 LTS** (tested)

---

## 🚀 Installation (recommended)

Run on a **fresh server** as `root` (or with `sudo`).

```bash
git clone https://github.com/EchoDev7/vpn-master-panel-lite.git
cd vpn-master-panel-lite
chmod +x install.sh
sudo ./install.sh
```

### What the installer does

1. Installs packages: OpenVPN, iptables, nginx, fail2ban, Node.js, Python
2. Builds the frontend and configures Nginx
3. Creates/starts systemd service: `vpnmaster-backend`
4. Creates firewall rules (UFW)
5. Creates the installation directory:
   - **/opt/vpn-master-panel** (this is the real installed location)

---

## 🌐 Ports used

- Panel (Frontend): **3000/tcp**
- API (Nginx → Backend): **8000/tcp**
- OpenVPN: **1194/udp**
- SSH: **22/tcp**

---

## � Default login

- URL: `http://YOUR_SERVER_IP:3000`
- Username: `admin`
- Password: `admin`

✅ بعد از اولین ورود، رمز را تغییر دهید.

---

## 🔄 Updating (safe update)

After installation, **do not update from the source folder**.

Use the installed folder:

```bash
cd /opt/vpn-master-panel
sudo ./update.sh
```

Update script behavior:

- If `/opt/vpn-master-panel` is a git repo, it will `git pull` safely
- Rebuilds frontend
- Restarts services (backend/nginx/openvpn)

---

## 🧪 Health check / logs

```bash
sudo systemctl status vpnmaster-backend --no-pager
sudo journalctl -u vpnmaster-backend -n 200 --no-pager
sudo ./check_status.sh
```

---

## 🛠️ Troubleshooting (common problems)

### 1) Panel does not open on port 3000

Run update (it repairs nginx + firewall):

```bash
cd /opt/vpn-master-panel
sudo ./update.sh
```

### 2) Backend shows 500 error

Check logs:

```bash
sudo journalctl -u vpnmaster-backend -n 200 --no-pager
```

Then run:

```bash
cd /opt/vpn-master-panel
sudo ./update.sh
```

### 3) Forgot admin password (reset to `admin`)

```bash
cd /opt/vpn-master-panel/backend
source venv/bin/activate
python3 - <<'PY'
from app.database import SessionLocal
from app.models.user import User
from app.utils.security import get_password_hash

db = SessionLocal()
u = db.query(User).filter(User.username == 'admin').first()
if not u:
    print('admin user not found')
else:
    u.hashed_password = get_password_hash('admin')
    db.commit()
    print("✅ admin password reset to 'admin'")
db.close()
PY

sudo systemctl restart vpnmaster-backend
```

---

## License

MIT (see `LICENSE`).
