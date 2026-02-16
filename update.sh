#!/bin/bash

# VPN Master Panel - Auto Update Script
# Usage: sudo ./update.sh

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
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

# 1. Update Source Code (Targeting the /opt directory)
echo -e "${CYAN}📥 Updating Installation at $INSTALL_DIR...${NC}"
cd "$INSTALL_DIR" || exit 1

# Check if it's a git repo
if [ -d ".git" ]; then
    git fetch --all
    git reset --hard origin/main
    git pull origin main
else
    echo -e "${YELLOW}⚠️ Not a git repository. Forcing re-sync...${NC}"
    # Backup config
    cp backend/.env /tmp/vpn_env_backup
    
    # Re-initialize
    cd ..
    rm -rf vpn-master-panel
    git clone --depth 1 https://github.com/EchoDev7/vpn-master-panel-lite-.git vpn-master-panel
    mv vpn-master-panel-lite- vpn-master-panel 2>/dev/null || true
    cd vpn-master-panel
    
    # Restore config
    if [ -f "/tmp/vpn_env_backup" ]; then
        mv /tmp/vpn_env_backup backend/.env
    fi
fi

# 2. Update System Packages (Removed conflicting packages)
echo -e "${CYAN}📦 Updating System Packages...${NC}"
export DEBIAN_FRONTEND=noninteractive
apt update -qq
# Removed 'npm' from list as it conflicts with nodejs package
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
cd ..

# 5. Rebuild Frontend (Critical for UI updates)
echo -e "${CYAN}⚛️  Rebuilding Frontend...${NC}"
cd frontend
# Install ALL dependencies (including devDependencies like vite)
npm install
npm run build
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

# Check Firewall
echo -e "${CYAN}🔥 Checking Firewall...${NC}"
ufw allow 3000/tcp > /dev/null 2>&1
ufw allow 8000/tcp > /dev/null 2>&1
ufw allow 22/tcp > /dev/null 2>&1
ufw allow 1194/udp > /dev/null 2>&1
ufw allow 51820/udp > /dev/null 2>&1
ufw --force enable > /dev/null 2>&1

echo -e "${CYAN}🔄 Restarting Services...${NC}"
systemctl daemon-reload
systemctl restart vpnmaster-backend

# Check Nginx Config
if ! nginx -t > /dev/null 2>&1; then
    repair_nginx
else
    systemctl restart nginx
fi

# Final Port Check
if ! netstat -tuln | grep -q ":3000"; then
    echo -e "${RED}⚠️ Warning: Port 3000 still not listening. Trying force repair...${NC}"
    repair_nginx
fi

echo -e "${GREEN}✅ Update Successfully Completed!${NC}"
echo -e "${GREEN}   Version: $(git rev-parse --short HEAD)${NC}"
echo -e "${GREEN}   Version: $(git rev-parse --short HEAD)${NC}"
