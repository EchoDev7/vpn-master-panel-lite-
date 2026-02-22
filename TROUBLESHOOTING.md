# 🛠️ VPN Master Panel - Troubleshooting Guide

This document lists common issues encountered during installation or usage and how to fix them.

---

## 1. 🌐 "This site can’t be reached" / Connection Refused
**Symptoms:**
- Browser shows `ERR_CONNECTION_REFUSED` when opening `http://YOUR_IP:3000`.
- The panel does not load.

**Causes:**
- Nginx service is not running.
- Firewall (UFW) is blocking port 3000.
- Nginx configuration is invalid.

**✅ Solution:**
Run the self-repairing update script. It automatically fixes Nginx config and firewall rules:
```bash
sudo ./update.sh
```

---

## 2. 🔑 "Login Failed" or Forgot Admin Password
**Symptoms:**
- You cannot log in with `admin`.
- You missed the random password generated during installation.

**✅ Solution:**
Reset the password to `admin` / `admin` by running this command on your server:

```bash
# Option 1: Run the update script (easiest)
sudo ./update.sh

# Option 2: Run the manual reset script
cd /opt/vpn-master-panel/backend
source venv/bin/activate
python reset_admin.py
```

---

## 3. 💥 "500 Internal Server Error" (Backend Crash)
**Symptoms:**
- The panel loads but login shows "Internal Server Error".
- API requests fail.

**Causes:**
- Database tables missing (did not run `init_db`).
- Python version incompatibility (Using Python 3.9 syntax on older systems).

**✅ Solution:**
Check the backend logs to see the exact error:
```bash
sudo journalctl -u vpnmaster-backend -f
```

If you see `no such table: users`, run the update script to re-initialize the database:
```bash
sudo ./update.sh
```

---

## 4. ❌ "Command not found" or "No such file"
**Symptoms:**
- Running `python reset_admin.py` gives `command not found: python`.
- Running `source venv/bin/activate` gives `No such file`.

**Cause:**
- You are running commands in the **source folder** (`~/vpn-master-panel-lite`) instead of the **installation folder** (`/opt/vpn-master-panel`).
- Multiple Python versions installed (use `python3` instead of `python`).

**✅ Solution:**
Always go to the installation directory first:
```bash
cd /opt/vpn-master-panel/backend
source venv/bin/activate
python3 reset_admin.py
```

---

## 5. 🔄 "System starts but Panel keeps restarting"
**Symptoms:**
- `systemctl status vpnmaster-backend` shows "Restarting..." repeatedly.

**Cause:**
- Startup order issue (e.g., trying to create admin before DB is ready).
- Port conflict (Port 8000 is already in use).

**✅ Solution:**
1. Check if another service is using port 8000:
   ```bash
   netstat -tuln | grep 8000
   ```
2. Run the update script to apply the latest startup logic fixes:
   ```bash
   sudo ./update.sh
   ```

---

## 🆘 Still having issues?
Collect basic diagnostics and check the logs:

```bash
sudo systemctl status vpnmaster-backend --no-pager
sudo journalctl -u vpnmaster-backend -n 200 --no-pager
sudo ./check_status.sh
```
