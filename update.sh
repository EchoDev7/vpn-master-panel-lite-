#!/bin/bash

# VPN Master Panel - Auto Update Script
# Usage: sudo ./update.sh

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_info()    { echo -e "${CYAN}ℹ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
print_error()   { echo -e "${RED}✗ $1${NC}"; }

declare -a UPDATE_SUMMARY

record_summary() {
    local item="$1"
    local result="$2"
    local details="$3"
    UPDATE_SUMMARY+=("${item}|${result}|${details}")
}

unit_active_state() {
    local unit="$1"
    if systemctl is-active --quiet "$unit" 2>/dev/null; then
        echo "active"
    else
        local state
        state=$(systemctl is-active "$unit" 2>/dev/null || echo "unknown")
        echo "$state"
    fi
}

print_update_summary() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  Update Operation Summary${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    if [ ${#UPDATE_SUMMARY[@]} -eq 0 ]; then
        echo -e "${YELLOW}No summary entries recorded.${NC}"
        return
    fi
    for row in "${UPDATE_SUMMARY[@]}"; do
        IFS='|' read -r item result details <<< "$row"
        if [ "$result" = "ok" ]; then
            echo -e "  ${GREEN}✓${NC} ${item}: ${details}"
        elif [ "$result" = "warn" ]; then
            echo -e "  ${YELLOW}⚠${NC} ${item}: ${details}"
        else
            echo -e "  ${RED}✗${NC} ${item}: ${details}"
        fi
    done
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

restart_unit_if_exists() {
    local unit="$1"
    local label="$2"
    if systemctl list-unit-files | grep -q "^${unit}"; then
        if systemctl restart "$unit" > /dev/null 2>&1; then
            local state
            state=$(unit_active_state "$unit")
            print_success "${label} restarted (${unit})"
            record_summary "$label" "ok" "restarted (${unit}) -> ${state}"
        else
            local state
            state=$(unit_active_state "$unit")
            print_warning "${label} restart failed (${unit})"
            record_summary "$label" "warn" "restart failed (${unit}) -> ${state}"
        fi
        return 0
    fi
    record_summary "$label" "warn" "unit not found (${unit})"
    return 1
}

reload_or_restart_nginx() {
    if ! command -v nginx > /dev/null 2>&1; then
        print_warning "nginx binary not found"
        record_summary "Nginx" "warn" "binary not found"
        return 1
    fi
    if nginx -t > /dev/null 2>&1; then
        systemctl reload nginx > /dev/null 2>&1 || systemctl restart nginx > /dev/null 2>&1
        print_success "Nginx config verified and reloaded"
        record_summary "Nginx" "ok" "config test passed; reload/restart attempted"
    else
        print_warning "Nginx config test failed, trying repair"
        record_summary "Nginx" "warn" "config test failed; repair triggered"
        if declare -f repair_nginx > /dev/null 2>&1; then
            repair_nginx
        else
            # For quick-action mode we may not have defined repair_nginx yet.
            systemctl restart nginx > /dev/null 2>&1 || true
        fi
    fi
}

# Check Root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}"
   exit 1
fi

INSTALL_DIR="/opt/vpn-master-panel"

# If admin runs update.sh from a different folder (e.g. a separate clone in /root),
# re-exec the installed copy so behavior matches the currently deployed version.
SCRIPT_REAL=""
if command -v readlink > /dev/null 2>&1; then
    SCRIPT_REAL=$(readlink -f "$0" 2>/dev/null || true)
fi
INSTALLED_SCRIPT="${INSTALL_DIR}/update.sh"
if [ -n "$SCRIPT_REAL" ] && [ -f "$INSTALLED_SCRIPT" ] && [ "$SCRIPT_REAL" != "$INSTALLED_SCRIPT" ]; then
    echo -e "${YELLOW}⚠ Detected update.sh was launched from: ${SCRIPT_REAL}${NC}"
    echo -e "${CYAN}➡ Re-running the installed updater: ${INSTALLED_SCRIPT}${NC}"
    exec "$INSTALLED_SCRIPT" "$@"
fi

usage() {
    echo ""
    echo "Usage: sudo ./update.sh [command]"
    echo ""
    echo "Commands (no command = full update):"
    echo "  restart-all           Restart backend + OpenVPN + WireGuard + Fail2Ban + Nginx"
    echo "  reset-openvpn         Hard reset OpenVPN service (stop/kill/start + reset-failed)"
    echo "  restart-openvpn       Restart OpenVPN service"
    echo "  restart-backend       Restart backend service"
    echo "  restart-nginx         Reload/restart Nginx (with config test)"
    echo "  restart-frontend      Reload Nginx only (frontend is static)"
    echo "  rebuild-frontend      npm install + npm run build + reload Nginx"
    echo "  status                Show status (backend/openvpn/nginx)"
    echo "  logs-openvpn          Tail OpenVPN logs"
    echo "  logs-backend          Tail backend logs"
    echo ""
}

detect_backend_service() {
    if systemctl list-unit-files 2>/dev/null | grep -q '^vpn-panel-backend.service'; then
        echo "vpn-panel-backend"
    elif systemctl list-unit-files 2>/dev/null | grep -q '^vpnmaster-backend.service'; then
        echo "vpnmaster-backend"
    else
        echo ""
    fi
}

restart_openvpn() {
    restart_unit_if_exists "openvpn@server.service" "OpenVPN" || restart_unit_if_exists "openvpn.service" "OpenVPN" || true
}

reset_openvpn() {
    print_info "Hard resetting OpenVPN..."
    systemctl daemon-reload > /dev/null 2>&1 || true
    systemctl reset-failed openvpn@server openvpn > /dev/null 2>&1 || true
    systemctl stop openvpn@server > /dev/null 2>&1 || true
    systemctl stop openvpn > /dev/null 2>&1 || true
    pkill -x openvpn > /dev/null 2>&1 || true
    sleep 1
    systemctl start openvpn@server > /dev/null 2>&1 || systemctl start openvpn > /dev/null 2>&1 || true
    restart_openvpn
}

restart_backend() {
    local svc
    svc=$(detect_backend_service)
    if [ -n "$svc" ]; then
        restart_unit_if_exists "${svc}.service" "Backend"
    else
        print_warning "No backend service unit found (vpn-panel-backend/vpnmaster-backend)."
    fi
}

restart_frontend() {
    # Frontend is served as static files by Nginx in this project.
    reload_or_restart_nginx
}

rebuild_frontend() {
    if ! command -v npm > /dev/null 2>&1; then
        print_error "npm not found. Install nodejs/npm first (or run full update with no args)."
        return 1
    fi
    if [ ! -d "$INSTALL_DIR/frontend" ]; then
        print_error "frontend directory not found at $INSTALL_DIR/frontend"
        return 1
    fi
    print_info "Rebuilding frontend..."
    (cd "$INSTALL_DIR/frontend" && npm install && npm run build) || return 1
    chmod -R 755 "$INSTALL_DIR/frontend/dist" 2>/dev/null || true
    reload_or_restart_nginx
}

show_status() {
    local svc
    svc=$(detect_backend_service)
    echo ""
    echo "=== Status ==="
    [ -n "$svc" ] && systemctl status "${svc}.service" --no-pager -l || true
    systemctl status openvpn@server.service --no-pager -l 2>/dev/null || systemctl status openvpn.service --no-pager -l 2>/dev/null || true
    systemctl status nginx.service --no-pager -l 2>/dev/null || true
}

tail_logs_openvpn() {
    if [ -f "/var/log/openvpn/openvpn.log" ]; then
        tail -n 200 /var/log/openvpn/openvpn.log
    fi
    if [ -f "/var/log/openvpn/auth.log" ]; then
        tail -n 200 /var/log/openvpn/auth.log
    fi
    journalctl -u openvpn@server.service -n 200 --no-pager 2>/dev/null || true
}

tail_logs_backend() {
    local svc
    svc=$(detect_backend_service)
    if [ -n "$svc" ]; then
        journalctl -u "${svc}.service" -n 200 --no-pager 2>/dev/null || true
    else
        print_warning "Backend unit not found."
    fi
}

echo -e "${CYAN}🚀 Starting VPN Master Panel Update...${NC}"

# 0. Verify Installation Directory
if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "${RED}Error: Installation not found at $INSTALL_DIR${NC}"
    echo -e "${RED}Please run install.sh first.${NC}"
    exit 1
fi

echo -e "${CYAN}📌 Effective install dir: ${INSTALL_DIR}${NC}"
if [ -d "${INSTALL_DIR}/.git" ]; then
    CUR_SHA=$(cd "$INSTALL_DIR" && git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    echo -e "${CYAN}📌 Current installed version (before update): ${CUR_SHA}${NC}"
fi

# Quick action mode: allow update.sh to be used as an admin ops tool.
if [ $# -gt 0 ]; then
    case "$1" in
        -h|--help|help)
            usage
            exit 0
            ;;
        restart-all)
            systemctl daemon-reload > /dev/null 2>&1 || true
            systemctl reset-failed > /dev/null 2>&1 || true
            restart_backend
            restart_openvpn
            restart_unit_if_exists "wg-quick@wg0.service" "WireGuard" || true
            restart_unit_if_exists "fail2ban.service" "Fail2Ban" || true
            restart_frontend
            exit 0
            ;;
        reset-openvpn)
            reset_openvpn
            exit 0
            ;;
        restart-openvpn)
            restart_openvpn
            exit 0
            ;;
        restart-backend)
            restart_backend
            exit 0
            ;;
        restart-nginx)
            reload_or_restart_nginx
            exit 0
            ;;
        restart-frontend)
            restart_frontend
            exit 0
            ;;
        rebuild-frontend)
            rebuild_frontend
            exit 0
            ;;
        status)
            show_status
            exit 0
            ;;
        logs-openvpn)
            tail_logs_openvpn
            exit 0
            ;;
        logs-backend)
            tail_logs_backend
            exit 0
            ;;
        *)
            print_error "Unknown command: $1"
            usage
            exit 1
            ;;
    esac
