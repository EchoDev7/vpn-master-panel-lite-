#!/bin/bash

#############################################################
#                                                           #
#     VPN Master Panel - LIGHTWEIGHT Auto Installer        #
#        Optimized for 1GB RAM / 1 Core CPU Servers        #
#                                                           #
#############################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

LOG_FILE="/var/log/vpnmaster-install.log"
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

# Functions
print_banner() {
    clear
    echo -e "${CYAN}"
    cat << "EOF"
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║      🛡️  VPN MASTER PANEL - LIGHTWEIGHT INSTALLER  🛡️        ║
║                                                              ║
║         Optimized for Low-Resource Servers (1GB RAM)         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

print_step() {
    echo -e "\n${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}▶ $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}\n"
}

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${CYAN}ℹ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root"
        exit 1
    fi
}

check_resources() {
    print_step "Checking System Resources"
    
    # Check RAM
    total_ram=$(free -m | awk '/^Mem:/{print $2}')
    if [ $total_ram -lt 900 ]; then
        print_error "Insufficient RAM: ${total_ram}MB (minimum 1GB required)"
        exit 1
    fi
    print_success "RAM: ${total_ram}MB ✓"
    
    # Check CPU cores
    cpu_cores=$(nproc)
    print_success "CPU Cores: $cpu_cores ✓"
    
    # Check disk space
    disk_space=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ $disk_space -lt 10 ]; then
        print_warning "Low disk space: ${disk_space}GB (recommended 20GB+)"
    else
        print_success "Disk Space: ${disk_space}GB ✓"
    fi
}

check_os() {
    if [[ ! -f /etc/os-release ]]; then
        print_error "Cannot detect OS"
        exit 1
    fi
    
    source /etc/os-release
    if [[ "$ID" != "ubuntu" ]] || [[ "$VERSION_ID" != "22.04" ]]; then
        print_error "This installer only supports Ubuntu 22.04"
        exit 1
    fi
    
    print_success "OS: Ubuntu 22.04 ✓"
}

optimize_system() {
    print_step "Optimizing System for Low Resources"
    
    # Disable unnecessary services
    print_info "Disabling unnecessary services..."
    systemctl disable snapd.service > /dev/null 2>&1 || true
    systemctl disable ModemManager.service > /dev/null 2>&1 || true
    
    # Configure swap (important for 1GB RAM)
    print_info "Configuring swap memory..."
    if [ ! -f /swapfile ]; then
        fallocate -l 2G /swapfile
        chmod 600 /swapfile
        mkswap /swapfile
        swapon /swapfile
        echo '/swapfile none swap sw 0 0' >> /etc/fstab
        print_success "2GB swap created"
    else
        print_info "Swap already exists"
    fi
    
    # Optimize swap usage
    sysctl vm.swappiness=10
    sysctl vm.vfs_cache_pressure=50
    echo "vm.swappiness=10" >> /etc/sysctl.conf
    echo "vm.vfs_cache_pressure=50" >> /etc/sysctl.conf
    
    # Enable IP Forwarding and Advanced Network Tuning (Enterprise)
    print_info "Optimizing Network Stack for VPN Throughput..."
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
    
    print_success "System & Network stack optimized"
}

