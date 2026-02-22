#!/bin/bash

# VPN Master Panel - Auto Update Script
# Usage: sudo ./update.sh

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check Root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}"
   exit 1
fi

INSTALL_DIR="/opt/vpn-master-panel"
CANONICAL_ORIGIN_URL="https://github.com/EchoDev7/vpn-master-panel-lite.git"

get_version() {
    # Prefer tag-based version if available, otherwise fallback to short SHA
    if [ -d ".git" ] && command -v git >/dev/null 2>&1; then
        git describe --tags --always --dirty 2>/dev/null || git rev-parse --short HEAD 2>/dev/null || echo "unknown"
    else
        echo "unknown"
    fi
}

echo -e "${CYAN}🚀 Starting VPN Master Panel Update...${NC}"

# 0. Verify Installation Directory
if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "${RED}Error: Installation not found at $INSTALL_DIR${NC}"
    echo -e "${RED}Please run install.sh first.${NC}"
    exit 1
fi

# 1. Update Source Code (Non-destructive)
echo -e "${CYAN}📥 Updating Installation at $INSTALL_DIR...${NC}"
cd "$INSTALL_DIR" || exit 1

echo -e "${CYAN}📌 Effective install dir: $INSTALL_DIR${NC}"
echo -e "${CYAN}📌 Current installed version (before update): $(get_version)${NC}"

# Check if it's a git repo
if [ -d ".git" ]; then
    # Fix old origin URL (GitHub redirects usually work, but make it clean)
    CURRENT_ORIGIN_URL=$(git remote get-url origin 2>/dev/null || true)
    if echo "$CURRENT_ORIGIN_URL" | grep -q "vpn-master-panel-lite-"; then
        git remote set-url origin "$CANONICAL_ORIGIN_URL" >/dev/null 2>&1 || true
    fi

    echo -e "${CYAN}Fetching updates...${NC}"
    git fetch --all --tags

    # Stash local changes (tracked + untracked) for safety.
    # IMPORTANT: we do NOT auto-pop the stash (it can create conflicts and break updates).
    # The stash is kept for manual recovery.
    if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
        echo -e "${YELLOW}⚠️ Local changes detected (tracked/untracked). Stashing them...${NC}"
        git stash push -u -m "vpnmaster-auto-stash $(date +%s)" >/dev/null 2>&1 || true
        echo -e "${YELLOW}ℹ️  Local changes were stashed and WILL NOT be restored automatically.${NC}"
        echo -e "${YELLOW}    If you need them later: git stash list && git stash show -p && git stash pop${NC}"
    fi
    
    git pull origin main

    # If a previous run left the repo in a conflicted state, clean it to avoid breaking the rest of update.
    if [ -n "$(git diff --name-only --diff-filter=U 2>/dev/null)" ]; then
        echo -e "${YELLOW}⚠️ Detected unresolved git conflicts. Resetting working tree to a clean state...${NC}"
        git reset --hard >/dev/null 2>&1 || true
        git clean -fd >/dev/null 2>&1 || true
    fi
else
    echo -e "${YELLOW}⚠️ Not a git repository. Skipping git update.${NC}"
    echo -e "${YELLOW}To update manually, backup your config and reinstall.${NC}"
fi

echo -e "${CYAN}📌 Installed version (after git update): $(get_version)${NC}"

# 2. Update System Packages
echo -e "${CYAN}📦 Updating System Packages...${NC}"
export DEBIAN_FRONTEND=noninteractive
apt update -qq
# Ensure critical packages are present - Added fail2ban
apt install -y openvpn iptables iptables-persistent ufw nodejs python3-pip openssl fail2ban netcat-openbsd sqlite3 git curl

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

# 3. Enable IP Forwarding (Ensure it persists)
if ! grep -q "net.ipv4.ip_forward=1" /etc/sysctl.conf; then
    echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
    sysctl -p
fi

# 3.1 Configure Firewall NAT (UFW Masquerading) - CRITICAL FOR INTERNET ACCESS
echo -e "${CYAN}🔥 Configuring UFW NAT...${NC}"

