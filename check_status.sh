#!/bin/bash

# VPN Master Panel - System Diagnostics & Health Report
# Usage: sudo ./check_status.sh [--live]

# --- Configuration & Styling ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# Ensure script is run as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Error: This script must be run as root.${NC}"
  exit 1
fi

# Live Mode Handler
if [ "$1" == "--live" ] || [ "$1" == "-l" ]; then
    while true; do
        $0 --internal-run
        sleep 2
    done
    exit 0
fi

# Clear screen for fresh output
if [ "$1" == "--internal-run" ]; then
    clear
else
    # First run clear
    clear
fi

echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║    🔍 VPN MASTER PANEL - PROFESSIONAL SYSTEM MONITOR         ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo -e "Report Time: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo ""

# Function to print aligned status
print_status() {
    local MESSAGE="$1"
    local STATUS="$2"
    
    if [ "$STATUS" == "ok" ]; then
        echo -e "  [${GREEN}  OK  ${NC}] $MESSAGE"
    elif [ "$STATUS" == "warn" ]; then
        echo -e "  [${YELLOW} WARN ${NC}] $MESSAGE"
    else
        echo -e "  [${RED} FAIL ${NC}] $MESSAGE"
    fi
}

# --- 1. Project & System Status (Real-time) ---
echo -e "${BOLD}${YELLOW}📊 1. System & Project Status${NC}"
echo -e "--------------------------------------------------------"

# Git/Project Status
if [ -d ".git" ]; then
    BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
    COMMIT=$(git rev-parse --short HEAD 2>/dev/null)
    MSG=$(git log -1 --pretty=%B 2>/dev/null | head -n 1)
    
    echo -e "  Project Version: ${CYAN}$COMMIT${NC} ($BRANCH)"
    echo -e "  Latest Change:   ${CYAN}$MSG${NC}"
    
    # Check for uncommitted changes
    if [ -n "$(git status --porcelain)" ]; then
        echo -e "  File Changes:    ${YELLOW}⚠️  Detected Uncommitted Changes (Dev Mode?)${NC}"
        git status --short | head -n 3 | sed 's/^/    /' 
        if [ $(git status --porcelain | wc -l) -gt 3 ]; then echo "    ...and more"; fi
    else
        echo -e "  File Changes:    ${GREEN}Clean (Synced with Git)${NC}"
    fi
else
    echo -e "  Project Status:  ${YELLOW}Not a Git Repository${NC}"
fi

echo -e ""
# Load & Resources
LOAD=$(uptime | awk -F'load average:' '{ print $2 }' | xargs)
MEM_USED=$(free -m | awk '/^Mem:/{print $3}')
MEM_TOTAL=$(free -m | awk '/^Mem:/{print $2}')
MEM_PERCENT=$(( 100 * MEM_USED / MEM_TOTAL ))
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')

echo -e "  System Load:     ${CYAN}$LOAD${NC}"
if [ "$MEM_PERCENT" -gt 90 ]; then
    print_status "Memory: ${MEM_USED}MB / ${MEM_TOTAL}MB (${MEM_PERCENT}%)" "warn"
else
    print_status "Memory: ${MEM_USED}MB / ${MEM_TOTAL}MB (${MEM_PERCENT}%)" "ok"
fi

if [ "$DISK_USAGE" -gt 90 ]; then
    print_status "Disk (/): ${DISK_USAGE}%" "fail"
else
    print_status "Disk (/): ${DISK_USAGE}%" "ok"
fi

# --- 2. Service & Dependency Integrity ---
echo -e "\n${BOLD}${YELLOW}⚙️  2. Installed Packages & Versions${NC}"
echo -e "--------------------------------------------------------"

# Function to get versions
get_version() {
    local cmd=$1
    if ! command -v $cmd &> /dev/null; then echo "MISSING"; return; fi
    
    case $cmd in
        python3) python3 --version | awk '{print $2}' ;;
        pip) pip --version | awk '{print $2}' ;;
        node) node -v ;;
        npm) npm -v ;;
        openvpn) openvpn --version | head -n 1 | awk '{print $2}' ;;
        nginx) nginx -v 2>&1 | awk -F'/' '{print $2}' ;;
        git) git --version | awk '{print $3}' ;;
        curl) curl --version | head -n 1 | awk '{print $2}' ;;
        ufw) ufw --version | grep -v 'Copyright' | head -n 1 ;; # ufw version output varies
        sqlite3) sqlite3 --version | awk '{print $1}' ;;
        wg) wg --version | awk '{print $2}' ;; # usually just 'wireguard-tools v1.0...'
        docker) docker --version | awk '{print $3}' | tr -d ',' ;;
        *) echo "INSTALLED" ;;
    esac
}

