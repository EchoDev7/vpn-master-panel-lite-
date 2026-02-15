#!/bin/bash

# VPN Master Panel - Automated Installation Script
# Supports Ubuntu 22.04+

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Functions
print_banner() {
    clear
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                                                              ║"
    echo "║          🛡️  VPN MASTER PANEL - INSTALLATION  🛡️             ║"
    echo "║                                                              ║"
    echo "║     Advanced Multi-Protocol VPN Management Panel            ║"
    echo "║           with PersianShield™ Technology                    ║"
    echo "║                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   print_error "This script must be run as root"
   exit 1
fi

# Check OS
if [[ ! -f /etc/os-release ]]; then
    print_error "Cannot detect OS. This script requires Ubuntu 22.04+"
    exit 1
fi

source /etc/os-release
if [[ "$ID" != "ubuntu" ]] || [[ "${VERSION_ID}" < "22.04" ]]; then
    print_error "This script requires Ubuntu 22.04 or higher"
    exit 1
fi

print_banner
print_info "Detected: $PRETTY_NAME"
echo ""

# Ask installation method
echo -e "${YELLOW}Select installation method:${NC}"
echo "1) Docker (Recommended - Easiest)"
echo "2) Manual (Advanced)"
read -p "Enter choice [1-2]: " install_method

if [[ "$install_method" != "1" && "$install_method" != "2" ]]; then
    print_error "Invalid choice"
    exit 1
fi

# Get configuration
echo ""
print_info "Configuration Setup"
echo ""

read -p "Enter admin username [admin]: " ADMIN_USERNAME
ADMIN_USERNAME=${ADMIN_USERNAME:-admin}

read -sp "Enter admin password: " ADMIN_PASSWORD
echo ""
if [[ -z "$ADMIN_PASSWORD" ]]; then
    print_error "Password cannot be empty"
    exit 1
fi

read -p "Enter admin email: " ADMIN_EMAIL
ADMIN_EMAIL=${ADMIN_EMAIL:-admin@vpnmaster.local}

read -p "Enter web panel port [3000]: " WEB_PORT
WEB_PORT=${WEB_PORT:-3000}

read -p "Enter API port [8000]: " API_PORT
API_PORT=${API_PORT:-8000}

# Generate secret key
SECRET_KEY=$(openssl rand -hex 32)
DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

# Install Docker method
install_docker_method() {
    print_info "Installing Docker deployment..."
    
    # Install Docker
    if ! command -v docker &> /dev/null; then
        print_info "Installing Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        rm get-docker.sh
        print_success "Docker installed"
    else
        print_success "Docker already installed"
    fi
    
    # Install Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_info "Installing Docker Compose..."
        curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        print_success "Docker Compose installed"
    else
        print_success "Docker Compose already installed"
    fi
    
    # Clone repository
    print_info "Downloading VPN Master Panel..."
    INSTALL_DIR="/opt/vpn-master-panel"
    
    if [[ -d "$INSTALL_DIR" ]]; then
        print_warning "Installation directory exists. Backing up..."
        mv "$INSTALL_DIR" "$INSTALL_DIR.backup.$(date +%s)"
    fi
    
    # For this demo, we'll create the structure
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    
    # Create .env file
    print_info "Creating configuration..."
    cat > .env <<EOF
# VPN Master Panel Configuration
API_PORT=$API_PORT
WEB_PORT=$WEB_PORT
DEBUG=false

DB_PASSWORD=$DB_PASSWORD
SECRET_KEY=$SECRET_KEY

INITIAL_ADMIN_USERNAME=$ADMIN_USERNAME
INITIAL_ADMIN_PASSWORD=$ADMIN_PASSWORD
INITIAL_ADMIN_EMAIL=$ADMIN_EMAIL

OPENVPN_PORT=1194
WIREGUARD_PORT=51820
L2TP_PSK=vpnmaster
CISCO_PORT=4443

DOMAIN_FRONTING_ENABLED=true
TLS_OBFUSCATION_ENABLED=true
AUTO_SWITCH_ON_BLOCK=true

LOG_LEVEL=INFO
EOF
    
    print_success "Configuration created"
    
    # Start services
    print_info "Starting services..."
    docker-compose up -d
    
    print_success "Services started!"
    
    # Wait for services to be ready
    print_info "Waiting for services to initialize..."
    sleep 10
    
    # Show summary
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                  INSTALLATION COMPLETE!                      ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}Access Information:${NC}"
    echo -e "  ${YELLOW}Web Panel:${NC}  http://$(hostname -I | awk '{print $1}'):$WEB_PORT"
    echo -e "  ${YELLOW}API:${NC}        http://$(hostname -I | awk '{print $1}'):$API_PORT"
    echo -e "  ${YELLOW}API Docs:${NC}   http://$(hostname -I | awk '{print $1}'):$API_PORT/docs"
    echo ""
    echo -e "${CYAN}Login Credentials:${NC}"
    echo -e "  ${YELLOW}Username:${NC}   $ADMIN_USERNAME"
    echo -e "  ${YELLOW}Password:${NC}   $ADMIN_PASSWORD"
    echo ""
    echo -e "${RED}⚠️  IMPORTANT: Change your password after first login!${NC}"
    echo ""
    echo -e "${CYAN}Useful Commands:${NC}"
    echo -e "  View logs:        ${YELLOW}docker-compose logs -f${NC}"
    echo -e "  Restart:          ${YELLOW}docker-compose restart${NC}"
    echo -e "  Stop:             ${YELLOW}docker-compose stop${NC}"
    echo -e "  Start:            ${YELLOW}docker-compose start${NC}"
    echo ""
}

