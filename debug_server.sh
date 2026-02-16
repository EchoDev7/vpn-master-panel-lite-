#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🔍 VPN Master Panel - Diagnostic Tool${NC}"
echo "==============================================="

# 1. System Resources
echo -e "\n${YELLOW}1. System Resources:${NC}"
free -m
uptime

# 2. Service Status
echo -e "\n${YELLOW}2. Service Status:${NC}"
echo -n "Nginx: "
if systemctl is-active --quiet nginx; then echo -e "${GREEN}Running${NC}"; else echo -e "${RED}Stopped${NC}"; fi

echo -n "Backend: "
if systemctl is-active --quiet vpnmaster-backend; then echo -e "${GREEN}Running${NC}"; else echo -e "${RED}Stopped${NC}"; fi

# 3. Port Check (Listening?)
echo -e "\n${YELLOW}3. Network Ports (Listening?):${NC}"
netstat -tuln | grep -E "3000|8000|8001" || echo -e "${RED}❌ No relevant ports found listening!${NC}"

# 4. Firewall Status
echo -e "\n${YELLOW}4. Firewall Rules (UFW):${NC}"
ufw status | grep -E "3000|8000" || echo -e "${RED}❌ Ports 3000/8000 NOT explicitly allowed in UFW${NC}"

# 5. Connectivy Test
echo -e "\n${YELLOW}5. Internal Connectivity Test (Localhost):${NC}"
echo -n "Frontend (Port 3000): "
curl -s -I http://127.0.0.1:3000 | head -n 1 || echo -e "${RED}Failed${NC}"
echo -n "Backend API (Port 8000): "
curl -s -I http://127.0.0.1:8000 | head -n 1 || echo -e "${RED}Failed${NC}"

# 6. Logs
echo -e "\n${YELLOW}6. Recent Backend Logs (Last 20 lines):${NC}"
journalctl -u vpnmaster-backend -n 20 --no-pager

echo -e "\n${YELLOW}7. Recent Nginx Error Logs (Last 20 lines):${NC}"
tail -n 20 /var/log/nginx/error.log 2>/dev/null || echo -e "${RED}Nginx error log not found${NC}"

echo -e "\n${YELLOW}8. Nginx Configuration Utility:${NC}"
nginx -t