fi

# 1. Update Source Code (Non-destructive)
echo -e "${CYAN}📥 Updating Installation at $INSTALL_DIR...${NC}"
cd "$INSTALL_DIR" || exit 1

# Check if it's a git repo
if [ -d ".git" ]; then
    echo -e "${CYAN}Fetching updates...${NC}"
    
    # Try standard fetch first
    if ! GIT_TERMINAL_PROMPT=0 git fetch origin; then
        echo -e "${YELLOW}⚠️ Connection to GitHub failed (likely due to regional blocking).${NC}"
        echo -e "${CYAN}🔄 Attempting to use GitHub Proxy mirror (gh-proxy.com)...${NC}"
        
        # Determine the current remote URL
        CURRENT_REMOTE=$(git remote get-url origin)
        
        # If it's already a proxied URL, we don't double proxy.
        # IMPORTANT: this project repo name includes a trailing dash: vpn-master-panel-lite-
        if [[ "$CURRENT_REMOTE" != *"gh-proxy "* && "$CURRENT_REMOTE" != *"ghproxy"* ]]; then
            # Temporarily set to mirror
            git remote set-url origin "https://gh-proxy.com/https://github.com/EchoDev7/vpn-master-panel-lite-.git"
            
            # Fetch using proxy
            if ! GIT_TERMINAL_PROMPT=0 git fetch origin; then
                echo -e "${RED}❌ Failed to fetch from proxy as well. Check server internet connection.${NC}"
                # Restore original remote
                git remote set-url origin "$CURRENT_REMOTE"
                echo -e "${YELLOW}⚠️ Skipping remote update. Attempting to continue with local changes only...${NC}"
            else
                echo -e "${GREEN}✓ Successfully connected via proxy.${NC}"
            fi
            
            # Restore original remote so next time it defaults cleanly
            git remote set-url origin "$CURRENT_REMOTE"
        else
            echo -e "${RED}❌ Fetch failed even with proxy. Skipping remote update.${NC}"
        fi
    fi

    # Stash local tracked + untracked changes instead of hard reset
    STASH_RESULT=""
    if [ -n "$(git status --porcelain)" ]; then
        STASH_RESULT="changed"
        echo -e "${YELLOW}⚠️ Local changes detected (tracked/untracked). Stashing them...${NC}"
        git stash push -u -m "update.sh auto-stash $(date +%s)"
    fi
    
    # Attempt to pull. If standard fetch worked, pull origin main works.
    # If standard fetch failed but proxy fetched, `git pull origin main` might fail again if it tries to connect.
    # We should specify standard merge if fetch already pulled the objects.
    # git merge origin/main handles it without network calls if fetch succeeded.
    if ! git merge origin/main --no-edit; then
        echo -e "${YELLOW}⚠️ Merge failed, trying git pull origin main...${NC}"
        if ! git pull origin main; then
            echo -e "${RED}❌ Could not update repository from origin/main.${NC}"
            echo -e "${RED}❌ Your server is likely still running old code. Resolve git conflicts and re-run update.sh.${NC}"
        fi
    fi
    
    # Restore local changes if we stashed them
    if [ "$STASH_RESULT" = "changed" ]; then
        echo -e "${YELLOW}♻️  Restoring local changes...${NC}"
        if ! git stash pop; then
            echo -e "${RED}❌ Merge conflict during stash pop! Please resolve manually in $INSTALL_DIR${NC}"
        fi
    fi
