#!/bin/bash

# VPN Master Panel - ULTRA Comprehensive Status Check & Logs
# Usage: sudo ./check_status.sh

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

clear
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║    🔍 VPN MASTER PANEL - ULTIMATE DIAGNOSTICS TOOL           ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to print status
print_status() {
    if [ "$2" == "ok" ]; then
        echo -e "  [${GREEN}OK${NC}] $1"
    elif [ "$2" == "warn" ]; then
        echo -e "  [${YELLOW}WARN${NC}] $1"
    else
        echo -e "  [${RED}FAIL${NC}] $1"
    fi
}

# 1. System Vital Signs
echo -e "${BOLD}${YELLOW}📊 1. System Vital Signs${NC}"
echo -e "--------------------------------------------------------"
# Load Average
LOAD=$(uptime | awk -F'load average:' '{ print $2 }' | xargs)
echo -e "  Load Average: ${CYAN}$LOAD${NC}"

# Memory
MEM_USED=$(free -m | awk '/^Mem:/{print $3}')
MEM_TOTAL=$(free -m | awk '/^Mem:/{print $2}')
MEM_PERCENT=$(( 100 * MEM_USED / MEM_TOTAL ))
if [ "$MEM_PERCENT" -gt 90 ]; then
    print_status "Memory Usage: ${MEM_USED}MB / ${MEM_TOTAL}MB (${MEM_PERCENT}%)" "warn"
else
    print_status "Memory Usage: ${MEM_USED}MB / ${MEM_TOTAL}MB (${MEM_PERCENT}%)" "ok"
fi

# Disk
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    print_status "Disk Usage: ${DISK_USAGE}%" "fail"
else
    print_status "Disk Usage: ${DISK_USAGE}%" "ok"
fi

# 2. Network & Ports
echo -e "\n${BOLD}${YELLOW}📡 2. Network & Ports${NC}"
echo -e "--------------------------------------------------------"
# List listening ports (IPv4 Preferred)
echo -e "${CYAN}Listening Ports (Service : Port -> Process):${NC}"
if command -v netstat >/dev/null; then
    # Show PID/Program name, filter for LISTEN, mostly IPv4 or IPv6 mapped
    netstat -tulnp | grep 'LISTEN' | awk '{printf "  %-20s %-20s\n", $4, $7}' | grep -E '(:8000|:3000|:1194|:51820|:443|:80|:22)'
else
    ss -tulnp | grep 'LISTEN' | awk '{printf "  %-20s %-20s\n", $5, $7}' | grep -E '(:8000|:3000|:1194|:51820|:443|:80|:22)'
fi

# Public IP Check
PUBLIC_IP=$(curl -4 -s --max-time 3 ifconfig.me)
if [ -z "$PUBLIC_IP" ]; then
    print_status "Public IP (IPv4) -> [UNKNOWN] (Internet issue?)" "warn"
else
    print_status "Public IP (IPv4): $PUBLIC_IP" "ok"
fi

# IPv6 Check (New Feature)
PUBLIC_IPV6=$(curl -6 -s --max-time 3 ifconfig.co)
if [ -z "$PUBLIC_IPV6" ]; then
    print_status "Public IP (IPv6) -> [NOT DETECTED/DISABLED]" "warn"
else
    print_status "Public IP (IPv6): $PUBLIC_IPV6" "ok"
fi

# 3. Service Health & Dependencies
echo -e "\n${BOLD}${YELLOW}⚙️  3. Service Health & Dependencies${NC}"
echo -e "--------------------------------------------------------"
SERVICES=("vpnmaster-backend" "nginx" "openvpn@server" "wg-quick@wg0" "ufw")
for SERVICE in "${SERVICES[@]}"; do
    if systemctl is-active --quiet "$SERVICE"; then
        print_status "Service: $SERVICE running" "ok"
    else
        STATUS=$(systemctl is-failed "$SERVICE")
        if [ "$STATUS" == "failed" ]; then
            print_status "Service: $SERVICE FAILED - Run: systemctl status $SERVICE -l" "fail"
        else
            print_status "Service: $SERVICE stopped" "warn"
        fi
    fi
done

# Check Dependencies (New Feature)
echo -e "\n${CYAN}📦 System Dependencies Check:${NC}"
DEPENDENCIES=("openvpn" "nginx" "python3" "pip" "node" "npm" "git" "curl" "ufw" "sqlite3" "wg")
for DEP in "${DEPENDENCIES[@]}"; do
    if command -v $DEP >/dev/null 2>&1; then
        VERSION=""
        # Try to get short version string
        if [ "$DEP" == "python3" ]; then
             VERSION=$(python3 --version | awk '{print $2}')
        elif [ "$DEP" == "node" ]; then
             VERSION=$(node -v)
        elif [ "$DEP" == "openvpn" ]; then
             VERSION=$(openvpn --version | head -n 1 | awk '{print $2}')
        fi
        
        if [ -n "$VERSION" ]; then
             print_status "Package: $DEP ($VERSION) -> [INSTALLED]" "ok"
        else
             print_status "Package: $DEP -> [INSTALLED]" "ok"
        fi
    else
        print_status "Package: $DEP -> [NOT INSTALLED]" "fail"
    fi
