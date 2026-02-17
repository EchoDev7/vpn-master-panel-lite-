#!/bin/bash

# VPN Master Panel - System Diagnostics & Health Report
# Usage: sudo ./check_status.sh

# --- Configuration & Styling ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Ensure script is run as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Error: This script must be run as root to access system logs and services.${NC}"
  exit 1
fi

clear
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║    🔍 VPN MASTER PANEL - SYSTEM HEALTH & DIAGNOSTICS         ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo -e "Generated: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo ""

# Function to print aligned status
print_status() {
    local MESSAGE="$1"
    local STATUS="$2"
    local WIDTH=60
    
    if [ "$STATUS" == "ok" ]; then
        echo -e "  [${GREEN}  OK  ${NC}] $MESSAGE"
    elif [ "$STATUS" == "warn" ]; then
        echo -e "  [${YELLOW} WARN ${NC}] $MESSAGE"
    else
        echo -e "  [${RED} FAIL ${NC}] $MESSAGE"
    fi
}

# --- 1. System Resources ---
echo -e "${BOLD}${YELLOW}📊 1. System Resources${NC}"
echo -e "--------------------------------------------------------"

# Load Average
LOAD=$(uptime | awk -F'load average:' '{ print $2 }' | xargs)
echo -e "  System Load: ${CYAN}$LOAD${NC}"

# Memory Usage
MEM_USED=$(free -m | awk '/^Mem:/{print $3}')
MEM_TOTAL=$(free -m | awk '/^Mem:/{print $2}')
MEM_PERCENT=$(( 100 * MEM_USED / MEM_TOTAL ))

if [ "$MEM_PERCENT" -gt 90 ]; then
    print_status "Memory Usage: ${MEM_USED}MB / ${MEM_TOTAL}MB (${MEM_PERCENT}%)" "warn"
else
    print_status "Memory Usage: ${MEM_USED}MB / ${MEM_TOTAL}MB (${MEM_PERCENT}%)" "ok"
fi

# Disk Usage (Root Partition)
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    print_status "Disk Usage (/): ${DISK_USAGE}%" "fail"
else
    print_status "Disk Usage (/): ${DISK_USAGE}%" "ok"
fi

# --- 2. Network Interface Status ---
echo -e "\n${BOLD}${YELLOW}📡 2. Network Configuration${NC}"
echo -e "--------------------------------------------------------"

# Public IP (IPv4)
PUBLIC_IP=$(curl -4 -s --max-time 3 ifconfig.me)
if [ -z "$PUBLIC_IP" ]; then
    print_status "Public IP (IPv4) -> [UNKNOWN] (Check Internet Connection)" "warn"
else
    print_status "Public IP (IPv4): $PUBLIC_IP" "ok"
fi

# Public IP (IPv6)
PUBLIC_IPV6=$(curl -6 -s --max-time 3 -H "User-Agent: curl" ipv6.icanhazip.com)
if [ -z "$PUBLIC_IPV6" ]; then
    print_status "Public IP (IPv6) -> [NOT DETECTED/DISABLED]" "warn"
else
    print_status "Public IP (IPv6): $PUBLIC_IPV6" "ok"
fi

# Listening Ports
echo -e "\n${CYAN}Active Listening Ports:${NC}"
if command -v netstat >/dev/null; then
    netstat -tulnp | grep 'LISTEN' | awk '{printf "  %-20s %-20s\n", $4, $7}' | grep -E '(:8000|:3000|:1194|:51820|:443|:80|:22)'
else
    ss -tulnp | grep 'LISTEN' | awk '{printf "  %-20s %-20s\n", $5, $7}' | grep -E '(:8000|:3000|:1194|:51820|:443|:80|:22)'
fi

# --- 3. Core Services ---
echo -e "\n${BOLD}${YELLOW}⚙️  3. Service Status & Dependencies${NC}"
echo -e "--------------------------------------------------------"

SERVICES=("vpnmaster-backend" "nginx" "openvpn@server" "wg-quick@wg0" "ufw")
for SERVICE in "${SERVICES[@]}"; do
    if systemctl is-active --quiet "$SERVICE"; then
        print_status "Service: $SERVICE -> Running" "ok"
    else
        STATUS=$(systemctl is-failed "$SERVICE")
        if [ "$STATUS" == "failed" ]; then
            print_status "Service: $SERVICE -> FAILED (Check logs)" "fail"
        else
            print_status "Service: $SERVICE -> Stopped" "warn"
        fi
    fi
done

# Check Installed Dependencies
echo -e "\n${CYAN}Package Verification:${NC}"
DEPENDENCIES=("openvpn" "nginx" "python3" "pip" "node" "npm" "git" "curl" "ufw" "sqlite3" "wg")
ALL_DEPS_OK=true

for DEP in "${DEPENDENCIES[@]}"; do
    if command -v $DEP >/dev/null 2>&1; then
        VERSION=""
        # Concise version check
        if [ "$DEP" == "python3" ]; then
             VERSION=$(python3 --version | awk '{print $2}')
        elif [ "$DEP" == "node" ]; then
             VERSION=$(node -v)
        elif [ "$DEP" == "openvpn" ]; then
             VERSION=$(openvpn --version | head -n 1 | awk '{print $2}')
        fi
        
        if [ -n "$VERSION" ]; then
             echo -e "  [${GREEN} INSTALLED ${NC}] $DEP ($VERSION)"
        else
             echo -e "  [${GREEN} INSTALLED ${NC}] $DEP"
        fi
    else
        echo -e "  [${RED} MISSING  ${NC}] $DEP"
        ALL_DEPS_OK=false
    fi
