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

if [ "$1" == "--internal-run" ]; then
    clear
else
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

# --- 1. Project & System Status ---
echo -e "${BOLD}${YELLOW}📊 1. System & Project Status${NC}"
echo -e "--------------------------------------------------------"

# Git/Project Status
if [ -d ".git" ]; then
    COMMIT=$(git rev-parse --short HEAD 2>/dev/null)
    BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
    MSG=$(git log -1 --pretty=%B 2>/dev/null | head -n 1)
    
    echo -e "  Project Version: ${CYAN}$COMMIT${NC} ($BRANCH)"
    echo -e "  Latest Change:   ${CYAN}$MSG${NC}"
    
    if [ -n "$(git status --porcelain)" ]; then
        echo -e "  File Changes:    ${YELLOW}⚠️  Uncommitted Changes Detected${NC}"
    else
        echo -e "  File Changes:    ${GREEN}Clean${NC}"
    fi
else
    echo -e "  Project Status:  ${YELLOW}Not a Git Repository${NC}"
fi

# Resources
LOAD=$(uptime | awk -F'load average:' '{ print $2 }' | xargs)
MEM_USED=$(free -m | awk '/^Mem:/{print $3}')
MEM_TOTAL=$(free -m | awk '/^Mem:/{print $2}')
MEM_PERCENT=$(( 100 * MEM_USED / MEM_TOTAL ))
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')

echo -e "\n  System Load:     ${CYAN}$LOAD${NC}"
print_status "Memory: ${MEM_USED}MB / ${MEM_TOTAL}MB (${MEM_PERCENT}%)" "$([ $MEM_PERCENT -gt 90 ] && echo "warn" || echo "ok")"
print_status "Disk (/): ${DISK_USAGE}%" "$([ $DISK_USAGE -gt 90 ] && echo "fail" || echo "ok")"

# --- 2. Package Versions & Updates ---
echo -e "\n${BOLD}${YELLOW}⚙️  2. Installed Packages & Updates${NC}"
echo -e "--------------------------------------------------------"
printf "  %-15s %-20s %-20s %s\n" "PACKAGE" "INSTALLED" "LATEST AVAILABLE" "STATUS"
echo "  -----------------------------------------------------------------------"

check_version() {
    local PKG=$1
    local CMD=$2
    local INSTALLED="Not Installed"
    local LATEST="Unknown"
    local STATUS="${RED}MISSING${NC}"
    
    # Get Installed Version
    if command -v $CMD &> /dev/null; then
        case $CMD in
            python3) INSTALLED=$(python3 --version | awk '{print $2}') ;;
            openvpn) INSTALLED=$(openvpn --version | head -n 1 | awk '{print $2}') ;;
            nginx)   INSTALLED=$(nginx -v 2>&1 | awk -F'/' '{print $2}') ;;
            git)     INSTALLED=$(git --version | awk '{print $3}') ;;
            curl)    INSTALLED=$(curl --version | head -n 1 | awk '{print $2}') ;;
            wg)      INSTALLED=$(wg --version | awk '{print $2}') ;;
            node)    INSTALLED=$(node -v) ;;
            npm)     INSTALLED=$(npm -v) ;;
            pip)     INSTALLED=$(pip --version | awk '{print $2}') ;;
            ufw)     INSTALLED=$(ufw --version | grep -v 'Copyright' | head -n 1) ;;
            sqlite3) INSTALLED=$(sqlite3 --version | awk '{print $1}') ;;
        esac
    fi
    
    # Get Latest (Candidate) Version via apt-cache
    # Map CMD to Package Name
    local APT_PKG=$PKG
    if [ "$PKG" == "pip" ]; then APT_PKG="python3-pip"; fi
    if [ "$PKG" == "node" ]; then APT_PKG="nodejs"; fi
    if [ "$PKG" == "wg" ]; then APT_PKG="wireguard"; fi
    
    if command -v apt-cache &>/dev/null; then
        CANDIDATE=$(apt-cache policy $APT_PKG 2>/dev/null | grep "Candidate:" | awk '{print $2}')
        if [ -n "$CANDIDATE" ] && [ "$CANDIDATE" != "(none)" ]; then
            LATEST="$CANDIDATE"
        else
            LATEST="-"
        fi
    fi
    
    # Determine Status
    if [ "$INSTALLED" == "Not Installed" ]; then
        STATUS="${RED}MISSING${NC}"
    elif [ "$LATEST" != "-" ] && [[ "$LATEST" != *"$INSTALLED"* ]] && [ "$PKG" != "python3" ] && [ "$PKG" != "node" ]; then
        # Simple string check isn't perfect for versions, but good enough for drift detection
        # python/node often installed via other means (pyenv/nvm), so apt version might differ irrelevantly
        STATUS="${YELLOW}UPDATE?${NC}"
    else
        STATUS="${GREEN}OK${NC}"
    fi
    
    if [ "$PKG" == "python3" ] || [ "$PKG" == "node" ] || [ "$PKG" == "npm" ] || [ "$PKG" == "pip" ]; then
        # For these, LATEST via apt might be older than installed via scripts
        STATUS="${GREEN}OK${NC}"
    fi

    printf "  %-15s %-20s %-20s %s\n" "$PKG" "${INSTALLED:0:18}" "${LATEST:0:18}" "$STATUS"
}