install_dependencies() {
    print_step "Installing Minimal Dependencies"
    
    export DEBIAN_FRONTEND=noninteractive
    
    print_info "Updating package lists and upgrading system..."
    apt update -qq > /dev/null 2>&1
    apt upgrade -y > /dev/null 2>&1
    
    print_info "Installing VPN Core Services (Latest)..."
    apt install -y openvpn wireguard wireguard-tools iptables iptables-persistent --no-install-recommends > /dev/null 2>&1
    print_success "OpenVPN & WireGuard installed"

    print_info "Installing Certbot (Let's Encrypt SSL)..."
    apt install -y certbot python3-certbot-nginx --no-install-recommends > /dev/null 2>&1
    print_success "Certbot installed ($(certbot --version 2>&1 | head -1))"

    print_info "Installing sqlite3 CLI (used by update.sh to read panel settings)..."
    apt install -y sqlite3 --no-install-recommends > /dev/null 2>&1
    print_success "sqlite3 installed"

    print_info "Installing Python 3.11 (latest)..."
    add-apt-repository ppa:deadsnakes/ppa -y > /dev/null 2>&1
    apt install -y python3.11 python3.11-venv python3.11-dev python3-pip --no-install-recommends > /dev/null 2>&1
    
    # Use SQLite instead of PostgreSQL (much lighter)
    print_info "SQLite will be used (lightweight database)..."
    apt install -y sqlite3 --no-install-recommends > /dev/null 2>&1
    print_success "SQLite installed (saves ~150MB RAM)"
    
    # Nginx (lightweight web server)
    print_info "Installing Nginx..."
    apt install -y nginx-light --no-install-recommends > /dev/null 2>&1
    print_success "Nginx-light installed"
    
    # Node.js for frontend
    print_info "Installing Node.js 20 (LTS)..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1
    apt install -y nodejs --no-install-recommends > /dev/null 2>&1
    print_success "Node.js 20 installed"
    
    print_info "Installing essential tools..."
    apt install -y curl wget git unzip software-properties-common fail2ban --no-install-recommends > /dev/null 2>&1
    
    # Configure Fail2Ban
    cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
EOF
    systemctl restart fail2ban > /dev/null 2>&1
    
    # Clean up
    apt autoremove -y > /dev/null 2>&1
    apt clean > /dev/null 2>&1
    
    print_success "All dependencies installed (minimal footprint)"
}

download_project() {
    print_step "Copying Local VPN Master Panel Files"
    
    CURRENT_DIR="$PWD"
    cd /opt
    if [ -d "vpn-master-panel-lite" ]; then
        rm -rf vpn-master-panel-lite
    fi
    
    # Copy the current directory to the installation path
    cp -r "$CURRENT_DIR" /opt/vpn-master-panel
    print_success "Project files copied locally"
}

setup_backend() {
    print_step "Setting up Lightweight Backend"
    
    cd /opt/vpn-master-panel/backend
    
    print_info "Creating virtual environment..."
    python3.11 -m venv venv
    
    print_info "Installing minimal Python dependencies..."
    source venv/bin/activate
    
    # Create minimal requirements with loose versioning for latest compatible
    cat > requirements.txt << EOF
# Core (minimal)
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.3
pydantic-settings>=2.1.0

# Database - SQLite only (no PostgreSQL)
sqlalchemy>=2.0.25
aiosqlite>=0.19.0

# Security (minimal)
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6

# Utils (minimal)
python-dotenv>=1.0.0
psutil>=5.9.8
EOF
    
    pip install --upgrade pip -q > /dev/null 2>&1
    pip install -r requirements.txt -q > /dev/null 2>&1
    print_success "Lightweight dependencies installed"

    # Ensure auth script is executable
    chmod +x /opt/vpn-master-panel/backend/auth.py > /dev/null 2>&1 || true
    
    # Generate config
    SECRET_KEY=$(openssl rand -hex 32)
    ADMIN_PASS="admin" # Default password as requested
    
    cat > .env << EOF
# ─── VPN Master Panel — Runtime Configuration ───────────────
# Generated by install.sh — do NOT edit API_PORT / WEB_PORT
# unless you also change Nginx and the systemd service.

# FastAPI backend (internal — Nginx proxies :8000 → :8001)
API_PORT=8001
WEB_PORT=3000
DEBUG=false

# SQLite Database (lightweight, no PostgreSQL needed)
DATABASE_URL=sqlite:///./vpnmaster_lite.db
USE_SQLITE=true

# Security — auto-generated 256-bit key
SECRET_KEY=$SECRET_KEY

# Admin account (change password after first login!)
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=$ADMIN_PASS
INITIAL_ADMIN_EMAIL=admin@active-vpn.com

# VPN service ports (OpenVPN & WireGuard)
OPENVPN_PORT=1194
WIREGUARD_PORT=51820

# Logging level (WARNING keeps logs quiet in production)
LOG_LEVEL=WARNING
EOF
    
    print_success "Lightweight config created (SQLite)"
    
    # Initialize database
    print_info "Initializing SQLite database..."
    python3 << PYEOF
from app.database import init_db
init_db()
PYEOF
    print_success "Database initialized (file-based, no extra RAM)"
}

