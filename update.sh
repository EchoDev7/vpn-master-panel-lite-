#!/bin/bash

# VPN Master Panel - Auto Update Script
# Usage: sudo ./update.sh

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check Root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}"
   exit 1
fi

INSTALL_DIR="/opt/vpn-master-panel"

echo -e "${CYAN}🚀 Starting VPN Master Panel Update...${NC}"

# 0. Verify Installation Directory
if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "${RED}Error: Installation not found at $INSTALL_DIR${NC}"
    echo -e "${RED}Please run install.sh first.${NC}"
    exit 1
fi

# 1. Update Source Code (Non-destructive)
echo -e "${CYAN}📥 Updating Installation at $INSTALL_DIR...${NC}"
cd "$INSTALL_DIR" || exit 1

# Check if it's a git repo
if [ -d ".git" ]; then
    echo -e "${CYAN}Fetching updates...${NC}"
    git fetch --all
    # Stash local changes instead of hard reset
    if ! git diff-index --quiet HEAD --; then
        echo -e "${YELLOW}⚠️ Local changes detected. Stashing them...${NC}"
        git stash
    fi
    git pull origin main
else
    echo -e "${YELLOW}⚠️ Not a git repository. Skipping git update.${NC}"
    echo -e "${YELLOW}To update manually, backup your config and reinstall.${NC}"
fi

# 2. Update System Packages
echo -e "${CYAN}📦 Updating System Packages...${NC}"
export DEBIAN_FRONTEND=noninteractive
apt update -qq
# Ensure critical packages are present
apt install -y openvpn wireguard wireguard-tools iptables iptables-persistent nodejs python3-pip

# 3. Enable IP Forwarding (Ensure it persists)
if ! grep -q "net.ipv4.ip_forward=1" /etc/sysctl.conf; then
    echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
    sysctl -p
fi

# 4. Update Backend Dependencies
echo -e "${CYAN}🐍 Updating Backend...${NC}"
cd backend
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️ Virtual environment missing. Creating one...${NC}"
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt
python -m py_compile app/main.py # Syntax check

# 4.5 Run Database Migrations (Safe Python Script)
echo -e "${CYAN}🗄️  Running Database Migrations...${NC}"
if [ -f "migrate_db.py" ]; then
    python3 migrate_db.py
else
    echo -e "${YELLOW}⚠️ Migration script not found. Skipping.${NC}"
fi

cd ..

# 5. Rebuild Frontend (Critical for UI updates)
echo -e "${CYAN}⚛️  Rebuilding Frontend...${NC}"
cd frontend
# Install ALL dependencies (including devDependencies like vite)
npm install
npm run build

# Verify Build Success
if [ ! -f "dist/index.html" ]; then
    echo -e "${RED}❌ Frontend Build Failed! 'dist/index.html' not found.${NC}"
    echo -e "${YELLOW}Check npm logs above.${NC}"
    exit 1
fi

# Fix Permissions (Critical for Nginx)
chmod -R 755 dist
cd ..

# 6. Repair & Restart Services
echo -e "${CYAN}🔧 Verifying Services...${NC}"

# Backend Service Repair
SERVICE_FILE="/etc/systemd/system/vpnmaster-backend.service"
if [ ! -f "$SERVICE_FILE" ]; then
    echo -e "${YELLOW}⚠️ Service file missing. Recreating...${NC}"
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=VPN Master Panel Backend (Lightweight)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/vpn-master-panel/backend
Environment="PATH=/opt/vpn-master-panel/backend/venv/bin"
ExecStart=/opt/vpn-master-panel/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001 --workers 1 --limit-concurrency 50
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable vpnmaster-backend
fi

# Nginx Repair Function
repair_nginx() {
    echo -e "${YELLOW}⚠️ Detected Nginx issue. Reconfiguring...${NC}"
    
    # Create safe config
    cat > /etc/nginx/sites-available/vpnmaster << EOF
# Backend API
server {
    listen 8000;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }
}

# Frontend
server {
    listen 3000;
    server_name _;

    root /opt/vpn-master-panel/frontend/dist;
    index index.html;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript;

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location /api {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
    }
}
EOF
    rm -f /etc/nginx/sites-enabled/default
    ln -sf /etc/nginx/sites-available/vpnmaster /etc/nginx/sites-enabled/
    nginx -t && systemctl restart nginx
    echo -e "${GREEN}✓ Nginx repaired${NC}"
}

# Check Firewall (SECURED: Only necessary ports)
echo -e "${CYAN}🔥 Configuring Firewall...${NC}"
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp > /dev/null 2>&1
ufw allow 80/tcp > /dev/null 2>&1
ufw allow 443/tcp > /dev/null 2>&1
ufw allow 3000/tcp > /dev/null 2>&1
ufw allow 8000/tcp > /dev/null 2>&1
# VPN Ports (customizable via panel later, but defaults here)
ufw allow 1194/udp > /dev/null 2>&1
ufw allow 51820/udp > /dev/null 2>&1

ufw --force enable > /dev/null 2>&1

# Ensure TUN Device Exists (Common VPS Issue)
if [ ! -c /dev/net/tun ]; then
    echo -e "${YELLOW}⚠️ Creating /dev/net/tun...${NC}"
    mkdir -p /dev/net
    mknod /dev/net/tun c 10 200
    chmod 600 /dev/net/tun
fi

# Fix AppArmor (Allow OpenVPN to read keys in /opt)
if [ -f "/etc/apparmor.d/usr.sbin.openvpn" ]; then
    echo -e "${CYAN}🛡️  Updating AppArmor Profile...${NC}"
    if ! grep -q "/opt/vpn-master-panel/" /etc/apparmor.d/usr.sbin.openvpn; then
        # Append rule to allow read access
        sed -i '/}/d' /etc/apparmor.d/usr.sbin.openvpn
        echo "  /opt/vpn-master-panel/backend/data/** r," >> /etc/apparmor.d/usr.sbin.openvpn
        echo "}" >> /etc/apparmor.d/usr.sbin.openvpn
        systemctl reload apparmor
        echo -e "${GREEN}✓ AppArmor Updated${NC}"
    fi
fi

# Ensure Port 443 is FREE for OpenVPN (If configured)
# Only do this if 443 is actually intended for VPN, otherwise warn.
# For now, we assume user wants 443 for VPN/SSL.

# Ensure OpenVPN Log Directory Exists
if [ ! -d "/var/log/openvpn" ]; then
    mkdir -p /var/log/openvpn
    touch /var/log/openvpn/openvpn.log
    touch /var/log/openvpn/openvpn-status.log
    chmod 755 /var/log/openvpn
fi

echo -e "${CYAN}🔄 Restarting Services...${NC}"
systemctl daemon-reload

# Fix permissions so OpenVPN can read keys
if [ -d "/opt/vpn-master-panel/backend/data" ]; then
    chmod -R 755 /opt/vpn-master-panel/backend/data
fi

systemctl restart vpnmaster-backend
# Restart OpenVPN to apply changes
if systemctl list-units --full -all | grep -q "openvpn@server.service"; then
    systemctl restart openvpn@server
else
    systemctl restart openvpn
fi

# Check Nginx Config
if ! nginx -t > /dev/null 2>&1; then
    repair_nginx
else
    systemctl restart nginx
fi

echo -e "${GREEN}✅ Update Successfully Completed!${NC}"
if [ -d ".git" ]; then
    echo -e "${GREEN}   Version: $(git rev-parse --short HEAD)${NC}"
fi