# Set default forward policy to ACCEPT
sed -i 's/DEFAULT_FORWARD_POLICY="DROP"/DEFAULT_FORWARD_POLICY="ACCEPT"/g' /etc/default/ufw
sed -i 's/DEFAULT_FORWARD_POLICY="REJECT"/DEFAULT_FORWARD_POLICY="ACCEPT"/g' /etc/default/ufw

# Detect Main Interface (e.g., eth0, ens3)
MAIN_IFACE=$(ip route | grep '^default' | awk '{print $5}' | head -n1)
if [ -z "$MAIN_IFACE" ]; then
    MAIN_IFACE=$(ip -o link show | awk -F': ' '{print $2}' | grep -v '^lo$' | head -n1)
fi

# Add NAT rules to before.rules if not present
if ! grep -Fq "*nat" /etc/ufw/before.rules; then
    echo -e "${YELLOW}⚠️ Adding NAT rules to /etc/ufw/before.rules for interface $MAIN_IFACE${NC}"
    
    # Append NAT table rules to the end of the file
    cat <<EOT >> /etc/ufw/before.rules

# NAT table rules
*nat
:POSTROUTING ACCEPT [0:0]
# Allow traffic from OpenVPN client to interface '$MAIN_IFACE'
-A POSTROUTING -s 10.8.0.0/8 -o $MAIN_IFACE -j MASQUERADE
COMMIT
EOT
    echo -e "${GREEN}✓ UFW NAT rules added${NC}"
else
    # NAT table exists, ensure our OpenVPN masquerade rule exists.
    NAT_RULE="-A POSTROUTING -s 10.8.0.0/8 -o $MAIN_IFACE -j MASQUERADE"
    if grep -Fq -- "$NAT_RULE" /etc/ufw/before.rules; then
        echo -e "${GREEN}✓ UFW NAT rules already present${NC}"
    else
        echo -e "${YELLOW}⚠️ NAT table exists but OpenVPN MASQUERADE rule missing. Patching...${NC}"
        tmpfile=$(mktemp)
        awk -v rule="$NAT_RULE" '
            BEGIN { in_nat=0; inserted=0 }
            /^\*nat$/ { in_nat=1 }
            in_nat && /^COMMIT$/ {
                if (!inserted) {
                    print rule
                    inserted=1
                }
                in_nat=0
            }
            { print }
        ' /etc/ufw/before.rules > "$tmpfile" && cat "$tmpfile" > /etc/ufw/before.rules
        rm -f "$tmpfile"
        echo -e "${GREEN}✓ UFW NAT rule patched${NC}"
    fi
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
elif systemctl is-failed --quiet openvpn@server 2>/dev/null; then
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
    
    # Stop Service (support multiple unit names)
    systemctl stop openvpn@server 2>/dev/null || true
    systemctl stop openvpn-server@server 2>/dev/null || true
    systemctl stop openvpn 2>/dev/null || true

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
python3 -m py_compile app/main.py # Syntax check

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
npm install --no-package-lock
npm run build

# Verify Build Success
if [ ! -f "dist/index.html" ]; then
    echo -e "${RED}❌ Frontend Build Failed! 'dist/index.html' not found.${NC}"
    echo -e "${YELLOW}Check npm logs above.${NC}"
    exit 1
fi

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

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable vpnmaster-backend


# Nginx Repair Function
repair_nginx() {
    echo -e "${YELLOW}⚠️ Detected Nginx issue. Reconfiguring...${NC}"
    
    # Create safe config
    cat > /etc/nginx/sites-available/vpnmaster << EOF
# Backend API
server {
    listen 0.0.0.0:8000;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }
}

# Frontend
server {
    listen 0.0.0.0:3000;
    server_name _;

    root /opt/vpn-master-panel/frontend/dist;
    index index.html;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript;

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location /api {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
    }
}
EOF
    rm -f /etc/nginx/sites-enabled/default
    ln -sf /etc/nginx/sites-available/vpnmaster /etc/nginx/sites-enabled/
    nginx -t && systemctl restart nginx
    echo -e "${GREEN}✓ Nginx repaired${NC}"
}

