# 🛡️ VPN Master Panel

**Advanced Multi-Protocol VPN Management Panel with Anti-Censorship Features**

A powerful, open-source VPN management system with built-in Iran bypass capabilities through PersianShield™ tunnel technology.

![GitHub stars](https://img.shields.io/github/stars/EchoDev7/vpn-master-panel?style=social)
![GitHub forks](https://img.shields.io/github/forks/EchoDev7/vpn-master-panel?style=social)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)

---

## ✨ Features

### 🌐 Multi-Protocol VPN Support
- ✅ **OpenVPN** (UDP/TCP)
- ✅ **WireGuard** (Modern, fast protocol)
- ✅ **L2TP/IPsec** (Universal compatibility)
- ✅ **Cisco AnyConnect (Ocserv)**

### 🔐 Advanced Tunneling Solutions
- **Backhaul** - Proven Iran-Foreign tunnel
- **Rathole** - Rust-based, high-performance
- **FRP** - Feature-rich port forwarding
- **Chisel** - HTTP-based tunneling
- **ShadowTLS** - Bypass DPI detection
- **🌟 PersianShield™** - Custom anti-censorship tunnel with:
  - TLS 1.3 Obfuscation
  - Domain Fronting
  - WebSocket over TLS
  - Traffic Randomization
  - Auto-switching on detection
  - SNI Fragmentation

### 👥 User Management
- User roles: Super Admin, Admin, Reseller, User
- Data limits & quotas
- Connection limits
- Expiry dates
- Protocol-specific passwords
- Real-time traffic monitoring
- Subscription pages with QR codes

### 🖥️ System Features
- Multi-node support
- Real-time monitoring & statistics
- RESTful API with JWT authentication
- Modern React dashboard
- PostgreSQL & SQLite support
- Docker deployment
- Grafana & Prometheus integration (optional)

---

## 🚀 Quick Start

## 🚀 نصب سریع

### سرورهای 2GB+ RAM (Standard):
```bash
curl -sSL https://raw.githubusercontent.com/EchoDev7/vpn-master-panel/main/quick-install.sh | sudo bash
```

### سرورهای 1GB RAM (Lightweight):
```bash
curl -sSL https://raw.githubusercontent.com/EchoDev7/vpn-master-panel/main/install-light.sh | sudo bash
```

📊 [مقایسه نسخه‌ها](COMPARISON.md)
---------------------
### Prerequisites
- **Docker** & **Docker Compose** (Recommended)
- OR **Ubuntu 22.04** with Python 3.11+
## 🚀 نصب سریع (توصیه می‌شود)

### یک دستور، نصب کامل:
```bash
curl -sSL https://raw.githubusercontent.com/EchoDev7/vpn-master-panel/main/quick-install.sh | sudo bash
```

**همین!** اسکریپت خودکار همه چیز را نصب و تنظیم می‌کند.

⏱️ زمان نصب: 5-10 دقیقه

📖 [راهنمای کامل نصب خودکار](QUICK_INSTALL.md)
### Option 1: Docker Deployment (Recommended)

```bash
# Clone repository
git clone https://github.com/EchoDev7/vpn-master-panel.git
cd vpn-master-panel

# Copy environment file
cp .env.example .env

# Edit .env and set your passwords
nano .env

# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f backend

# Access panel
# Frontend: http://localhost:3000
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Option 2: Manual Installation

#### 1. Install System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and Node.js
sudo apt install -y python3.11 python3-pip nodejs npm postgresql redis-server

# Install VPN services
sudo apt install -y openvpn wireguard-tools xl2tpd strongswan ocserv
```

#### 2. Setup Backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup database
createdb vpnmaster
createuser vpnmaster

# Run migrations (create tables)
python -c "from app.database import init_db; init_db()"

# Start backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 3. Setup Frontend

```bash
cd frontend

# Install dependencies
npm install

# Build for production
npm run build

# Or run development server
npm run dev
```

---

## 📖 Configuration

### Environment Variables

Create `.env` file:

```bash
# API Settings
API_PORT=8000
DEBUG=false

# Database
DATABASE_URL=postgresql://vpnmaster:password@localhost:5432/vpnmaster

# Security
SECRET_KEY=your-super-secret-key-change-this

# Admin Account
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=admin123

# VPN Ports
OPENVPN_PORT=1194
WIREGUARD_PORT=51820

# Iran Bypass
DOMAIN_FRONTING_ENABLED=true
TLS_OBFUSCATION_ENABLED=true
```

---

## 🔧 Usage Guide

### 1. Login to Panel

- Navigate to `http://your-server:3000`
- Default credentials:
  - Username: `admin`
  - Password: `admin123`
- **⚠️ Change default password immediately!**

### 2. Create VPN User

```bash
# Via API
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user1",
    "password": "secure_password",
    "data_limit_gb": 50,
    "expiry_days": 30,
    "openvpn_enabled": true,
    "wireguard_enabled": true
  }'
```

### 3. Setup Iran-Foreign Tunnel

#### PersianShield™ Tunnel (Recommended for Iran)

```bash
curl -X POST http://localhost:8000/api/v1/tunnels/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "iran-germany-shield",
    "tunnel_type": "persianshield",
    "iran_server_ip": "IRAN_IP",
    "iran_server_port": 443,
    "foreign_server_ip": "FOREIGN_IP",
    "foreign_server_port": 443,
    "domain_fronting_enabled": true,
    "domain_fronting_domain": "cloudflare.com",
    "tls_obfuscation": true
  }'
```

#### Backhaul Tunnel

```bash
curl -X POST http://localhost:8000/api/v1/tunnels/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "iran-germany-backhaul",
    "tunnel_type": "backhaul",
    "protocol": "tcp",
    "iran_server_ip": "IRAN_IP",
    "iran_server_port": 8080,
    "foreign_server_ip": "FOREIGN_IP",
    "foreign_server_port": 1194,
    "forwarded_ports": [1194, 51820]
  }'
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│   React Frontend (Tailwind CSS)    │
│   - Dashboard                       │
│   - User Management                 │
│   - Tunnel Configuration            │
└──────────────┬──────────────────────┘
               │ REST API
        ┌──────▼──────┐
        │   FastAPI   │
        │   Backend   │
        └──────┬──────┘
               │
    ┌──────────┼──────────┐
    │          │          │
┌───▼────┐ ┌──▼─────┐ ┌──▼──────┐
│PostgreSQL│ │ Redis  │ │ Celery  │
└─────────┘ └────────┘ └─────────┘
                │
        ┌───────┴────────┐
        │                │
┌───────▼─────┐  ┌───────▼──────┐
│VPN Services │  │Tunnel Manager│
│- OpenVPN    │  │- Backhaul    │
│- WireGuard  │  │- Rathole     │
│- L2TP       │  │- PersianShield│
│- Cisco      │  └──────────────┘
└─────────────┘
```

---

## 🔐 PersianShield™ Technology

Our custom anti-censorship tunnel uses multiple layers of obfuscation:

1. **TLS 1.3 Encryption** - Latest secure protocol
2. **SNI Fragmentation** - Bypass SNI-based filtering
3. **Domain Fronting** - Hide real destination
4. **WebSocket Framing** - Mimic HTTPS traffic
5. **Traffic Padding** - Randomize packet sizes
6. **Auto-Switching** - Change strategy on detection

---

## 📊 Monitoring

### Enable Grafana Dashboards

```bash
# Start with monitoring stack
docker-compose --profile monitoring up -d

# Access Grafana
# URL: http://localhost:3001
# Username: admin
# Password: (from .env)
```

---

## 🔒 Security Best Practices

1. **Change default passwords** immediately
2. Use **strong SECRET_KEY** (32+ characters)
3. Enable **HTTPS** with Let's Encrypt
4. Implement **2FA** (coming soon)
5. Regular **backups** of database
6. Monitor **failed login attempts**
7. Use **firewall** rules (UFW/iptables)

---

## 🐛 Troubleshooting

### Backend won't start

```bash
# Check logs
docker-compose logs backend

# Verify database connection
docker-compose exec postgres psql -U vpnmaster -d vpnmaster -c "SELECT 1;"
```

### Tunnel not connecting

```bash
# Check tunnel status
curl http://localhost:8000/api/v1/tunnels/1/status \
  -H "Authorization: Bearer YOUR_TOKEN"

# Verify ports are open
sudo netstat -tulpn | grep -E '(1194|51820|8080)'
```

### High CPU usage

```bash
# Check system resources
docker stats

# Optimize database
docker-compose exec postgres vacuumdb -U vpnmaster -d vpnmaster -z
```

---

## 📝 API Documentation

Full API documentation available at: `http://your-server:8000/docs`

### Quick API Examples

#### Get Dashboard Stats
```bash
curl http://localhost:8000/api/v1/monitoring/dashboard \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### List Users
```bash
curl http://localhost:8000/api/v1/users/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

---

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file.

---

## 🙏 Acknowledgments

- Inspired by [OpenVPN Web Panel](https://github.com/eylandoo/openvpn_webpanel_manager)
- Uses [Backhaul](https://github.com/Musixal/Backhaul) for tunneling
- Built with [FastAPI](https://fastapi.tiangolo.com/) and [React](https://react.dev/)

---

## 📞 Support

* **Issues**: [GitHub Issues](https://github.com/EchoDev7/vpn-master-panel/issues)
* **Discussions**: [GitHub Discussions](https://github.com/EchoDev7/vpn-master-panel/discussions)

---

**Made with ❤️ for the free internet**

🌐 Breaking barriers, connecting people
