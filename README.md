# 🛡️ VPN Master Panel - Lite Edition

> **Lightweight VPN Management Panel for Low-Resource Servers**  
> Optimized for 512MB - 1GB RAM | No Redis | No Complex Setup

![VPN Master Panel](https://placehold.co/1200x400/2563eb/white?text=VPN+Master+Panel+Lite)

## 🌟 Features

### Core Features
- **Ultra Lightweight**: Runs on weak VPS (1 Core, 512MB RAM)
- **Simple Architecture**: Uses **SQLite** (file-based database) instead of heavy PostgreSQL/MySQL
- **No Redis/Celery**: Background tasks are handled internally by Python
- **Modern UI**: React + TailwindCSS dashboard with professional design
- **Multi-Protocol**: WireGuard, OpenVPN, L2TP, Cisco AnyConnect
- **User Management**: Create/Edit users, set traffic limits, expiry dates

### 🎉 New in v2.0 (Professional Dashboard)
- **📊 Advanced Analytics**: Usage heatmaps, traffic comparison, geographic user maps
- **🔔 Real-time Notifications**: Database-backed notification system with filtering
- **📝 Activity Timeline**: Visual log of all system activities
- **📈 Protocol Distribution**: Real-time charts showing user distribution
- **🗺️ User Location Map**: Interactive world map with user locations
- **📤 Data Export**: Export users, logs, traffic in CSV/JSON formats
- **🔍 Audit Logs**: Comprehensive audit trail with search and filtering
- **💾 Backup & Restore**: One-click system backup and restore
- **⚡ Performance**: Code splitting, lazy loading, optimized bundle size
- **🛡️ Error Handling**: Comprehensive error boundaries and recovery
- **🔄 Auto-Start**: Systemd services with automatic restart on failure

### 🚀 New in v3.0 (Enterprise Features)
- **⚡ WebSocket**: Real-time updates without page refresh
- **🌍 Multi-language**: Support for 5 languages (English, Persian, Arabic, Turkish, Russian) with RTL
- **📧 Email Notifications**: SMTP integration with HTML templates
- **🤖 Telegram Bot**: Bot commands and admin notifications
- **🔒 Automatic SSL**: Let's Encrypt integration with auto-renewal
- **💳 Subscription Management**: Multiple plans with payment tracking

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

## 🛠️ Access Information

Once the installation finishes, open your browser:

- **Panel URL**: `http://YOUR_SERVER_IP:3000`
- **Default Username**: `admin`
- **Default Password**: `admin`

> **⚠️ SECURITY WARNING**: Please change your password immediately after the first login!

---

## 🔄 Updating the Panel

To update your panel to the latest version without losing data:

```bash
cd vpn-master-panel-lite-
git pull
chmod +x update.sh
sudo ./update.sh
```

*(This script automatically backs up your config, updates the code, rebuilds the frontend, and restarts services)*

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

## ❓ Troubleshooting
Having issues? check out the [Troubleshooting Guide](TROUBLESHOOTING.md) for common fixes.

---

## 🤝 Contributing
Feel free to fork this repository and submit Pull Requests. For major changes, please open an issue first.

---
*Built with ❤️ for the community.*
