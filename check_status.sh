#!/bin/bash

# VPN Master Panel - Comprehensive Status Check & Logs
# Usage: sudo ./check_status.sh

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

clear
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     🔍 VPN MASTER PANEL - COMPREHENSIVE DIAGNOSTICS          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 1. Check Listening Ports
echo -e "${YELLOW}📡 1. Active Ports (Listening)${NC}"
echo -e "--------------------------------------------------------"
if command -v netstat >/dev/null; then
    netstat -tulnp | grep -E '(:8000|:3000|:1194|:51820|:443|:80|:22)' | awk '{print $4 " \t" $7}' | sort
else
    ss -tulnp | grep -E '(:8000|:3000|:1194|:51820|:443|:80|:22)' | awk '{print $5 " \t" $7}' | sort
fi
echo ""

# 2. Check Service Status
echo -e "${YELLOW}⚙️  2. Service Status${NC}"
echo -e "--------------------------------------------------------"
check_service() {
    if systemctl is-active --quiet "$1"; then
        echo -e "  $1: \t${GREEN}● ACTIVE${NC}"
    else
        if systemctl is-failed --quiet "$1"; then
            echo -e "  $1: \t${RED}● FAILED${NC}"
        else
            echo -e "  $1: \t${YELLOW}● STOPPED/INACTIVE${NC}"
        fi
    fi
}

check_service "vpnmaster-backend"
check_service "nginx"
check_service "openvpn@server"
check_service "wg-quick@wg0"
check_service "ufw"
echo ""

# 3. Common Issues Check
echo -e "${YELLOW}⚠️  3. Common Issues Check${NC}"
echo -e "--------------------------------------------------------"

# Check Disk Space
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo -e "  ${RED}❌ Disk Space Critical: ${DISK_USAGE}% used${NC}"
else
    echo -e "  ${GREEN}✓ Disk Space OK (${DISK_USAGE}%)${NC}"
fi

# Check Python Backend Connection
if curl -s http://127.0.0.1:8001/health >/dev/null; then
     echo -e "  ${GREEN}✓ Backend API (Port 8001) is responding${NC}"
else
     echo -e "  ${RED}❌ Backend API (Port 8001) is NOT responding${NC}"
fi

# Check OpenVPN Tun
if [ -c /dev/net/tun ]; then
    echo -e "  ${GREEN}✓ TUN Device (/dev/net/tun) exists${NC}"
else
    echo -e "  ${RED}❌ TUN Device MISSING! Run: mkdir -p /dev/net && mknod /dev/net/tun c 10 200${NC}"
fi

# Check IP Forwarding
if grep -q "1" /proc/sys/net/ipv4/ip_forward; then
    echo -e "  ${GREEN}✓ IP Forwarding ENABLED${NC}"
else
    echo -e "  ${RED}❌ IP Forwarding DISABLED! VPN will not work.${NC}"
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Diagnostics Complete.${NC}"
echo -e "${YELLOW}👇 Streaming Live Logs (Press Ctrl+C to exit)...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 4. Stream Logs
journalctl -u vpnmaster-backend -u openvpn@server -u openvpn -u wg-quick@wg0 -u nginx -f --output cat