else
    echo -e "${YELLOW}⚠️ Not a git repository. Skipping git update.${NC}"
    echo -e "${YELLOW}To update manually, backup your config and reinstall.${NC}"
fi

# 2. Update System Packages
echo -e "${CYAN}📦 Updating System Packages...${NC}"
export DEBIAN_FRONTEND=noninteractive
apt update -qq
# Ensure critical packages are present
# sqlite3 is needed by post_update_fixes() to read settings from DB
# NOTE: Do NOT force-install Ubuntu's `npm` package when NodeSource `nodejs` is present.
# It can cause dependency conflicts (nodejs Conflicts: npm). NodeSource nodejs ships with npm.
apt install -y openvpn wireguard wireguard-tools iptables iptables-persistent nodejs python3-pip openssl fail2ban certbot python3-certbot-nginx sqlite3
echo -e "${GREEN}✓ certbot: $(certbot --version 2>&1 | head -1)${NC}"
record_summary "System packages" "ok" "dependencies install completed"

# Configure Fail2Ban if missing
if [ ! -f "/etc/fail2ban/jail.local" ]; then
    echo -e "${CYAN}🛡️  Configuring Fail2Ban...${NC}"
    cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
EOF

    # F9: OpenVPN Brute-Force Detection
    # Create Filter
    cat > /etc/fail2ban/filter.d/openvpn-auth.conf << EOF
[Definition]
failregex = AUTH_FAILED.*from <HOST>
ignoreregex =
EOF

    # Create Jail
    cat > /etc/fail2ban/jail.d/openvpn.conf << EOF
[openvpn-auth]
enabled = true
port = 1194
protocol = udp
filter = openvpn-auth
logpath = /var/log/openvpn/auth.log
maxretry = 3
bantime = 3600
action = iptables-multiport[name=OpenVPN, port=1194, protocol=udp]
EOF

    systemctl restart fail2ban
    systemctl enable fail2ban
fi

# 3. Enable IP Forwarding and Tuning (Enterprise)
echo -e "${CYAN}📈 Optimizing Network Stack...${NC}"
cat > /etc/sysctl.d/99-vpn-master.conf << EOF
# IP Forwarding
net.ipv4.ip_forward=1
net.ipv6.conf.all.forwarding=1

# Network throughput optimizations
net.core.default_qdisc=fq
net.ipv4.tcp_congestion_control=bbr
net.ipv4.tcp_fastopen=3

# Increase ephemeral ports
net.ipv4.ip_local_port_range=1024 65535

# Increase connection tracking table size
net.netfilter.nf_conntrack_max=1048576
EOF
sysctl --system > /dev/null 2>&1

# 3.1 Configure Firewall NAT (UFW Masquerading) - Enterprise Idempotent Method
echo -e "${CYAN}🔥 Configuring UFW NAT...${NC}"

# Set default forward policy to ACCEPT
sed -i 's/DEFAULT_FORWARD_POLICY="DROP"/DEFAULT_FORWARD_POLICY="ACCEPT"/g' /etc/default/ufw

# SELF HEALING: Restore UFW rules if prior script deleted the *filter block
if ! grep -q "^\*filter" /etc/ufw/before.rules; then
    echo -e "${YELLOW}⚠️ Corrupted UFW before.rules detected (missing filter block). Restoring to defaults...${NC}"
    if [ -f "/usr/share/ufw/before.rules" ]; then
        cp /usr/share/ufw/before.rules /etc/ufw/before.rules
    fi
fi

# Detect Main Interface (e.g., eth0, ens3)
MAIN_IFACE=$(ip -4 route ls | grep default | grep -Po '(?<=dev )(\S+)' | head -1)

if [ -n "$MAIN_IFACE" ]; then
    # Ensure *nat block exists safely without deleting existing rules
    if ! grep -q "^\*nat" /etc/ufw/before.rules; then
        echo -e "\n# NAT table rules\n*nat\n:POSTROUTING ACCEPT [0:0]\nCOMMIT\n" >> /etc/ufw/before.rules
    fi
    
    # Add MASQUERADE rules idempotently
    if ! grep -q "-A POSTROUTING -s 10.8.0.0/8 -o \$MAIN_IFACE -j MASQUERADE" /etc/ufw/before.rules; then
        sed -i "/^\*nat/a -A POSTROUTING -s 10.8.0.0/8 -o \$MAIN_IFACE -j MASQUERADE" /etc/ufw/before.rules
    fi
    if ! grep -q "-A POSTROUTING -s 10.9.0.0/8 -o \$MAIN_IFACE -j MASQUERADE" /etc/ufw/before.rules; then
        sed -i "/^\*nat/a -A POSTROUTING -s 10.9.0.0/8 -o \$MAIN_IFACE -j MASQUERADE" /etc/ufw/before.rules
    fi
    
    # Ensure UFW routes traffic seamlessly
    if ! grep -q "-A ufw-before-forward -s 10.8.0.0/8 -j ACCEPT" /etc/ufw/before.rules; then
        sed -i '/\*filter/a -A ufw-before-forward -s 10.8.0.0/8 -j ACCEPT\n-A ufw-before-forward -s 10.9.0.0/8 -j ACCEPT' /etc/ufw/before.rules
    fi
    echo -e "${GREEN}✓ UFW NAT rules added/updated${NC}"
else
    echo -e "${YELLOW}⚠️ Could not detect main network interface for NAT mapping.${NC}"
fi

