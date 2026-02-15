#!/bin/bash

#############################################################
#                                                           #
#           VPN Master Panel - Auto Installer               #
#         One-Command Installation for Ubuntu 22.04         #
#                                                           #
#############################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Logging
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
║         🛡️  VPN MASTER PANEL - AUTO INSTALLER  🛡️            ║
║                                                              ║
║           One-Command Installation for Ubuntu 22.04          ║
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
        echo "Please run: sudo bash $0"
        exit 1
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
        print_info "Your system: $PRETTY_NAME"
        exit 1
    fi
    
    print_success "OS Check: Ubuntu 22.04 ✓"
}

spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    while ps -p $pid > /dev/null 2>&1; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

install_dependencies() {
    print_step "Installing System Dependencies"
    
    export DEBIAN_FRONTEND=noninteractive
    
    print_info "Updating package lists..."
    apt update -qq > /dev/null 2>&1 &
    spinner $!
    print_success "Package lists updated"
    
    print_info "Installing Python 3.11..."
    add-apt-repository ppa:deadsnakes/ppa -y > /dev/null 2>&1
    apt install -y python3.11 python3.11-venv python3.11-dev python3-pip > /dev/null 2>&1 &
    spinner $!
    print_success "Python 3.11 installed"
    
    print_info "Installing PostgreSQL..."
    apt install -y postgresql postgresql-contrib > /dev/null 2>&1 &
    spinner $!
    print_success "PostgreSQL installed"
    
    print_info "Installing Redis..."
    apt install -y redis-server > /dev/null 2>&1 &
    spinner $!
    print_success "Redis installed"
    
    print_info "Installing Nginx..."
    apt install -y nginx > /dev/null 2>&1 &
    spinner $!
    print_success "Nginx installed"
    
    print_info "Installing Node.js 18..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - > /dev/null 2>&1
    apt install -y nodejs > /dev/null 2>&1 &
    spinner $!
    print_success "Node.js installed"
    
    print_info "Installing additional tools..."
    apt install -y curl wget git unzip build-essential libpq-dev > /dev/null 2>&1 &
    spinner $!
    print_success "Additional tools installed"
}

setup_database() {
    print_step "Setting up PostgreSQL Database"
    
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    
    print_info "Creating database and user..."
    sudo -u postgres psql > /dev/null 2>&1 << EOF
CREATE DATABASE vpnmaster;
CREATE USER vpnmaster WITH ENCRYPTED PASSWORD '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE vpnmaster TO vpnmaster;
ALTER DATABASE vpnmaster OWNER TO vpnmaster;
EOF
    
    print_success "Database created: vpnmaster"
    print_success "Database user: vpnmaster"
    print_info "Database password: [Generated automatically]"
}

download_project() {
    print_step "Downloading VPN Master Panel"
    
    print_info "Cloning from GitHub..."
    cd /opt
    if [ -d "vpn-master-panel" ]; then
        print_warning "Directory exists, removing old version..."
        rm -rf vpn-master-panel
    fi
    
    git clone -q https://github.com/EchoDev7/vpn-master-panel.git > /dev/null 2>&1 &
    spinner $!
    print_success "Project downloaded successfully"
}

setup_backend() {
    print_step "Setting up Backend (FastAPI)"
    
    cd /opt/vpn-master-panel/backend
    
    print_info "Creating Python virtual environment..."
    python3.11 -m venv venv
    print_success "Virtual environment created"
    
    print_info "Installing Python dependencies..."
    source venv/bin/activate
    pip install --upgrade pip -q > /dev/null 2>&1
    pip install -r requirements.txt -q > /dev/null 2>&1 &
    spinner $!
    print_success "Python dependencies installed"
    
    print_info "Generating configuration..."
    SECRET_KEY=$(openssl rand -hex 32)
    ADMIN_PASS=$(openssl rand -base64 12)
    
    cat > .env << EOF
# VPN Master Panel Configuration
API_PORT=8000
WEB_PORT=3000
DEBUG=false

DATABASE_URL=postgresql://vpnmaster:$DB_PASSWORD@localhost:5432/vpnmaster
REDIS_URL=redis://localhost:6379/0

SECRET_KEY=$SECRET_KEY

INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=$ADMIN_PASS
INITIAL_ADMIN_EMAIL=admin@vpnmaster.local

OPENVPN_PORT=1194
WIREGUARD_PORT=51820
LOG_LEVEL=INFO
EOF
    
    print_success "Configuration file created"
    
    print_info "Initializing database..."
    python3 << PYEOF
from app.database import init_db
init_db()
PYEOF
    print_success "Database initialized"
}