DEPENDENCIES=("openvpn" "nginx" "python3" "pip" "node" "npm" "git" "curl" "ufw" "sqlite3" "wg")

for DEP in "${DEPENDENCIES[@]}"; do
    VER=$(get_version $DEP)
    if [ "$VER" == "MISSING" ]; then
        echo -e "  [${RED} MISSING  ${NC}] $DEP"
    else
        # If version check failed to return string but command exists
        if [ -z "$VER" ] || [ "$VER" == "INSTALLED" ]; then
             echo -e "  [${GREEN} INSTALLED ${NC}] $DEP"
        else
             echo -e "  [${GREEN} INSTALLED ${NC}] $DEP ${CYAN}($VER)${NC}"
        fi
    fi
done

echo -e "\n${CYAN}💡 Optimization Suggestions (Optional):${NC}"
SUGGESTIONS=("htop" "iftop" "fail2ban" "jq" "tree" "speedtest")
for SUG in "${SUGGESTIONS[@]}"; do
    if ! command -v $SUG &> /dev/null; then
         echo -e "  - ${YELLOW}$SUG${NC} is not installed (Recommended for monitoring/security)"
    else
         echo -e "  - ${GREEN}$SUG${NC} is installed"
    fi
done

# --- 3. VPN & Network Configuration ---
echo -e "\n${BOLD}${YELLOW}🔒 3. Network & VPN Configuration${NC}"
echo -e "--------------------------------------------------------"

# Public IPs
PUBLIC_IP=$(curl -4 -s --max-time 2 ifconfig.me)
PUBLIC_IPV6=$(curl -6 -s --max-time 2 -H "User-Agent: curl" ipv6.icanhazip.com)
echo -e "  Public IPv4:     ${GREEN}${PUBLIC_IP:-UNKNOWN}${NC}"
echo -e "  Public IPv6:     ${GREEN}${PUBLIC_IPV6:-NOT DETECTED}${NC}"

# Config Audits
if [ -f "/etc/openvpn/server.conf" ]; then
    OVPN_PORT=$(grep '^port ' /etc/openvpn/server.conf | awk '{print $2}')
    print_status "OpenVPN Configured (Port ${OVPN_PORT:-1194})" "ok"
else
    print_status "OpenVPN Configuration Missing" "fail"
fi

if [ -f "/etc/wireguard/wg0.conf" ]; then
    WG_PORT=$(grep '^ListenPort' /etc/wireguard/wg0.conf | awk -F'=' '{print $2}' | xargs)
    print_status "WireGuard Configured (Port ${WG_PORT:-51820})" "ok"
else
    print_status "WireGuard Verification Skipped (Config not found)" "warn"
fi

# --- 4. API & Service Health ---
echo -e "\n${BOLD}${YELLOW}🔌 4. API & Connectivity Health${NC}"
echo -e "--------------------------------------------------------"

# API Checks
API_BASE="http://127.0.0.1:8001"
APIS=(
    "/api/health|Core System"
    "/docs|Documentation"
    "/api/v1/monitoring/server-resources|Resource Monitor" 
    "/api/v1/monitoring/dashboard|Dashboard Data"
)

for API in "${APIS[@]}"; do
    ENDPOINT="${API%%|*}"
    NAME="${API##*|}"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE$ENDPOINT")
    
    if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "307" ]; then
        print_status "$NAME ($ENDPOINT) -> Connected" "ok"
    elif [ "$HTTP_CODE" == "401" ] || [ "$HTTP_CODE" == "403" ] || [ "$HTTP_CODE" == "405" ]; then
         print_status "$NAME ($ENDPOINT) -> Secured & Active" "ok"
    else
        print_status "$NAME ($ENDPOINT) -> Offline (Code: $HTTP_CODE)" "fail"
    fi
done

# --- End of Single Run ---
# If internal run (live mode), stop here
if [ "$1" == "--internal-run" ]; then
    echo -e "\n${BLUE}Updating in 2 seconds... (Ctrl+C to stop)${NC}"
    exit 0
fi

# --- Live Logs (Only for standard run) ---
echo -e "\n${BOLD}${YELLOW}🚨 5. Recent Critical Log Events${NC}"
echo -e "--------------------------------------------------------"
journalctl -p 3 -n 10 --no-pager

echo -e "\n${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Diagnostic Scan Complete.${NC}"
echo -e "💡  Tip: Run with ${BOLD}--live${NC} for real-time dashboard."
echo -e "${YELLOW}👇 Streaming Live Logs (Press Ctrl+C to stop)...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

journalctl -u vpnmaster-backend -u nginx -u openvpn@server -f -n 20