# Ensure Tun Device Exists (Common VPS Issue)
# 3.5 CLEANUP: Remove Encrypted/Corrupt OpenVPN Keys (Force Regeneration)
KEY_FILE="/opt/vpn-master-panel/backend/data/openvpn/server.key"
if [ -f "$KEY_FILE" ]; then
    # Check for ENCRYPTED header or missing BEGIN PRIVATE KEY
    if grep -q "ENCRYPTED" "$KEY_FILE" || grep -q "Proc-Type: 4,ENCRYPTED" "$KEY_FILE" || ! grep -q "BEGIN PRIVATE KEY" "$KEY_FILE"; then
        echo -e "${YELLOW}⚠️ Detected Encrypted/Corrupt Server Key. Deleting to force regeneration...${NC}"
        rm -f "$KEY_FILE"
        rm -f "/opt/vpn-master-panel/backend/data/openvpn/server.crt"
        # Also clean /etc/openvpn to be sure
        rm -f "/etc/openvpn/server.key"
        rm -f "/etc/openvpn/server.crt"
    fi
fi

# 3.5 CLEANUP & REPAIR: Fix OpenVPN Keys (Deterministic)
KEY_FILE="/opt/vpn-master-panel/backend/data/openvpn/server.key"
SHOULD_FIX_PKI=false

if [ ! -f "$KEY_FILE" ]; then
    SHOULD_FIX_PKI=true
elif grep -q "ENCRYPTED" "$KEY_FILE" || grep -q "Proc-Type: 4,ENCRYPTED" "$KEY_FILE"; then
    echo -e "${YELLOW}⚠️ Detected Encrypted Server Key.${NC}"
    SHOULD_FIX_PKI=true
elif systemctl is-failed --quiet openvpn@server; then
     echo -e "${YELLOW}⚠️ OpenVPN Service is in FAILED state.${NC}"
     SHOULD_FIX_PKI=true
else
    # Check Modulus Match
    KEY_MOD=$(openssl rsa -noout -modulus -in "$KEY_FILE" 2>/dev/null | openssl md5)
    CERT_FILE="/opt/vpn-master-panel/backend/data/openvpn/server.crt"
    if [ -f "$CERT_FILE" ]; then
        CERT_MOD=$(openssl x509 -noout -modulus -in "$CERT_FILE" 2>/dev/null | openssl md5)
        if [ "$KEY_MOD" != "$CERT_MOD" ]; then
             echo -e "${YELLOW}⚠️ Key/Cert Mismatch Detected.${NC}"
             SHOULD_FIX_PKI=true
        fi
    fi
fi

if [ "$SHOULD_FIX_PKI" = true ]; then
    echo -e "${CYAN}🔧 Repairing OpenVPN PKI using OpenSSL (Robust Method)...${NC}"
    
    DATA_DIR="/opt/vpn-master-panel/backend/data/openvpn"
    mkdir -p "$DATA_DIR"
    
    # Stop Service
    systemctl stop openvpn@server
    systemctl stop openvpn

    # Clean Old Keys
    rm -f $DATA_DIR/ca.crt $DATA_DIR/ca.key
    rm -f $DATA_DIR/server.crt $DATA_DIR/server.key $DATA_DIR/server.csr
    rm -f $DATA_DIR/ta.key $DATA_DIR/dh.pem $DATA_DIR/server.ext

    # Generate CA
    echo -e "${CYAN}  Generating CA...${NC}"
    openssl req -new -x509 -days 3650 -nodes \
        -out $DATA_DIR/ca.crt \
        -keyout $DATA_DIR/ca.key \
        -subj "/CN=VPN-Master-CA" 2>/dev/null

    # Generate Server Key & CSR
    echo -e "${CYAN}  Generating Server Cert/Key...${NC}"
    openssl req -new -nodes \
        -out $DATA_DIR/server.csr \
        -keyout $DATA_DIR/server.key \
        -subj "/CN=server" 2>/dev/null

    # Create Extensions File (Critical for modern clients)
    echo "basicConstraints=CA:FALSE" > $DATA_DIR/server.ext
    echo "nsCertType=server" >> $DATA_DIR/server.ext
    echo "keyUsage=digitalSignature,keyEncipherment" >> $DATA_DIR/server.ext
    echo "extendedKeyUsage=serverAuth" >> $DATA_DIR/server.ext
    echo "subjectKeyIdentifier=hash" >> $DATA_DIR/server.ext
    echo "authorityKeyIdentifier=keyid,issuer" >> $DATA_DIR/server.ext

    # Sign Server Cert
    openssl x509 -req \
        -in $DATA_DIR/server.csr \
        -CA $DATA_DIR/ca.crt \
        -CAkey $DATA_DIR/ca.key \
        -CAcreateserial \
        -out $DATA_DIR/server.crt \
        -days 3650 \
        -extfile $DATA_DIR/server.ext 2>/dev/null

    # DH & TA
    echo -e "${CYAN}  Generating DH & TA...${NC}"
    openssl dhparam -out $DATA_DIR/dh.pem 2048 2>/dev/null
    openvpn --genkey tls-auth $DATA_DIR/ta.key

    # Permissions
    chmod 600 $DATA_DIR/server.key $DATA_DIR/ta.key $DATA_DIR/ca.key
    chmod 644 $DATA_DIR/ca.crt $DATA_DIR/server.crt $DATA_DIR/dh.pem

    # Verify Mismatch Immediately
    KEY_MOD=$(openssl rsa -noout -modulus -in "$DATA_DIR/server.key" 2>/dev/null | openssl md5)
    CERT_MOD=$(openssl x509 -noout -modulus -in "$DATA_DIR/server.crt" 2>/dev/null | openssl md5)
    
    if [ "$KEY_MOD" != "$CERT_MOD" ]; then
        echo -e "${RED}❌ Critical Error: Generated Key/Cert mismatch!${NC}"
        # Should not happen with fresh generation, but warn
    else
        echo -e "${GREEN}✓ PKI Repaired Successfully (OpenSSL match verified)${NC}"
    fi

    # Cleanup CSR
    rm -f $DATA_DIR/server.csr $DATA_DIR/server.ext

    # Copy keys to /etc/openvpn (for the service)
    # Ensure destination exists
    mkdir -p /etc/openvpn
    cp -f $DATA_DIR/ca.crt /etc/openvpn/
    cp -f $DATA_DIR/server.crt /etc/openvpn/
    cp -f $DATA_DIR/server.key /etc/openvpn/
    cp -f $DATA_DIR/ta.key /etc/openvpn/
    cp -f $DATA_DIR/dh.pem /etc/openvpn/
    
    chmod 600 /etc/openvpn/server.key /etc/openvpn/ta.key
    
    cd "$INSTALL_DIR" || exit 1
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

# 4.5 Run Database Migrations (Safe Python Script)
echo -e "${CYAN}🗄️  Running Database Migrations...${NC}"
if [ -f "migrate_db.py" ]; then
    python3 migrate_db.py