setup_frontend() {
    print_step "Building Frontend (optimized)"
    
    cd /opt/vpn-master-panel/frontend
    
    # Install all dependencies including dev build tools like vite
    print_info "Installing Node dependencies..."
    npm install -q > /dev/null 2>&1
    
    print_info "Building optimized frontend..."
    npm run build -q > /dev/null 2>&1
    
    # Verify Build Success
    if [ ! -f "dist/index.html" ]; then
        print_error "Frontend Build Failed! 'dist/index.html' not found."
        exit 1
    fi
    
    # Fix Permissions (Critical for Nginx)
    chmod -R 755 dist
    
    print_success "Frontend built and optimized"
}

setup_nginx() {
    print_step "Configuring Nginx (lightweight)"

    # Create safe config
    cat > /etc/nginx/sites-available/vpnmaster << 'NGINXEOF'
# ─────────────────────────────────────────────────────────────
# VPN Master Panel — Nginx Configuration
#
# Architecture:
#   Port 3000  → React frontend (built static files)
#   Port 8000  → Public API gateway  (proxies to FastAPI :8001)
#   Port 80    → Reserved for Let's Encrypt ACME challenges
#
# Backend FastAPI runs on 127.0.0.1:8001 (internal only)
# ─────────────────────────────────────────────────────────────

# ── Port 80: ACME challenge passthrough (Let's Encrypt) ──────
server {
    listen 0.0.0.0:80;
    server_name _;

    # ACME challenge — served from webroot for certbot
    location /.well-known/acme-challenge/ {
        root /var/www/html;
        try_files $uri =404;
    }

    # All other HTTP → just return 200 (avoids redirect loops during cert issuance)
    location / {
        return 200 "VPN Master Panel";
        add_header Content-Type text/plain;
    }
}

# ── Port 8000: Backend API gateway ───────────────────────────
server {
    listen 0.0.0.0:8000;
    server_name _;

    # ── Regular API endpoints ─────────────────────────────────
    location /api/ {
        proxy_pass         http://127.0.0.1:8001/api/;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;

        # ── Critical for SSL streaming ────────────────────────
        # certbot can take 30-180 seconds; never timeout during SSL issuance
        proxy_read_timeout  600s;
        proxy_send_timeout  600s;
        proxy_connect_timeout 30s;

        # Disable ALL buffering so SSE / streaming chunks reach
        # the browser immediately (required for live certbot output)
        proxy_buffering    off;
        proxy_cache        off;
        proxy_cache_bypass 1;
        chunked_transfer_encoding on;

        # Tell Nginx NOT to buffer this response (belt-and-suspenders)
        add_header X-Accel-Buffering no always;
    }

    # ── WebSocket endpoint ────────────────────────────────────
    location /ws/ {
        proxy_pass         http://127.0.0.1:8001/ws/;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade    $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_set_header   Host       $host;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
        proxy_buffering    off;
    }

    # ── Fallback: any path not matched above ──────────────────
    location / {
        proxy_pass         http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header   Host       $host;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
        proxy_buffering    off;
    }
}

# ── Port 3000: React frontend (static files) ─────────────────
server {
    listen 0.0.0.0:3000;
    server_name _;

    root  /opt/vpn-master-panel/frontend/dist;
    index index.html;

    # Enable gzip for static assets
    gzip on;
    gzip_types text/plain text/css application/json application/javascript
               text/xml application/xml text/javascript image/svg+xml;
    gzip_min_length 1000;

    # Cache static assets aggressively (Vite adds content hash to filenames)
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
        expires     30d;
        add_header  Cache-Control "public, immutable";
        try_files   $uri =404;
    }

    # SPA routing — all unknown paths → index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Pass /api/ calls through to backend (fallback if VITE_API_URL is empty)
    location /api/ {
        proxy_pass         http://127.0.0.1:8001/api/;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;

        # Same streaming settings as port 8000
        proxy_read_timeout  600s;
        proxy_send_timeout  600s;
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
    
    # Optimize Nginx worker processes for 1 core
    sed -i 's/worker_processes.*/worker_processes 1;/' /etc/nginx/nginx.conf
    sed -i 's/worker_connections.*/worker_connections 512;/' /etc/nginx/nginx.conf
    
    nginx -t > /dev/null 2>&1
    systemctl restart nginx
    
    print_success "Nginx configured (optimized for 1 core)"
}

setup_pki() {
    print_step "Initializing OpenVPN PKI (OpenSSL)"
    
    DATA_DIR="/opt/vpn-master-panel/backend/data/openvpn"
    mkdir -p "$DATA_DIR"
    
    # Clean old keys (if any)
    rm -f $DATA_DIR/ca.crt $DATA_DIR/ca.key
    rm -f $DATA_DIR/server.crt $DATA_DIR/server.key $DATA_DIR/server.csr
    rm -f $DATA_DIR/ta.key $DATA_DIR/dh.pem $DATA_DIR/server.ext

    # Generate CA
    print_info "Generating CA..."
    openssl req -new -x509 -days 3650 -nodes \
        -out $DATA_DIR/ca.crt \
        -keyout $DATA_DIR/ca.key \
        -subj "/CN=VPN-Master-CA" 2>/dev/null

    # Generate Server Key & CSR
    print_info "Generating Server Cert/Key..."
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
    print_info "Generating DH & TA..."
    openssl dhparam -out $DATA_DIR/dh.pem 2048 2>/dev/null
    openvpn --genkey tls-auth $DATA_DIR/ta.key

    # Permissions
    chmod 600 $DATA_DIR/server.key $DATA_DIR/ta.key $DATA_DIR/ca.key
    chmod 644 $DATA_DIR/ca.crt $DATA_DIR/server.crt $DATA_DIR/dh.pem
    
    # Cleanup CSR
    rm -f $DATA_DIR/server.csr $DATA_DIR/server.ext
    
    # Copy keys to /etc/openvpn (for the service)
    mkdir -p /etc/openvpn
    print_success "PKI Initialized (Standard EasyRSA)"
}

setup_systemd() {
    print_step "Creating Lightweight Service"
    
    cat > /etc/systemd/system/vpnmaster-backend.service << EOF
[Unit]
Description=VPN Master Panel Backend (Lightweight)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/vpn-master-panel/backend
Environment="PATH=/opt/vpn-master-panel/backend/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/opt/vpn-master-panel/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001 --workers 1 --limit-concurrency 50

# Memory limits
MemoryMax=300M
MemoryHigh=250M

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable vpnmaster-backend > /dev/null 2>&1
    systemctl start vpnmaster-backend
    
    sleep 3
    
    if systemctl is-active --quiet vpnmaster-backend; then
        print_success "Lightweight backend started (limited to 300MB RAM)"
    else
        print_error "Failed to start backend"
        exit 1
    fi
}

setup_firewall() {
    print_step "Configuring Firewall"

    ufw default deny incoming
    ufw default allow outgoing

    ufw allow 22/tcp > /dev/null 2>&1
    ufw allow 80/tcp > /dev/null 2>&1
    ufw allow 443/tcp > /dev/null 2>&1
    ufw allow 8443/tcp > /dev/null 2>&1  # Panel HTTPS (avoids conflict with OpenVPN on 443)
    
    # Configure NAT for internet routing (Enterprise Idempotent Method)
    print_info "Configuring UFW NAT routing..."
    # Always allow forwarding
    sed -i 's/DEFAULT_FORWARD_POLICY="DROP"/DEFAULT_FORWARD_POLICY="ACCEPT"/g' /etc/default/ufw
    
    # SELF HEALING: Restore UFW rules if prior script deleted the *filter block
    if ! grep -q "^\*filter" /etc/ufw/before.rules 2>/dev/null; then
        echo -e "${YELLOW}⚠️ Corrupted UFW before.rules detected. Restoring to defaults...${NC}"
        if [ -f "/usr/share/ufw/before.rules" ]; then
            cp /usr/share/ufw/before.rules /etc/ufw/before.rules
        fi
    fi
    
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
    else
        print_warning "Could not detect main network interface for NAT mapping."
    fi
    
    # Panel ports
    ufw allow 3000/tcp > /dev/null 2>&1
    ufw allow 8000/tcp > /dev/null 2>&1
    
    # VPN ports
    ufw allow 1194/udp > /dev/null 2>&1
    ufw allow 51820/udp > /dev/null 2>&1
    
    ufw --force enable > /dev/null 2>&1
    
    print_success "Firewall configured (secured)"
}

setup_apparmor() {
    print_step "Configuring AppArmor & Scripts"
    
    # Ensure TUN Device Exists
    if [ ! -c /dev/net/tun ]; then
        print_info "Creating /dev/net/tun..."
        mkdir -p /dev/net
        mknod /dev/net/tun c 10 200
        chmod 600 /dev/net/tun
    fi

    # Deploy Auth Scripts to standard location
    mkdir -p /etc/openvpn/scripts
    cp /opt/vpn-master-panel/backend/auth.py /etc/openvpn/scripts/auth.py
    cp /opt/vpn-master-panel/backend/scripts/auth.sh /etc/openvpn/scripts/ 2>/dev/null || true
    cp /opt/vpn-master-panel/backend/scripts/client-connect.sh /etc/openvpn/scripts/ 2>/dev/null || true
    cp /opt/vpn-master-panel/backend/scripts/client-disconnect.sh /etc/openvpn/scripts/ 2>/dev/null || true
    cp /opt/vpn-master-panel/backend/scripts/get_speed_limit.py /etc/openvpn/scripts/ 2>/dev/null || true

    chmod 755 /etc/openvpn/scripts/auth.py
    chmod 755 /etc/openvpn/scripts/*.sh 2>/dev/null || true
    chmod 755 /etc/openvpn/scripts/*.py 2>/dev/null || true
    chown root:root /etc/openvpn/scripts/* 2>/dev/null || true
    print_success "Auth scripts deployed to /etc/openvpn/scripts/"

    if [ -f "/etc/apparmor.d/usr.sbin.openvpn" ]; then
        print_info "Updating OpenVPN AppArmor profile..."
        if ! grep -q "/etc/openvpn/scripts/\*\*" /etc/apparmor.d/usr.sbin.openvpn; then
            sed -i '/}/d' /etc/apparmor.d/usr.sbin.openvpn
            echo "  /opt/vpn-master-panel/backend/data/** r," >> /etc/apparmor.d/usr.sbin.openvpn
            echo "  /etc/openvpn/scripts/** rUx," >> /etc/apparmor.d/usr.sbin.openvpn
            echo "  /opt/vpn-master-panel/backend/** r," >> /etc/apparmor.d/usr.sbin.openvpn
            echo "}" >> /etc/apparmor.d/usr.sbin.openvpn
            
            systemctl reload apparmor
            print_success "AppArmor configured (Auth Scripts Unconfined)"
        else
            print_info "AppArmor already configured"
        fi
    else
        print_info "AppArmor not present, skipping"
    fi
}

show_resource_usage() {
    print_step "Resource Usage Report"
    
    echo -e "${CYAN}Current Usage:${NC}"
    echo ""
    
    # RAM usage
    used_ram=$(free -m | awk '/^Mem:/{print $3}')
    total_ram=$(free -m | awk '/^Mem:/{print $2}')
    echo -e "  RAM:  ${used_ram}MB / ${total_ram}MB"
    
    # Swap usage
    used_swap=$(free -m | awk '/^Swap:/{print $3}')
    total_swap=$(free -m | awk '/^Swap:/{print $2}')
    echo -e "  Swap: ${used_swap}MB / ${total_swap}MB"
    
    # Disk usage
    disk_used=$(df -h / | awk 'NR==2 {print $3}')
    disk_total=$(df -h / | awk 'NR==2 {print $2}')
    echo -e "  Disk: ${disk_used} / ${disk_total}"
    
    echo ""
    print_success "Optimized for minimal resource usage!"
}

show_success_message() {
    SERVER_IP=$(curl -s --connect-timeout 5 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')

    clear
    echo -e "${GREEN}"
    cat << "EOF"
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║         🎉  LIGHTWEIGHT INSTALLATION SUCCESSFUL!  🎉         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"

    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}🎯 Optimized for Low Resources:${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ✓ Database:  SQLite (file-based, no RAM overhead)"
    echo -e "  ✓ Backend:   Single worker, 300MB max"
    echo -e "  ✓ Nginx:     1 worker, optimized"
    echo -e "  ✓ Swap:      2GB configured"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}📡 Access Information:${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  🌐 Panel (HTTP):   ${GREEN}http://$SERVER_IP:3000${NC}"
    echo -e "  📡 API Gateway:    http://$SERVER_IP:8000"
    echo ""
    echo -e "  👤 Username:  admin"
    echo -e "  🔑 Password:  admin"
    echo ""
    echo -e "${RED}  ⚠️  IMPORTANT: Change the admin password after first login!${NC}"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}🔒 Next Step — Enable HTTPS (SSL):${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  1. Point your domain DNS to this server: ${GREEN}$SERVER_IP${NC}"
    echo -e "     e.g.  panel.yourdomain.com  →  $SERVER_IP  (Cloudflare: DNS-only ⚪)"
    echo ""
    echo -e "  2. Open the panel → ${GREEN}Settings → 🔒 Domain & SSL${NC}"
    echo -e "     • Enter your domain:  panel.yourdomain.com"
    echo -e "     • Enter your email:   admin@yourdomain.com"
    echo -e "     • Click: ${GREEN}Issue Let's Encrypt SSL${NC}"
    echo ""
    echo -e "  3. After SSL is issued, access via HTTPS:"
    echo -e "     ${GREEN}https://panel.yourdomain.com:8443${NC}"
    echo ""
    echo -e "  ℹ️  Port 8443 is used for HTTPS because OpenVPN uses port 443."
    echo -e "  ℹ️  Port 8443 is already open in the firewall."
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}🔗 Subscription Domain (for users):${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  Point a second domain:  sub.yourdomain.com  →  $SERVER_IP"
    echo -e "  Then in Settings → 🔒 Domain & SSL → enter it as Subscription Domain"
    echo -e "  Click ${GREEN}Issue Let's Encrypt SSL${NC} — it will get cert for both domains."
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}🛠️  Useful Commands:${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  Status:    systemctl status vpnmaster-backend nginx"
    echo -e "  Logs:      journalctl -u vpnmaster-backend -f"
    echo -e "  Diagnose:  bash /opt/vpn-master-panel/diagnose.sh"
    echo -e "  Update:    bash /opt/vpn-master-panel/update.sh"
    echo ""

    show_resource_usage
}

# Main
main() {
    print_banner
    
    print_warning "⚡ LIGHTWEIGHT MODE"
    print_info "Optimized for 1GB RAM / 1 Core CPU servers"
    echo ""
    
    check_root
    check_os
    check_resources
    
    optimize_system
    install_dependencies
    download_project
    setup_backend
    setup_frontend
    setup_nginx
    setup_pki
    setup_systemd
    setup_apparmor
    setup_firewall
    
    # Ensure log files exist and have correct permissions
    mkdir -p /var/log/openvpn
    touch /var/log/openvpn/openvpn.log
    touch /var/log/openvpn/openvpn-status.log
    touch /var/log/openvpn/auth.log
    touch /var/log/openvpn/auth_wrapper.log
    chmod 755 /var/log/openvpn
    chmod 666 /var/log/openvpn/auth.log
    chmod 666 /var/log/openvpn/auth_wrapper.log
    
    show_success_message
}

main
