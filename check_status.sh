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
# List listening ports
# List listening ports (IPv4 Preferred)
echo -e "${CYAN}Listening Ports (Service : Port -> Process):${NC}"
if command -v netstat >/dev/null; then
    # Show PID/Program name, filter for LISTEN, mostly IPv4 or IPv6 mapped
    netstat -tulnp | grep 'LISTEN' | awk '{printf "  %-20s %-20s\n", $4, $7}' | grep -E '(:8000|:3000|:1194|:51820|:443|:80|:22)'
else
    ss -tulnp | grep 'LISTEN' | awk '{printf "  %-20s %-20s\n", $5, $7}' | grep -E '(:8000|:3000|:1194|:51820|:443|:80|:22)'
fi

# Public IP Check (Forced IPv4)
PUBLIC_IP=$(curl -4 -s --max-time 3 ifconfig.me)
if [ -z "$PUBLIC_IP" ]; then
    print_status "Cannot detect Public IP (Internet issue?)" "warn"
else
    print_status "Public IP (IPv4): $PUBLIC_IP" "ok"
fi

# 3. Service Health
echo -e "\n${BOLD}${YELLOW}⚙️  3. Service Health${NC}"
echo -e "--------------------------------------------------------"
SERVICES=("vpnmaster-backend" "nginx" "openvpn@server" "wg-quick@wg0" "ufw")
for SERVICE in "${SERVICES[@]}"; do
    if systemctl is-active --quiet "$SERVICE"; then
        print_status "$SERVICE running" "ok"
    else
        STATUS=$(systemctl is-failed "$SERVICE")
        if [ "$STATUS" == "failed" ]; then
            print_status "$SERVICE FAILED - Run: systemctl status $SERVICE -l" "fail"
        else
            print_status "$SERVICE stopped" "warn"
        fi
    fi
done

# Check for ANY failed units in system
FAILED_UNITS=$(systemctl list-units --state=failed --no-legend)
if [ -n "$FAILED_UNITS" ]; then
    echo -e "\n${RED}⚠️  Other Failed System Units:${NC}"
    echo "$FAILED_UNITS"
fi

# 4. Full Stack Connectivity Check (Frontend -> Nginx -> Backend)
echo -e "\n${BOLD}${YELLOW}🔌 4. Full Stack Connectivity Check${NC}"
echo -e "--------------------------------------------------------"

# 4.1 Backend Direct Check (Internal)
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/health)
if [ "$HTTP_CODE" == "200" ]; then
    print_status "Backend API (Internal Port 8001) -> [CONNECTED]" "ok"
else
    print_status "Backend API (Internal Port 8001) -> [DISCONNECTED] (Code: $HTTP_CODE)" "fail"
fi

# 4.2 Nginx Proxy Check (External API Path)
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3000/api/health)
if [ "$HTTP_CODE" == "200" ]; then
    print_status "Nginx Reverse Proxy (/api -> Backend) -> [CONNECTED]" "ok"
else
    print_status "Nginx Reverse Proxy (/api -> Backend) -> [BROKEN] (Code: $HTTP_CODE)" "fail"
fi

# 4.3 Frontend Static Files Check
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3000/)
if [ "$HTTP_CODE" == "200" ]; then
    print_status "Frontend UI (Port 3000) -> [SERVING]" "ok"
else
    print_status "Frontend UI (Port 3000) -> [DOWN/ERROR] (Code: $HTTP_CODE)" "fail"
fi

# 4.4 Database Check (Deep Diagnostics)
if [ -f "/opt/vpn-master-panel/backend/vpnmaster_lite.db" ]; then
    print_status "Database File (SQLite) -> [FOUND]" "ok"
    # Run deep check script
    if [ -f "/opt/vpn-master-panel/backend/check_db.py" ]; then
        cd /opt/vpn-master-panel/backend
        python3 check_db.py
        cd ..
    else
        # Fallback basic check
        if sqlite3 /opt/vpn-master-panel/backend/vpnmaster_lite.db "PRAGMA integrity_check;" | grep -q "ok"; then
             print_status "Database Integrity -> [VALID]" "ok"
        else
             print_status "Database Integrity -> [CORRUPT]" "fail"
        fi
    fi
else
    print_status "Database File (SQLite) -> [MISSING]" "fail"
fi

# 5. Tun/Forwarding Check
echo -e "\n${BOLD}${YELLOW}🛡️  5. VPN Core Check${NC}"
echo -e "--------------------------------------------------------"
if [ -c /dev/net/tun ]; then
    print_status "TUN Device available" "ok"
else
    print_status "TUN Device MISSING (/dev/net/tun)" "fail"
fi

# DEBUG: Dump OpenVPN Config if service is failed
if systemctl is-failed --quiet openvpn@server; then
    echo -e "\n${RED}⚠️  OpenVPN Configuration (/etc/openvpn/server.conf):${NC}"
    if [ -f /etc/openvpn/server.conf ]; then
        cat /etc/openvpn/server.conf | grep -v "^#" | grep -v "^$"
    else
        echo "Config file not found!"
    fi
fi

IP_FWD=$(cat /proc/sys/net/ipv4/ip_forward)
if [ "$IP_FWD" == "1" ]; then
    print_status "IP Forwarding enabled" "ok"
else
    print_status "IP Forwarding DISABLED" "fail"
fi

# 6. Critical Log Analysis (Last 50 lines)
echo -e "\n${BOLD}${YELLOW}🚨 6. Recent Critical Errors (Last 50 lines)${NC}"
echo -e "--------------------------------------------------------"
if [ -f /var/log/syslog ]; then
    grep -i "error\|fail\|denied" /var/log/syslog | tail -n 5
    echo -e "${CYAN}... (checks syslog)${NC}"
fi
dmesg | grep -i "wireguard\|tun\|refused\|denied" | tail -n 5
echo -e "${CYAN}... (checks kernel dmesg)${NC}"

echo -e "\n${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Diagnostics Complete.${NC}"
echo -e "${YELLOW}👇 Streaming LIVE Logs (Press Ctrl+C to stop)...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 7. Unified Live Log Stream
journalctl -u vpnmaster-backend -u openvpn@server -u openvpn -u wg-quick@wg0 -u nginx -u ufw -u fail2ban -f --output cat