else
    echo -e "${YELLOW}⚠️ Migration script not found. Skipping.${NC}"
fi

cd ..

# 5. Rebuild Frontend (Critical for UI updates)
echo -e "${CYAN}⚛️  Rebuilding Frontend...${NC}"
cd frontend
# Install ALL dependencies (including devDependencies like vite)
npm install
npm run build

# Verify Build Success
if [ ! -f "dist/index.html" ]; then
    echo -e "${RED}❌ Frontend Build Failed! 'dist/index.html' not found.${NC}"
    echo -e "${YELLOW}Check npm logs above.${NC}"
    record_summary "Frontend build" "error" "dist/index.html not found"
    exit 1
fi
record_summary "Frontend build" "ok" "dist assets generated"

# Fix Permissions (Critical for Nginx)
chmod -R 755 dist
cd ..

# 6. Repair & Restart Services
echo -e "${CYAN}🔧 Verifying Services...${NC}"

# Backend Service Repair (Fix PATH issue)
SERVICE_FILE="/etc/systemd/system/vpnmaster-backend.service"
# We force update the service file to fix the PATH
echo -e "${YELLOW}⚠️ Updating Backend Service Definition...${NC}"
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=VPN Master Panel Backend (Lightweight)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/vpn-master-panel/backend
Environment="PATH=/opt/vpn-master-panel/backend/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/opt/vpn-master-panel/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001 --workers 1 --limit-concurrency 50
Restart=always
RestartSec=10

# Memory limits (Lite Edition)
MemoryMax=300M
MemoryHigh=250M

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable vpnmaster-backend


# Nginx Repair Function
repair_nginx() {
    echo -e "${YELLOW}⚠️ Detected Nginx issue. Reconfiguring...${NC}"

    cat > /etc/nginx/sites-available/vpnmaster << 'NGINXEOF'
# ─────────────────────────────────────────────────────────────
# VPN Master Panel — Nginx Configuration (update.sh)
# Backend FastAPI on 127.0.0.1:8001 (internal)
# Port 8000 = public API gateway  |  Port 3000 = React frontend
# ─────────────────────────────────────────────────────────────

# ── Port 80: ACME challenge passthrough (Let's Encrypt) ──────
server {
    listen 0.0.0.0:80;
    server_name _;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
        try_files $uri =404;
    }

    location / {
        return 200 "VPN Master Panel";
        add_header Content-Type text/plain;
    }
}

# ── Port 8000: Backend API gateway ───────────────────────────
server {
    listen 0.0.0.0:8000;
    server_name _;

    location /api/ {
        proxy_pass         http://127.0.0.1:8001/api/;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;

        # Critical for SSL streaming — certbot can take 30-180 seconds
        proxy_read_timeout  600s;
        proxy_send_timeout  600s;
        proxy_connect_timeout 30s;

        # Disable buffering for SSE / streaming (certbot live output)
        proxy_buffering    off;
        proxy_cache        off;
        proxy_cache_bypass 1;
        chunked_transfer_encoding on;
        add_header X-Accel-Buffering no always;
    }

    location /ws/ {
        proxy_pass         http://127.0.0.1:8001/ws/;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade    $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_set_header   Host       $host;
        proxy_read_timeout 3600s;
        proxy_buffering    off;
    }

    location / {
        proxy_pass         http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header   Host       $host;
        proxy_read_timeout 600s;
        proxy_buffering    off;
    }
}

# ── Port 3000: React frontend (static files) ─────────────────
server {
    listen 0.0.0.0:3000;
    server_name _;

    root  /opt/vpn-master-panel/frontend/dist;
    index index.html;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript
               text/xml application/xml text/javascript image/svg+xml;
    gzip_min_length 1000;

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
        expires     30d;
        add_header  Cache-Control "public, immutable";
        try_files   $uri =404;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass         http://127.0.0.1:8001/api/;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_read_timeout  600s;
        proxy_buffering     off;
        proxy_cache         off;
        chunked_transfer_encoding on;
        add_header X-Accel-Buffering no always;
    }

    location /ws/ {
        proxy_pass         http://127.0.0.1:8001/ws/;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade    $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_set_header   Host       $host;
        proxy_read_timeout 3600s;
        proxy_buffering    off;
    }
}
NGINXEOF

    rm -f /etc/nginx/sites-enabled/default
    ln -sf /etc/nginx/sites-available/vpnmaster /etc/nginx/sites-enabled/
    nginx -t && systemctl restart nginx
    echo -e "${GREEN}✓ Nginx repaired${NC}"
}

# Check Firewall (SECURED: Only necessary ports)
echo -e "${CYAN}🔥 Configuring Firewall...${NC}"
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp > /dev/null 2>&1
ufw allow 80/tcp > /dev/null 2>&1
ufw allow 443/tcp > /dev/null 2>&1
ufw allow 3000/tcp > /dev/null 2>&1
ufw allow 8000/tcp > /dev/null 2>&1
ufw allow 8443/tcp > /dev/null 2>&1  # Panel HTTPS (OpenVPN uses 443)
# VPN Ports (customizable via panel later, but defaults here)
ufw allow 1194/udp > /dev/null 2>&1
ufw allow 51820/udp > /dev/null 2>&1

ufw --force enable > /dev/null 2>&1

# Ensure TUN Device Exists (Common VPS Issue)
if [ ! -c /dev/net/tun ]; then
    echo -e "${YELLOW}⚠️ Creating /dev/net/tun...${NC}"
    mkdir -p /dev/net
    mknod /dev/net/tun c 10 200
    chmod 600 /dev/net/tun
fi

# Deploy Auth Script to standard location (Fixes permissions issues)
# User Request: strictly copy to /etc/openvpn/scripts/auth.py and chmod 755
mkdir -p /etc/openvpn/scripts
cp /opt/vpn-master-panel/backend/auth.py /etc/openvpn/scripts/auth.py
cp /opt/vpn-master-panel/backend/scripts/auth.sh /etc/openvpn/scripts/
cp /opt/vpn-master-panel/backend/scripts/client-connect.sh /etc/openvpn/scripts/
cp /opt/vpn-master-panel/backend/scripts/client-disconnect.sh /etc/openvpn/scripts/
cp /opt/vpn-master-panel/backend/scripts/get_speed_limit.py /etc/openvpn/scripts/