done

# 4. VPN Configuration Checks (New Feature)
echo -e "\n${BOLD}${YELLOW}🔒 4. VPN Configuration & Ports${NC}"
echo -e "--------------------------------------------------------"

# OpenVPN Config Check
OVPN_CONF="/etc/openvpn/server.conf"
if [ -f "$OVPN_CONF" ]; then
    OVPN_PORT=$(grep '^port ' $OVPN_CONF | awk '{print $2}')
    OVPN_PROTO=$(grep '^proto ' $OVPN_CONF | awk '{print $2}')
    print_status "OpenVPN Config: Found ($OVPN_CONF)" "ok"
    echo -e "  -> Configured Port: ${CYAN}${OVPN_PORT:-1194}/${OVPN_PROTO:-udp}${NC}"
else
    print_status "OpenVPN Config: MISSING ($OVPN_CONF)" "fail"
fi

# WireGuard Config Check
WG_CONF="/etc/wireguard/wg0.conf"
if [ -f "$WG_CONF" ]; then
    WG_PORT=$(grep '^ListenPort' $WG_CONF | awk -F'=' '{print $2}' | xargs)
    print_status "WireGuard Config: Found ($WG_CONF)" "ok"
    echo -e "  -> Configured Port: ${CYAN}${WG_PORT:-51820}/udp${NC}"
else
    print_status "WireGuard Config: MISSING ($WG_CONF) (Expected if not set up)" "warn"
fi

# 5. Full Stack & API Connectivity
echo -e "\n${BOLD}${YELLOW}🔌 5. Full Stack & API Connectivity${NC}"
echo -e "--------------------------------------------------------"

# Backend Port Check
if nc -z 127.0.0.1 8001; then
     print_status "Backend Port (8001) -> [OPEN]" "ok"
else
     print_status "Backend Port (8001) -> [CLOSED]" "fail"
fi

# Frontend Port Check
if nc -z 127.0.0.1 3000; then
     print_status "Frontend Port (3000) -> [OPEN]" "ok"
else
     print_status "Frontend Port (3000) -> [CLOSED]" "fail"
fi

# Database File Check
if [ -f "/opt/vpn-master-panel/backend/vpnmaster_lite.db" ]; then
    print_status "Database File -> [FOUND]" "ok"
    # Run deep check script
    if [ -f "/opt/vpn-master-panel/backend/check_db.py" ]; then
        cd /opt/vpn-master-panel/backend
        python3 check_db.py
        cd ..
    fi
else
    print_status "Database File -> [MISSING]" "fail"
fi

# API Endpoint Checks
echo -e "\n${CYAN}🔗 API Health Monitor:${NC}"

API_BASE="http://127.0.0.1:8001"
APIS=(
    "/api/health|System Health"
    "/docs|API Documentation"
    "/api/v1/monitoring/system|System Monitor" 
    "/api/v1/auth/login|Auth Service"
)

for API in "${APIS[@]}"; do
    ENDPOINT="${API%%|*}"
    NAME="${API##*|}"
    
    # Capture HTTP Code only
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE$ENDPOINT")
    
    if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "405" ] || [ "$HTTP_CODE" == "401" ] || [ "$HTTP_CODE" == "307" ]; then
        # 405/401/307 is fine, means service operates (Method Not Allowed / Unauthorized / Redirect)
        print_status "API: $NAME ($ENDPOINT) -> [ONLINE] (Code: $HTTP_CODE)" "ok"
    else
        print_status "API: $NAME ($ENDPOINT) -> [OFFLINE] (Code: $HTTP_CODE)" "fail"
    fi
done

# 6. Core Check
echo -e "\n${BOLD}${YELLOW}🛡️  6. System Core Check${NC}"
echo -e "--------------------------------------------------------"
if [ -c /dev/net/tun ]; then
    print_status "TUN Device available" "ok"
else
    print_status "TUN Device MISSING (/dev/net/tun)" "fail"
fi

IP_FWD=$(cat /proc/sys/net/ipv4/ip_forward)
if [ "$IP_FWD" == "1" ]; then
    print_status "IP Forwarding enabled" "ok"
else
    print_status "IP Forwarding DISABLED" "fail"
fi

# DEBUG: Dump OpenVPN Config if service is failed
if systemctl is-failed --quiet openvpn@server; then
    echo -e "\n${RED}⚠️  OpenVPN Configuration (/etc/openvpn/server.conf):${NC}"
    grep -vE '^#|^$' /etc/openvpn/server.conf | head -n 20
fi

echo -e "\n${BOLD}${YELLOW}🚨 7. Recent Critical Errors (Last 50 lines)${NC}"
echo -e "--------------------------------------------------------"
journalctl -p 3 -n 50 --no-pager | tail -n 20

echo -e "\n${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Diagnostics Complete.${NC}"
echo -e "👇 Streaming LIVE Logs (Press Ctrl+C to stop)..."
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Tail logs safely
journalctl -u vpnmaster-backend -u nginx -u openvpn@server -f -n 20