# Check Firewall (SECURED: Only necessary ports)
echo -e "${CYAN}🔥 Configuring Firewall...${NC}"

# Remove known legacy/insecure rules from older versions (best-effort)
ufw --force delete allow 51820/udp > /dev/null 2>&1 || true
ufw --force delete allow 1:65535/tcp > /dev/null 2>&1 || true
ufw --force delete allow 1:65535/udp > /dev/null 2>&1 || true

# Detect OpenVPN port/proto from server.conf (so panel-custom ports work automatically)
OVPN_PORT=$(awk '/^[[:space:]]*port[[:space:]]+[0-9]+/ {print $2; exit}' /etc/openvpn/server.conf 2>/dev/null || true)
OVPN_PROTO_RAW=$(awk '/^[[:space:]]*proto[[:space:]]+/ {print $2; exit}' /etc/openvpn/server.conf 2>/dev/null || true)
case "$OVPN_PROTO_RAW" in
    tcp|tcp-server|tcp4|tcp4-server|tcp6|tcp6-server) OVPN_PROTO="tcp" ;;
    udp|udp4|udp6) OVPN_PROTO="udp" ;;
    "") OVPN_PROTO="udp" ;;
    *) OVPN_PROTO="udp" ;;
esac
OVPN_PORT=${OVPN_PORT:-1194}

# If user moved OpenVPN away from 1194/udp, close the legacy default (best-effort).
if [ "$OVPN_PORT" != "1194" ] || [ "$OVPN_PROTO" != "udp" ]; then
    ufw --force delete allow 1194/udp > /dev/null 2>&1 || true
fi

ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp > /dev/null 2>&1
ufw allow 80/tcp > /dev/null 2>&1
ufw allow 443/tcp > /dev/null 2>&1
ufw allow 3000/tcp > /dev/null 2>&1
ufw allow 8000/tcp > /dev/null 2>&1
# VPN Port (read from OpenVPN config so panel-custom ports work)
ufw allow ${OVPN_PORT}/${OVPN_PROTO} > /dev/null 2>&1

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
    # Check if we already added our rules
    # We need to allow executing the wrapper AND the python script
    if ! grep -q "/etc/openvpn/scripts/auth.sh" /etc/apparmor.d/usr.sbin.openvpn; then
        # Append rule to allow read access & UNCONFINED execution (Ux) to avoid any restriction
        sed -i '/}/d' /etc/apparmor.d/usr.sbin.openvpn
        echo "  /opt/vpn-master-panel/backend/data/** r," >> /etc/apparmor.d/usr.sbin.openvpn
        echo "  /etc/openvpn/scripts/auth.py r," >> /etc/apparmor.d/usr.sbin.openvpn
        echo "  /etc/openvpn/scripts/auth.sh Ux," >> /etc/apparmor.d/usr.sbin.openvpn
        echo "  /opt/vpn-master-panel/backend/** r," >> /etc/apparmor.d/usr.sbin.openvpn
        echo "}" >> /etc/apparmor.d/usr.sbin.openvpn
        
        systemctl reload apparmor
        echo -e "${GREEN}✓ AppArmor Updated (Auth Script Unconfined)${NC}"
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
# Do not chmod files inside /opt repo (it dirties git status on servers).
# OpenVPN uses /etc/openvpn/scripts/auth.sh (wrapper) which is chmodded above.

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

systemctl restart vpnmaster-backend
# Restart OpenVPN to apply changes (support multiple unit names)
if systemctl list-units --full -all | grep -q "openvpn-server@server.service"; then
    systemctl restart openvpn-server@server
elif systemctl list-units --full -all | grep -q "openvpn@server.service"; then
    systemctl restart openvpn@server
else
    systemctl restart openvpn
fi

# Check Nginx Config
if ! nginx -t > /dev/null 2>&1; then
    repair_nginx
else
    systemctl restart nginx
fi

# Ensure check_status.sh is executable
if [ -f "check_status.sh" ]; then
    chmod +x check_status.sh
fi

echo -e "${GREEN}✅ Update Successfully Completed!${NC}"
if [ -d ".git" ]; then
    echo -e "${GREEN}   Version: $(get_version)${NC}"
fi