chmod 755 /etc/openvpn/scripts/auth.py
chmod 755 /etc/openvpn/scripts/auth.sh
chmod 755 /etc/openvpn/scripts/client-connect.sh
chmod 755 /etc/openvpn/scripts/client-disconnect.sh
chmod 755 /etc/openvpn/scripts/get_speed_limit.py
chown root:root /etc/openvpn/scripts/*

# Fix AppArmor (Allow OpenVPN to read keys in /opt and EXECUTE auth script)
if [ -f "/etc/apparmor.d/usr.sbin.openvpn" ]; then
    echo -e "${CYAN}🛡️  Updating AppArmor Profile...${NC}"
    if ! grep -q "/etc/openvpn/scripts/\*\*" /etc/apparmor.d/usr.sbin.openvpn; then
        sed -i '/}/d' /etc/apparmor.d/usr.sbin.openvpn
        echo "  /opt/vpn-master-panel/backend/data/** r," >> /etc/apparmor.d/usr.sbin.openvpn
        echo "  /etc/openvpn/scripts/** rUx," >> /etc/apparmor.d/usr.sbin.openvpn
        echo "  /opt/vpn-master-panel/backend/** r," >> /etc/apparmor.d/usr.sbin.openvpn
        echo "}" >> /etc/apparmor.d/usr.sbin.openvpn
        
        systemctl reload apparmor
        echo -e "${GREEN}✓ AppArmor Updated (Auth Scripts Unconfined)${NC}"
    else
         echo -e "${GREEN}✓ AppArmor already configured${NC}"
    fi
fi

# Ensure Port 443 is FREE for OpenVPN (If configured)
# Only do this if 443 is actually intended for VPN, otherwise warn.
# For now, we assume user wants 443 for VPN/SSL.

# Always ensure log files exist and have correct permissions
# We do this unconditionally to fix any permission issues
mkdir -p /var/log/openvpn
touch /var/log/openvpn/openvpn.log
touch /var/log/openvpn/openvpn-status.log
touch /var/log/openvpn/auth.log
touch /var/log/openvpn/auth_wrapper.log

# Set directory permissions
chmod 755 /var/log/openvpn

# Allow OpenVPN (nobody/nogroup) to write to auth logs
# This is CRITICAL for auth.sh and auth.py to work
chmod 666 /var/log/openvpn/auth.log
chmod 666 /var/log/openvpn/auth_wrapper.log

echo -e "${CYAN}🔄 Restarting Services...${NC}"
systemctl daemon-reload

# Fix permissions so OpenVPN can execute auth script
chmod +x /opt/vpn-master-panel/backend/auth.py

# Force Regenerate Server Config - DISABLED to preserve manual changes
# echo -e "${CYAN}♻️  Regenerating OpenVPN Config...${NC}"
# cd /opt/vpn-master-panel/backend
# source venv/bin/activate
# # Ensure PYTHONPATH includes current directory
# export PYTHONPATH=$PYTHONPATH:/opt/vpn-master-panel/backend
# # python3 force_server_config.py # Skip this to avoid overwriting server.conf

# Force fix potential path issues (Double Safety) - Inline Patch
SERVER_CONF="/etc/openvpn/server.conf"
if [ -f "$SERVER_CONF" ]; then
    echo -e "${CYAN}🔧 Patching server.conf paths...${NC}"
    # Replace auth.py with auth.sh (Wrapper)
    # First revert any direct auth.py ref to be sure we match
    sed -i 's|/opt/vpn-master-panel/backend/auth.py|/etc/openvpn/scripts/auth.sh|g' "$SERVER_CONF"
    sed -i 's|/etc/openvpn/scripts/auth.py|/etc/openvpn/scripts/auth.sh|g' "$SERVER_CONF"
    
    # Force ensure the line exists if it was missing or commented out
    if ! grep -q "auth-user-pass-verify /etc/openvpn/scripts/auth.sh via-file" "$SERVER_CONF"; then
        echo "auth-user-pass-verify /etc/openvpn/scripts/auth.sh via-file" >> "$SERVER_CONF"
        echo -e "${GREEN}✓ Added auth script directive to server.conf${NC}"
    fi
    # Ensure script-security is at least 2
    if ! grep -q "script-security 2" "$SERVER_CONF"; then
         echo "script-security 2" >> "$SERVER_CONF"
    fi
    # Ensure Verify Client Cert is handled if missing (optional safety)
fi
cd ..

# Fix permissions so OpenVPN can read keys
if [ -d "/opt/vpn-master-panel/backend/data" ]; then
    chmod -R 755 /opt/vpn-master-panel/backend/data
fi

BACKEND_SERVICE=""
if systemctl list-unit-files | grep -q '^vpn-panel-backend.service'; then
    BACKEND_SERVICE="vpn-panel-backend"
elif systemctl list-unit-files | grep -q '^vpnmaster-backend.service'; then
    BACKEND_SERVICE="vpnmaster-backend"
fi

if [ -n "$BACKEND_SERVICE" ]; then
    restart_unit_if_exists "${BACKEND_SERVICE}.service" "Backend"
else
    print_warning "No backend service unit found (vpn-panel-backend/vpnmaster-backend). Attempting to install service..."
    if [ -x "/opt/vpn-master-panel/backend/install_service.sh" ]; then
        /opt/vpn-master-panel/backend/install_service.sh || true
        restart_unit_if_exists "vpn-panel-backend.service" "Backend" || true
    fi
fi
# Restart OpenVPN to apply changes
restart_unit_if_exists "openvpn@server.service" "OpenVPN" || restart_unit_if_exists "openvpn.service" "OpenVPN" || true

# Check Nginx Config
reload_or_restart_nginx

# ════════════════════════════════════════════════════════════
#  POST-UPDATE: Auto-apply all settings that previously
#  required manual server commands.
#  Runs every time so the server stays consistent with the
#  panel settings even if something drifted.
# ════════════════════════════════════════════════════════════
post_update_fixes() {
    echo -e "${CYAN}🔧 Running post-update fixes...${NC}"

    DB_FILE="$INSTALL_DIR/backend/vpnmaster_lite.db"

    # ── Helper: read a value from the settings table ──────────────────────────
    read_setting() {
        local key="$1"
        local default="$2"
        if [ -f "$DB_FILE" ]; then
            val=$(sqlite3 "$DB_FILE" \
                "SELECT value FROM settings WHERE key='${key}' LIMIT 1;" 2>/dev/null)
            echo "${val:-$default}"
        else
            echo "$default"
        fi
    }

    # ── 1. Read current settings from DB ─────────────────────────────────────
    PANEL_DOMAIN=$(read_setting "panel_domain" "")
    SUB_DOMAIN=$(read_setting "subscription_domain" "")
    PANEL_PORT=$(read_setting "panel_https_port" "8443")
    SUB_PORT=$(read_setting "sub_https_port" "2053")
    EFFECTIVE_SUB_PORT="$SUB_PORT"

    # Managed SSL edge-port policy
    ALLOWED_SSL_PORTS="2053 2083 2087 2096 8443"
    is_allowed_ssl_port() {
        local p="$1"
        for allowed in $ALLOWED_SSL_PORTS; do
            [ "$p" = "$allowed" ] && return 0
        done
        return 1
    }

    if ! is_allowed_ssl_port "$PANEL_PORT"; then
        echo -e "${YELLOW}⚠ panel_https_port=${PANEL_PORT} is outside policy. Resetting to 8443.${NC}"
        PANEL_PORT="8443"
        [ -f "$DB_FILE" ] && sqlite3 "$DB_FILE" "UPDATE settings SET value='8443' WHERE key='panel_https_port';" 2>/dev/null || true
    fi

    if ! is_allowed_ssl_port "$EFFECTIVE_SUB_PORT"; then
        echo -e "${YELLOW}⚠ sub_https_port=${EFFECTIVE_SUB_PORT} is outside policy. Resetting to 2053.${NC}"
        EFFECTIVE_SUB_PORT="2053"
        [ -f "$DB_FILE" ] && sqlite3 "$DB_FILE" "UPDATE settings SET value='2053' WHERE key='sub_https_port';" 2>/dev/null || true
    fi

    if [ "$PANEL_PORT" = "$EFFECTIVE_SUB_PORT" ]; then
        for candidate in 2053 2083 2087 2096 8443; do
            if [ "$candidate" != "$PANEL_PORT" ]; then
                EFFECTIVE_SUB_PORT="$candidate"
                break
            fi
        done
        echo -e "${YELLOW}⚠ Panel/Sub HTTPS ports were identical. Reassigned sub_https_port to ${EFFECTIVE_SUB_PORT}.${NC}"
        [ -f "$DB_FILE" ] && sqlite3 "$DB_FILE" "UPDATE settings SET value='${EFFECTIVE_SUB_PORT}' WHERE key='sub_https_port';" 2>/dev/null || true
    fi

    echo -e "${CYAN}   Panel domain:  ${PANEL_DOMAIN:-'(not set)'}  port ${PANEL_PORT}${NC}"
    echo -e "${CYAN}   Sub domain:    ${SUB_DOMAIN:-'(not set)'}  port ${EFFECTIVE_SUB_PORT}${NC}"

    # ── 2. Ensure firewall ports are open ─────────────────────────────────────
    echo -e "${CYAN}   Opening firewall ports...${NC}"
    ufw allow 8443/tcp > /dev/null 2>&1
    ufw allow 2053/tcp > /dev/null 2>&1
    ufw allow 2083/tcp > /dev/null 2>&1
    ufw allow 2087/tcp > /dev/null 2>&1
    ufw allow 2096/tcp > /dev/null 2>&1
    ufw allow 80/tcp   > /dev/null 2>&1
    # Open whatever port the admin has chosen
    [ -n "$PANEL_PORT" ] && ufw allow ${PANEL_PORT}/tcp > /dev/null 2>&1
    [ -n "$EFFECTIVE_SUB_PORT" ] && ufw allow ${EFFECTIVE_SUB_PORT}/tcp > /dev/null 2>&1
    print_success "Firewall ports verified"

    # ── 3. Re-build Nginx SSL configs for domains that have certs ────────────
    # This is the critical step that was previously manual.
    # Uses restore_ssl_nginx.sh which auto-detects port conflicts.
    RESTORE_SCRIPT="$INSTALL_DIR/restore_ssl_nginx.sh"
    if [ -f "$RESTORE_SCRIPT" ]; then
        # Panel domain
        if [ -n "$PANEL_DOMAIN" ]; then
            CERT_PATH="/etc/letsencrypt/live/${PANEL_DOMAIN}/fullchain.pem"
            if [ -f "$CERT_PATH" ]; then
                echo -e "${CYAN}   Rebuilding Nginx SSL config for panel: ${PANEL_DOMAIN} (port ${PANEL_PORT})${NC}"
                bash "$RESTORE_SCRIPT" "$PANEL_DOMAIN" "$PANEL_PORT" > /dev/null 2>&1 \
                    && print_success "Panel SSL config updated (${PANEL_DOMAIN}:${PANEL_PORT})" \
                    || echo -e "${YELLOW}⚠ Could not rebuild panel SSL config${NC}"
            else
                echo -e "${YELLOW}   Panel domain set but no cert yet — SSL not configured (use panel to issue cert)${NC}"
            fi
        fi

        # Subscription domain (only if different from panel)
        if [ -n "$SUB_DOMAIN" ] && [ "$SUB_DOMAIN" != "$PANEL_DOMAIN" ]; then
            CERT_PATH="/etc/letsencrypt/live/${SUB_DOMAIN}/fullchain.pem"
            if [ -f "$CERT_PATH" ]; then
                echo -e "${CYAN}   Rebuilding Nginx SSL config for sub: ${SUB_DOMAIN} (port ${EFFECTIVE_SUB_PORT})${NC}"
                bash "$RESTORE_SCRIPT" "$SUB_DOMAIN" "$EFFECTIVE_SUB_PORT" > /dev/null 2>&1 \
                    && print_success "Sub SSL config updated (${SUB_DOMAIN}:${EFFECTIVE_SUB_PORT})" \
                    || echo -e "${YELLOW}⚠ Could not rebuild sub SSL config${NC}"
            else
                echo -e "${YELLOW}   Sub domain set but no cert yet — use panel to issue cert${NC}"
            fi
        fi
    else
        echo -e "${YELLOW}⚠ restore_ssl_nginx.sh not found — skipping SSL config rebuild${NC}"
    fi

    # ── 4. Ensure certbot auto-renewal timer is active ────────────────────────
    if command -v certbot > /dev/null 2>&1; then
        # Enable systemd timer (preferred over cron)
        systemctl enable certbot.timer > /dev/null 2>&1
        systemctl start  certbot.timer > /dev/null 2>&1
        # Fallback: add cron if timer not available
        if ! systemctl is-active --quiet certbot.timer 2>/dev/null; then
            if ! crontab -l 2>/dev/null | grep -q 'certbot renew'; then
                (crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet --post-hook 'systemctl reload nginx'") | crontab -
                echo -e "${CYAN}   Added certbot renewal cron (daily 3am)${NC}"
            fi
        else
            print_success "Certbot auto-renewal timer active"
        fi
    fi

    # ── 5. Reload Nginx after all config changes ──────────────────────────────
    if nginx -t > /dev/null 2>&1; then
        systemctl reload nginx
        print_success "Nginx reloaded with latest configs"
    else
        echo -e "${RED}✗ Nginx config test failed after post-update fixes${NC}"
        nginx -t
    fi

    # ── 6. Print current access URLs ─────────────────────────────────────────
    SERVER_IP=$(hostname -I | awk '{print $1}')
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  Access URLs${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  HTTP  (no SSL):  ${GREEN}http://${SERVER_IP}:3000${NC}"
    if [ -n "$PANEL_DOMAIN" ] && [ -f "/etc/letsencrypt/live/${PANEL_DOMAIN}/fullchain.pem" ]; then
        if [ "$PANEL_PORT" = "443" ]; then
            echo -e "  Panel (HTTPS):   ${GREEN}https://${PANEL_DOMAIN}${NC}"
        else
            echo -e "  Panel (HTTPS):   ${GREEN}https://${PANEL_DOMAIN}:${PANEL_PORT}${NC}"
        fi
    fi
    if [ -n "$SUB_DOMAIN" ] && [ "$SUB_DOMAIN" != "$PANEL_DOMAIN" ] && \
       [ -f "/etc/letsencrypt/live/${SUB_DOMAIN}/fullchain.pem" ]; then
        if [ "$EFFECTIVE_SUB_PORT" = "443" ]; then
            echo -e "  Sub  (HTTPS):    ${GREEN}https://${SUB_DOMAIN}/sub/UUID${NC}"
        else
            echo -e "  Sub  (HTTPS):    ${GREEN}https://${SUB_DOMAIN}:${EFFECTIVE_SUB_PORT}/sub/UUID${NC}"
        fi
    fi
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # ── 7. Health checks (deployment verification) ───────────────────────────
    echo -e "${CYAN}🔎 Running health checks...${NC}"

    if [ -n "$BACKEND_SERVICE" ] && systemctl is-active --quiet "$BACKEND_SERVICE"; then
        print_success "Backend service active (${BACKEND_SERVICE})"
        record_summary "Backend health" "ok" "service active (${BACKEND_SERVICE})"
    else
        print_warning "Backend service is not active or unknown"
        record_summary "Backend health" "warn" "service not active or unknown"
    fi

    if systemctl is-active --quiet nginx; then
        print_success "Nginx service active"
        record_summary "Nginx health" "ok" "service active"
    else
        print_warning "Nginx service is not active"
        record_summary "Nginx health" "warn" "service not active"
    fi

    HEALTH_HTTP_CODE=$(curl -sS -o /dev/null -w "%{http_code}" "http://127.0.0.1:8001/health" 2>/dev/null || echo "000")
    if [ "$HEALTH_HTTP_CODE" = "200" ]; then
        print_success "Backend /health reachable on 127.0.0.1:8001"
        record_summary "Backend /health" "ok" "HTTP ${HEALTH_HTTP_CODE}"
    else
        print_warning "Backend /health check failed on 127.0.0.1:8001 (HTTP ${HEALTH_HTTP_CODE})"
        record_summary "Backend /health" "warn" "HTTP ${HEALTH_HTTP_CODE}"
    fi

    if [ -n "$SUB_DOMAIN" ]; then
        if [ "$EFFECTIVE_SUB_PORT" = "443" ]; then
            SUB_URL="https://${SUB_DOMAIN}/sub/INVALID_TOKEN"
        else
            SUB_URL="https://${SUB_DOMAIN}:${EFFECTIVE_SUB_PORT}/sub/INVALID_TOKEN"
        fi

        SUB_HTTP_CODE=$(curl -sk -o /dev/null -w "%{http_code}" "$SUB_URL" 2>/dev/null || echo "000")
        if [ "$SUB_HTTP_CODE" = "200" ] || [ "$SUB_HTTP_CODE" = "403" ] || [ "$SUB_HTTP_CODE" = "404" ]; then
            print_success "Subscription endpoint reachable (${SUB_URL} -> HTTP ${SUB_HTTP_CODE})"
            record_summary "Subscription endpoint" "ok" "${SUB_URL} -> HTTP ${SUB_HTTP_CODE}"
        else
            print_warning "Subscription endpoint check failed (${SUB_URL} -> HTTP ${SUB_HTTP_CODE})"
            echo -e "${YELLOW}   Check DNS (A record), firewall port ${EFFECTIVE_SUB_PORT}, and Nginx SSL site for ${SUB_DOMAIN}.${NC}"
            record_summary "Subscription endpoint" "warn" "${SUB_URL} -> HTTP ${SUB_HTTP_CODE}"
        fi
    fi

    # ── 8. Always-run service operations (permanent update policy) ───────────
    # These commands run on every update so operator never needs manual restarts.
    echo -e "${CYAN}♻️  Running permanent post-update service operations...${NC}"
    systemctl daemon-reload > /dev/null 2>&1 || true
    systemctl reset-failed > /dev/null 2>&1 || true

    if [ -n "$BACKEND_SERVICE" ]; then
        restart_unit_if_exists "${BACKEND_SERVICE}.service" "Backend"
    else
        restart_unit_if_exists "vpnmaster-backend.service" "Backend" || restart_unit_if_exists "vpn-panel-backend.service" "Backend" || true
    fi

    restart_unit_if_exists "openvpn@server.service" "OpenVPN" || restart_unit_if_exists "openvpn.service" "OpenVPN" || true
    restart_unit_if_exists "wg-quick@wg0.service" "WireGuard" || true
    restart_unit_if_exists "fail2ban.service" "Fail2Ban" || true

    systemctl enable certbot.timer > /dev/null 2>&1 || true
    systemctl start certbot.timer > /dev/null 2>&1 || true

    reload_or_restart_nginx
}

post_update_fixes

print_update_summary

# Ensure check_status.sh is executable
if [ -f "check_status.sh" ]; then
    chmod +x check_status.sh
fi

echo -e "${GREEN}✅ Update Successfully Completed!${NC}"
if [ -d ".git" ]; then
    echo -e "${GREEN}   Version: $(git rev-parse --short HEAD)${NC}"
fi
