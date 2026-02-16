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
npm install --production
npm run build
cd ..

# 6. Restart Services
echo -e "${CYAN}🔄 Restarting Services...${NC}"
systemctl restart vpnmaster-backend
systemctl restart nginx

echo -e "${GREEN}✅ Update Successfully Completed!${NC}"
echo -e "${GREEN}   Version: $(git rev-parse --short HEAD)${NC}"
