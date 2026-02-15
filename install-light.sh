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
    
    print_success "System optimized"
}

install_dependencies() {
    print_step "Installing Minimal Dependencies"
    
    export DEBIAN_FRONTEND=noninteractive
    
    print_info "Updating package lists..."
    apt update -qq > /dev/null 2>&1
    
    print_info "Installing Python 3.11 (lightweight)..."
    add-apt-repository ppa:deadsnakes/ppa -y > /dev/null 2>&1
    apt install -y python3.11 python3.11-venv python3.11-dev python3-pip --no-install-recommends > /dev/null 2>&1
    
    # Use SQLite instead of PostgreSQL (much lighter)
    print_info "SQLite will be used (lightweight database)..."
    apt install -y sqlite3 --no-install-recommends > /dev/null 2>&1
    print_success "SQLite installed (saves ~150MB RAM)"
    
    # Redis with memory optimization
    print_info "Installing Redis (optimized)..."
    apt install -y redis-server --no-install-recommends > /dev/null 2>&1
    
    # Configure Redis for low memory
    cat >> /etc/redis/redis.conf << EOF

# Memory optimization
maxmemory 100mb
maxmemory-policy allkeys-lru
save ""
appendonly no
EOF
    
    systemctl restart redis
    print_success "Redis installed (limited to 100MB)"
    
    # Nginx (lightweight web server)
    print_info "Installing Nginx..."
    apt install -y nginx-light --no-install-recommends > /dev/null 2>&1
    print_success "Nginx-light installed"
    
    # Node.js for frontend
    print_info "Installing Node.js 18..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - > /dev/null 2>&1
    apt install -y nodejs --no-install-recommends > /dev/null 2>&1
    print_success "Node.js installed"
    
    print_info "Installing essential tools..."
    apt install -y curl wget git unzip --no-install-recommends > /dev/null 2>&1
    
    # Clean up
    apt autoremove -y > /dev/null 2>&1
    apt clean > /dev/null 2>&1
    
    print_success "All dependencies installed (minimal footprint)"
}

download_project() {
    print_step "Downloading VPN Master Panel"
    
    cd /opt
    if [ -d "vpn-master-panel" ]; then
        rm -rf vpn-master-panel
    fi
    
    git clone --depth 1 -q https://github.com/EchoDev7/vpn-master-panel.git > /dev/null 2>&1
    print_success "Project downloaded"
}

setup_backend() {
    print_step "Setting up Lightweight Backend"
    
    cd /opt/vpn-master-panel/backend
    
    print_info "Creating virtual environment..."
    python3.11 -m venv venv
    
    print_info "Installing minimal Python dependencies..."
    source venv/bin/activate
    
    # Create minimal requirements
    cat > requirements-light.txt << EOF
# Core (minimal)
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
pydantic-settings==2.1.0

# Database - SQLite only (no PostgreSQL)
sqlalchemy==2.0.25
aiosqlite==0.19.0

# Security (minimal)
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# Redis
redis==5.0.1

# Utils (minimal)
python-dotenv==1.0.0
psutil==5.9.8
EOF
    
    pip install --upgrade pip -q > /dev/null 2>&1
    pip install -r requirements-light.txt -q > /dev/null 2>&1
    print_success "Lightweight dependencies installed"
    
    # Generate config
    SECRET_KEY=$(openssl rand -hex 32)
    ADMIN_PASS=$(openssl rand -base64 12)
    
    cat > .env << EOF
# Lightweight Configuration
API_PORT=8000
WEB_PORT=3000
DEBUG=false

# SQLite Database (lightweight)
DATABASE_URL=sqlite:///./vpnmaster.db
USE_SQLITE=true

# Redis (limited memory)
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=$SECRET_KEY

# Admin
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=$ADMIN_PASS
INITIAL_ADMIN_EMAIL=admin@vpnmaster.local

# VPN Ports
OPENVPN_PORT=1194
WIREGUARD_PORT=51820

# Logging (minimal)
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
    
    # Use minimal npm install
    print_info "Installing Node dependencies..."
    npm install --production -q > /dev/null 2>&1
    
    print_info "Building optimized frontend..."
    NODE_OPTIONS="--max-old-space-size=512" npm run build -q > /dev/null 2>&1
    
    # Clean up node_modules after build (save space)
    rm -rf node_modules
    
    print_success "Frontend built and optimized"
}

setup_nginx() {
    print_step "Configuring Nginx (lightweight)"
    
    SERVER_IP=$(curl -s ifconfig.me)
    
    cat > /etc/nginx/sites-available/vpnmaster << EOF
# Backend API
server {
    listen 8000;
    server_name $SERVER_IP;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        
        # Buffer optimization
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }
}

# Frontend (with caching)
server {
    listen 3000;
    server_name $SERVER_IP;

    root /opt/vpn-master-panel/frontend/dist;
    index index.html;

    # Enable gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript;
    gzip_min_length 1000;

    # Cache static files
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
    
    # Optimize Nginx worker processes for 1 core
    sed -i 's/worker_processes.*/worker_processes 1;/' /etc/nginx/nginx.conf
    sed -i 's/worker_connections.*/worker_connections 512;/' /etc/nginx/nginx.conf
    
    nginx -t > /dev/null 2>&1
    systemctl restart nginx
    
    print_success "Nginx configured (optimized for 1 core)"
}

setup_systemd() {
    print_step "Creating Lightweight Service"
    
    cat > /etc/systemd/system/vpnmaster-backend.service << EOF
[Unit]
Description=VPN Master Panel Backend (Lightweight)
After=network.target redis.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/vpn-master-panel/backend
Environment="PATH=/opt/vpn-master-panel/backend/venv/bin"

# Lightweight config: 1 worker, limited memory
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
    
    ufw --force enable > /dev/null 2>&1
    ufw allow 22/tcp > /dev/null 2>&1
    ufw allow 3000/tcp > /dev/null 2>&1
    ufw allow 8000/tcp > /dev/null 2>&1
    ufw allow 1194/udp > /dev/null 2>&1
    ufw allow 51820/udp > /dev/null 2>&1
    
    print_success "Firewall configured"
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
    SERVER_IP=$(curl -s ifconfig.me)
    
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
    echo -e "  ✓ Database:     SQLite (file-based, no RAM overhead)"
    echo -e "  ✓ Redis:        Limited to 100MB"
    echo -e "  ✓ Backend:      Single worker, 300MB max"
    echo -e "  ✓ Nginx:        1 worker, optimized"
    echo -e "  ✓ Swap:         2GB configured"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Access Information:${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  🌐 Web Panel:  http://$SERVER_IP:3000"
    echo -e "  📡 API:        http://$SERVER_IP:8000"
    echo ""
    echo -e "  👤 Username:   admin"
    echo -e "  🔑 Password:   $ADMIN_PASS"
    echo ""
    echo -e "${RED}⚠️  Change password after first login!${NC}"
    echo ""
    
    show_resource_usage
    
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Performance Tips:${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  • Supports 20+ concurrent users"
    echo -e "  • Database: /opt/vpn-master-panel/backend/vpnmaster.db"
    echo -e "  • Monitor: sudo systemctl status vpnmaster-backend"
    echo -e "  • Logs: sudo journalctl -u vpnmaster-backend -f"
    echo ""
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
    setup_systemd
    setup_firewall
    
    show_success_message
}

main
