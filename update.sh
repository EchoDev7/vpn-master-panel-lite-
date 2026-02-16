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

echo -e "${CYAN}🚀 Starting VPN Master Panel Update...${NC}"

# 1. Update Source Code (Force Reset to avoid conflicts)
echo -e "${CYAN}📥 Fetching latest version...${NC}"
git fetch --all
git reset --hard origin/main
git pull origin main

# 2. Update System Packages (Security Patches)
echo -e "${CYAN}📦 Updating System Packages...${NC}"
export DEBIAN_FRONTEND=noninteractive
apt update -qq
apt install -y openvpn wireguard wireguard-tools iptables iptables-persistent nodejs npm python3-pip

# 3. Enable IP Forwarding (Ensure it persists)
if ! grep -q "net.ipv4.ip_forward=1" /etc/sysctl.conf; then
    echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
    sysctl -p
fi

# 4. Update Backend Dependencies
echo -e "${CYAN}🐍 Updating Backend...${NC}"
cd backend
if [ -d "venv" ]; then
    source venv/bin/activate
    pip install -r requirements.txt
else
    echo -e "${RED}Virtual environment not found! Run install.sh first.${NC}"
    exit 1
fi
python -m py_compile app/main.py # Syntax check
cd ..

# 5. Rebuild Frontend (Critical for UI updates)
echo -e "${CYAN}⚛️  Rebuilding Frontend...${NC}"
cd frontend
npm install --production
npm run build
cd ..

# 6. Restart Services
echo -e "${CYAN}🔄 Restarting Services...${NC}"
systemctl restart vpnmaster-backend
systemctl restart nginx

echo -e "${GREEN}✅ Update Successfully Completed!${NC}"
echo -e "${GREEN}   Version: $(git rev-parse --short HEAD)${NC}"
