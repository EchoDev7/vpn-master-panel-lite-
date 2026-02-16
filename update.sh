#!/bin/bash

# colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🚀 Starting Update Process...${NC}"

# 1. Update Source Code
echo -e "${CYAN}📥 Pulling latest changes...${NC}"
git pull origin main

# 2. Install Missing System Packages (The fix we added)
echo -e "${CYAN}📦 Installing VPN Core Services (OpenVPN/WireGuard)...${NC}"
apt update -qq
apt install -y openvpn wireguard wireguard-tools iptables iptables-persistent

# 3. Enable IP Forwarding (The fix we added)
echo -e "${CYAN}🔧 Configuring IP Forwarding...${NC}"
if ! grep -q "net.ipv4.ip_forward=1" /etc/sysctl.conf; then
    echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
    sysctl -p
fi

# 4. Update Backend Dependencies
echo -e "${CYAN}🐍 Updating Python Dependencies...${NC}"
cd backend
if [ -d "venv" ]; then
    source venv/bin/activate
    pip install -r requirements.txt
else
    echo "Virtual environment not found, skipping python update."
fi
cd ..

# 5. Restart Backend Service
echo -e "${CYAN}🔄 Restarting Backend Service...${NC}"
systemctl restart vpnmaster-backend

echo -e "${GREEN}✅ Update Complete! Your server is now up to date.${NC}"