done

if [ "$ALL_DEPS_OK" = false ]; then
    echo -e "${YELLOW}Warning: Some dependencies are missing. Run ./update.sh to fix.${NC}"
fi

# --- 4. VPN Configuration Audit ---
echo -e "\n${BOLD}${YELLOW}🔒 4. VPN Configuration Audit${NC}"
echo -e "--------------------------------------------------------"

# OpenVPN
OVPN_CONF="/etc/openvpn/server.conf"
if [ -f "$OVPN_CONF" ]; then
    OVPN_PORT=$(grep '^port ' $OVPN_CONF | awk '{print $2}')
    OVPN_PROTO=$(grep '^proto ' $OVPN_CONF | awk '{print $2}')
    print_status "OpenVPN Config Found (/etc/openvpn/server.conf)" "ok"
    echo -e "      -> Mode: ${OVPN_PROTO:-udp} | Port: ${OVPN_PORT:-1194}"
else
    print_status "OpenVPN Config MISSING" "fail"
fi

# WireGuard
WG_CONF="/etc/wireguard/wg0.conf"
if [ -f "$WG_CONF" ]; then
    WG_PORT=$(grep '^ListenPort' $WG_CONF | awk -F'=' '{print $2}' | xargs)
    print_status "WireGuard Config Found (/etc/wireguard/wg0.conf)" "ok"
    echo -e "      -> Mode: udp | Port: ${WG_PORT:-51820}"
else
    print_status "WireGuard Config Not Setup (Optional)" "warn"
fi

# --- 5. Application Connectivity & Database ---
echo -e "\n${BOLD}${YELLOW}🔌 5. Connectivity & API Health${NC}"
echo -e "--------------------------------------------------------"

# Port Checks
if nc -z 127.0.0.1 8001; then
     print_status "Backend Port (8001) -> Listening" "ok"
else
     print_status "Backend Port (8001) -> CLOSED" "fail"
fi

if nc -z 127.0.0.1 3000; then
     print_status "Frontend Port (3000) -> Listening" "ok"
else
     print_status "Frontend Port (3000) -> CLOSED" "fail"
fi

# Database Integrity
if [ -f "/opt/vpn-master-panel/backend/vpnmaster_lite.db" ]; then
    print_status "Database File Present" "ok"
    
    # Execute Python-based Deep Check
    if [ -f "/opt/vpn-master-panel/backend/check_db.py" ]; then
        cd /opt/vpn-master-panel/backend
        python3 check_db.py
        cd ..
    fi
else
    print_status "Database File MISSING" "fail"
fi

# API Health Monitor
echo -e "\n${CYAN}API Endpoint Status:${NC}"

API_BASE="http://127.0.0.1:8001"
# Format: Endpoint|Name
APIS=(
    "/api/health|System Health"
    "/docs|API Documentation"
    "/api/v1/monitoring/server-resources|System Resources" 
    "/api/v1/monitoring/dashboard|Dashboard Stats"
    "/api/v1/auth/login|Auth Service"
)

for API in "${APIS[@]}"; do
    ENDPOINT="${API%%|*}"
    NAME="${API##*|}"
    
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE$ENDPOINT")
    
    if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "307" ]; then
        print_status "API: $NAME -> [ACTIVE] ($HTTP_CODE)" "ok"
    elif [ "$HTTP_CODE" == "401" ] || [ "$HTTP_CODE" == "403" ] || [ "$HTTP_CODE" == "405" ]; then
        # 403 Forbidden is expected for secured endpoints when accessed without token
        print_status "API: $NAME -> [SECURE & ACTIVE] (Status: $HTTP_CODE)" "ok"
    else
        print_status "API: $NAME -> [OFFLINE] (Status: $HTTP_CODE)" "fail"
    fi
done

# --- 6. Security & Kernel ---
echo -e "\n${BOLD}${YELLOW}🛡️  6. Security & Kernel Settings${NC}"
echo -e "--------------------------------------------------------"

if [ -c /dev/net/tun ]; then
    print_status "TUN Device interface available" "ok"
else
    print_status "TUN Device MISSING (/dev/net/tun)" "fail"
fi

IP_FWD=$(cat /proc/sys/net/ipv4/ip_forward)
if [ "$IP_FWD" == "1" ]; then
    print_status "IPv4 Forwarding Enabled" "ok"
else
    print_status "IPv4 Forwarding DISABLED" "fail"
fi

# DEBUG: Dump OpenVPN Config if failed
if systemctl is-failed --quiet openvpn@server; then
    echo -e "\n${RED}⚠️  DEBUG: Dumping OpenVPN Config (/etc/openvpn/server.conf):${NC}"
    grep -vE '^#|^$' /etc/openvpn/server.conf | head -n 20
fi

# --- 7. Critical Logs ---
echo -e "\n${BOLD}${YELLOW}🚨 7. Recent Critical System Logs (Last 50 Lines)${NC}"
echo -e "--------------------------------------------------------"
journalctl -p 3 -n 50 --no-pager | tail -n 10

echo -e "\n${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ System Diagnostics Completed Successfully.${NC}"
echo -e "${YELLOW}👇 Streaming Live Logs (Press Ctrl+C to stop)...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Tail logs for all related services
journalctl -u vpnmaster-backend -u nginx -u openvpn@server -u wg-quick@wg0 -f -n 20