PACKAGES=("openvpn" "openvpn" "nginx" "nginx" "python3" "python3" "pip" "pip" "node" "node" "npm" "npm" "git" "git" "curl" "curl" "ufw" "ufw" "sqlite3" "sqlite3" "wg" "wg")

# Loop through pairs
for ((i=0; i<${#PACKAGES[@]}; i+=2)); do
    check_version "${PACKAGES[i]}" "${PACKAGES[i+1]}"
done

# --- 3. Recommended Tools ---
echo -e "\n${BOLD}${YELLOW}🛠️  3. Recommended Professional Tools${NC}"
echo -e "--------------------------------------------------------"
TOOLS=(
    "htop|Interactive process viewer|htop"
    "iftop|Bandwidth monitor|iftop"
    "fail2ban|Intrusion prevention|fail2ban-client"
    "jq|Command-line JSON processor|jq"
    "speedtest-cli|Internet speed test|speedtest"
    "tree|Directory visualization|tree"
)

for TOOL in "${TOOLS[@]}"; do
    NAME="${TOOL%%|*}"
    REST="${TOOL#*|}"
    DESC="${REST%%|*}"
    CMD="${REST#*|}"
    
    if command -v $CMD &>/dev/null; then
        echo -e "  [${GREEN}INSTALLED${NC}] ${BOLD}$NAME${NC}: $DESC"
    else
        echo -e "  [${YELLOW}MISSING${NC}]   ${BOLD}$NAME${NC}: $DESC"
    fi
done

# --- 4. Network & VPN ---
echo -e "\n${BOLD}${YELLOW}🔒 4. Network & VPN Configuration${NC}"
echo -e "--------------------------------------------------------"
PUBLIC_IP=$(curl -4 -s --max-time 2 ifconfig.me)
PUBLIC_IPV6=$(curl -6 -s --max-time 2 -H "User-Agent: curl" ipv6.icanhazip.com)
echo -e "  Public IPv4:     ${GREEN}${PUBLIC_IP:-UNKNOWN}${NC}"
echo -e "  Public IPv6:     ${GREEN}${PUBLIC_IPV6:-NOT DETECTED}${NC}"

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
    print_status "WireGuard Verification Skipped" "warn"
fi

# --- 5. API Health ---
echo -e "\n${BOLD}${YELLOW}🔌 5. API Health Check${NC}"
echo -e "--------------------------------------------------------"
API_BASE="http://127.0.0.1:8001"
APIS=("/api/health" "/docs" "/api/v1/monitoring/dashboard")

for ENDPOINT in "${APIS[@]}"; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE$ENDPOINT")
    if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "307" ] || [ "$HTTP_CODE" == "401" ] || [ "$HTTP_CODE" == "403" ]; then
        print_status "$ENDPOINT -> Online ($HTTP_CODE)" "ok"
    else
        print_status "$ENDPOINT -> Offline ($HTTP_CODE)" "fail"
    fi
done

# --- Troubleshooting Hints (Only for manual run) ---
if [ "$1" != "--internal-run" ]; then
    echo -e "\n${BOLD}${CYAN}💡 Troubleshooting Hints:${NC}"
    echo -e "  - If OpenVPN is down: Check logs with ${YELLOW}journalctl -u openvpn@server -n 50${NC}"
    echo -e "  - If API is 502: Check Nginx with ${YELLOW}systemctl status nginx${NC} or Backend with ${YELLOW}journalctl -u vpnmaster-backend${NC}"
    echo -e "  - If 'Missing' packages: Run ${YELLOW}apt update && apt install <package>${NC}"
    echo -e "  - For live dashboard: Run ${YELLOW}./check_status.sh --live${NC}"
    
    echo -e "\n${BOLD}${YELLOW}🚨 recent Logs:${NC}" 
    journalctl -p 3 -n 10 --no-pager
fi