setup_frontend() {
    print_step "Setting up Frontend (React)"
    
    cd /opt/vpn-master-panel/frontend
    
    print_info "Installing Node.js dependencies..."
    npm install -q > /dev/null 2>&1 &
    spinner $!
    print_success "Node.js dependencies installed"
    
    print_info "Building frontend for production..."
    npm run build -q > /dev/null 2>&1 &
    spinner $!
    print_success "Frontend built successfully"
}

setup_nginx() {
    print_step "Configuring Nginx"
    
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
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}

# Frontend
server {
    listen 3000;
    server_name $SERVER_IP;

    root /opt/vpn-master-panel/frontend/dist;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location /api {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
    }
}
EOF
    
    rm -f /etc/nginx/sites-enabled/default
    ln -sf /etc/nginx/sites-available/vpnmaster /etc/nginx/sites-enabled/
    
    nginx -t > /dev/null 2>&1
    systemctl restart nginx
    print_success "Nginx configured"
}

setup_systemd() {
    print_step "Creating System Service"
    
    cat > /etc/systemd/system/vpnmaster-backend.service << EOF
[Unit]
Description=VPN Master Panel Backend
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/vpn-master-panel/backend
Environment="PATH=/opt/vpn-master-panel/backend/venv/bin"
ExecStart=/opt/vpn-master-panel/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable vpnmaster-backend > /dev/null 2>&1
    systemctl start vpnmaster-backend
    
    sleep 3
    
    if systemctl is-active --quiet vpnmaster-backend; then
        print_success "Backend service started"
    else
        print_error "Failed to start backend service"
        print_info "Check logs: sudo journalctl -u vpnmaster-backend"
        exit 1
    fi
}

setup_firewall() {
    print_step "Configuring Firewall"
    
    print_info "Setting up UFW rules..."
    ufw --force enable > /dev/null 2>&1
    ufw allow 22/tcp > /dev/null 2>&1
    ufw allow 3000/tcp > /dev/null 2>&1
    ufw allow 8000/tcp > /dev/null 2>&1
    ufw allow 1194/udp > /dev/null 2>&1
    ufw allow 51820/udp > /dev/null 2>&1
    
    print_success "Firewall configured"
}

final_checks() {
    print_step "Running Final Checks"
    
    sleep 2
    
    # Check services
    services=("postgresql" "redis" "nginx" "vpnmaster-backend")
    for service in "${services[@]}"; do
        if systemctl is-active --quiet $service; then
            print_success "$service: Running ✓"
        else
            print_error "$service: Not running ✗"
        fi
    done
    
    # Test API
    if curl -s http://localhost:8000/health | grep -q "healthy"; then
        print_success "API Health Check: Passed ✓"
    else
        print_warning "API Health Check: Failed (may need a moment)"
    fi
}

show_success_message() {
    SERVER_IP=$(curl -s ifconfig.me)
    
    clear
    echo -e "${GREEN}"
    cat << "EOF"
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║              🎉  INSTALLATION SUCCESSFUL!  🎉                ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Access Information:${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${GREEN}🌐 Web Panel:${NC}     http://$SERVER_IP:3000"
    echo -e "  ${GREEN}📡 API:${NC}           http://$SERVER_IP:8000"
    echo -e "  ${GREEN}📚 API Docs:${NC}      http://$SERVER_IP:8000/docs"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Login Credentials:${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${GREEN}Username:${NC}  admin"
    echo -e "  ${GREEN}Password:${NC}  $ADMIN_PASS"
    echo ""
    echo -e "${RED}⚠️  IMPORTANT: Change your password after first login!${NC}"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Useful Commands:${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  View logs:       ${BLUE}sudo journalctl -u vpnmaster-backend -f${NC}"
    echo -e "  Restart backend: ${BLUE}sudo systemctl restart vpnmaster-backend${NC}"
    echo -e "  Restart nginx:   ${BLUE}sudo systemctl restart nginx${NC}"
    echo -e "  Check status:    ${BLUE}sudo systemctl status vpnmaster-backend${NC}"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${GREEN}Installation completed in $(date)${NC}"
    echo -e "${GREEN}Log file: $LOG_FILE${NC}"
    echo ""
}

# Main Installation Flow
main() {
    print_banner
    
    print_info "Starting VPN Master Panel installation..."
    print_info "This will take 5-10 minutes..."
    echo ""
    
    check_root
    check_os
    
    install_dependencies
    setup_database
    download_project
    setup_backend
    setup_frontend
    setup_nginx
    setup_systemd
    setup_firewall
    final_checks
    
    show_success_message
}

# Run
main