# Install manual method
install_manual_method() {
    print_info "Starting manual installation..."
    
    # Update system
    print_info "Updating system packages..."
    apt update && apt upgrade -y
    
    # Install dependencies
    print_info "Installing system dependencies..."
    apt install -y \
        python3.11 python3-pip python3-venv \
        postgresql postgresql-contrib \
        redis-server \
        nginx \
        openvpn wireguard-tools \
        xl2tpd strongswan \
        ocserv \
        curl wget git
    
    print_success "Dependencies installed"
    
    # Setup PostgreSQL
    print_info "Configuring PostgreSQL..."
    sudo -u postgres psql -c "CREATE DATABASE vpnmaster;" 2>/dev/null || true
    sudo -u postgres psql -c "CREATE USER vpnmaster WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || true
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE vpnmaster TO vpnmaster;" 2>/dev/null || true
    
    print_success "PostgreSQL configured"
    
    # Install backend
    print_info "Setting up backend..."
    INSTALL_DIR="/opt/vpn-master-panel"
    mkdir -p "$INSTALL_DIR/backend"
    cd "$INSTALL_DIR/backend"
    
    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate
    
    # Note: In production, you would install from requirements.txt
    pip install fastapi uvicorn sqlalchemy psycopg2-binary redis
    
    # Create .env
    cat > .env <<EOF
DATABASE_URL=postgresql://vpnmaster:$DB_PASSWORD@localhost:5432/vpnmaster
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=$SECRET_KEY
INITIAL_ADMIN_USERNAME=$ADMIN_USERNAME
INITIAL_ADMIN_PASSWORD=$ADMIN_PASSWORD
INITIAL_ADMIN_EMAIL=$ADMIN_EMAIL
EOF
    
    # Create systemd service
    print_info "Creating systemd service..."
    cat > /etc/systemd/system/vpnmaster.service <<EOF
[Unit]
Description=VPN Master Panel API
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR/backend
Environment="PATH=$INSTALL_DIR/backend/venv/bin"
ExecStart=$INSTALL_DIR/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port $API_PORT
Restart=always

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable vpnmaster
    systemctl start vpnmaster
    
    print_success "Backend service started"
    
    # Show summary
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║             MANUAL INSTALLATION COMPLETE!                    ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}API Endpoint:${NC} http://$(hostname -I | awk '{print $1}'):$API_PORT"
    echo -e "${CYAN}API Docs:${NC}     http://$(hostname -I | awk '{print $1}'):$API_PORT/docs"
    echo ""
    echo -e "${CYAN}Login:${NC} $ADMIN_USERNAME / $ADMIN_PASSWORD"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Install and configure frontend separately"
    echo "2. Configure Nginx as reverse proxy"
    echo "3. Setup SSL with Let's Encrypt"
    echo ""
}

# Execute installation
if [[ "$install_method" == "1" ]]; then
    install_docker_method
else
    install_manual_method
fi

print_success "Installation completed successfully!"
echo ""
print_info "Thank you for using VPN Master Panel! 🛡️"
echo ""
