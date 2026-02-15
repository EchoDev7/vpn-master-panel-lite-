# 🛡️ VPN Master Panel - Lite Edition

> **Lightweight VPN Management Panel for Low-Resource Servers**  
> Optimized for 512MB - 1GB RAM | No Redis | No Complex Setup

![VPN Master Panel](https://placehold.co/1200x400/2563eb/white?text=VPN+Master+Panel+Lite)

## 🌟 Features
- **Ultra Lightweight**: Runs on weak VPS (1 Core, 512MB RAM).
- **Simple Architecture**: Uses **SQLite** (file-based database) instead of heavy PostgreSQL/MySQL.
- **No Redis/Celery**: Background tasks are handled internally by Python.
- **Modern UI**: React + TailwindCSS dashboard.
- **Multi-Protocol**: WireGuard, OpenVPN, L2TP, Cisco AnyConnect.
- **User Management**: Create/Edit users, set traffic limits, expiry dates.

---

## 🚀 Quick Install (One Command)

Copy and paste this command into your server terminal (Ubuntu 22.04 recommended):

```bash
git clone https://github.com/EchoDev7/vpn-master-panel-lite-.git && \
cd vpn-master-panel-lite- && \
chmod +x install.sh && \
sudo ./install.sh
```

*(This script automatically installs dependencies, sets up the database, builds the frontend, and starts the services)*

---

## 📋 System Requirements
- **OS**: Ubuntu 22.04 LTS (Recommended)
- **RAM**: Minimum 512MB (1GB Recommended)
- **CPU**: 1 Core
- **Disk**: 10GB SSD

---

## 🛠️ After Installation

Once the installation finishes, you will see the access details in the terminal:

1.  **Open your browser** and go to: `http://YOUR_SERVER_IP:3000`
2.  **Login** with the default credentials:
    - **Username**: `admin`
    - **Password**: *(The installer will generate a random password and show it to you at the end)*

> **⚠️ IMPORTANT**: If you missed the password, run this command on your server to reset it:
> ```bash
> cd /opt/vpn-master-panel/backend
> source venv/bin/activate
> python reset_admin.py
> ```

---

## ⚙️ Management Commands

You can manage the panel services using simpler commands:

- **Check Status**:
  ```bash
  systemctl status vpnmaster-backend  # Backend API
  systemctl status nginx              # Web Server
  ```

- **Restart Panel**:
  ```bash
  systemctl restart vpnmaster-backend
  ```

- **View Logs (for debugging)**:
  ```bash
  journalctl -u vpnmaster-backend -f
  ```

---

## 🔒 Security Tips
1.  **Change the admin password** immediately after login.
2.  **Enable Firewall**: The installer sets up UFW, but ensure only necessary ports are open.

---

## 🤝 Contributing
Feel free to fork this repository and submit Pull Requests. For major changes, please open an issue first.

---
*Built with ❤️ for the community.*
