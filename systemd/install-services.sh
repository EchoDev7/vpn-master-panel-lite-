#!/bin/bash

###############################################################################
#  VPN Master Panel - Systemd Service Installer
#  Installs and enables auto-start services
###############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Installing VPN Master Panel Services...${NC}\n"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}" 
   exit 1
fi

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${YELLOW}Project Root: $PROJECT_ROOT${NC}"

# 1. Install Backend Service
echo -e "\n${GREEN}[1/2] Installing Backend Service...${NC}"

if [ -f "$SCRIPT_DIR/vpnmaster-backend.service" ]; then
    cp "$SCRIPT_DIR/vpnmaster-backend.service" /etc/systemd/system/
    echo -e "${GREEN}✓ Backend service file copied${NC}"
else
    echo -e "${RED}✗ Service file not found: $SCRIPT_DIR/vpnmaster-backend.service${NC}"
    exit 1
fi

# 2. Reload systemd
echo -e "\n${GREEN}[2/2] Configuring Services...${NC}"
systemctl daemon-reload
echo -e "${GREEN}✓ Systemd reloaded${NC}"

# 3. Enable services (auto-start on boot)
systemctl enable vpnmaster-backend
echo -e "${GREEN}✓ Backend service enabled (auto-start on boot)${NC}"

# 4. Start services
systemctl restart vpnmaster-backend
echo -e "${GREEN}✓ Backend service started${NC}"

# 5. Wait and check status
sleep 3

if systemctl is-active --quiet vpnmaster-backend; then
    echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ All services installed and running!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "\n${YELLOW}Service Status:${NC}"
    systemctl status vpnmaster-backend --no-pager -l
    
    echo -e "\n${YELLOW}Useful Commands:${NC}"
    echo -e "  • Check status:  ${GREEN}systemctl status vpnmaster-backend${NC}"
    echo -e "  • View logs:     ${GREEN}journalctl -u vpnmaster-backend -f${NC}"
    echo -e "  • Restart:       ${GREEN}systemctl restart vpnmaster-backend${NC}"
    echo -e "  • Stop:          ${GREEN}systemctl stop vpnmaster-backend${NC}"
    echo -e "  • Disable:       ${GREEN}systemctl disable vpnmaster-backend${NC}"
    
    echo -e "\n${GREEN}✓ Services will auto-start on server reboot${NC}\n"
else
    echo -e "\n${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}✗ Backend service failed to start${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "\n${YELLOW}Checking logs:${NC}"
    journalctl -u vpnmaster-backend -n 50 --no-pager
    exit 1
fi
