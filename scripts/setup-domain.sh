#!/bin/bash

###############################################################################
#  Domain & SSL Setup Script
#  Automatic SSL certificate with Let's Encrypt
###############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}VPN Master Panel - Domain & SSL Setup${NC}\n"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}" 
   exit 1
fi

# Get domain from user
read -p "Enter your domain name (e.g., vpn.example.com): " DOMAIN

if [ -z "$DOMAIN" ]; then
    echo -e "${RED}Domain name is required${NC}"
    exit 1
fi

# Get email for Let's Encrypt
read -p "Enter your email for SSL certificate: " EMAIL

if [ -z "$EMAIL" ]; then
    echo -e "${RED}Email is required${NC}"
    exit 1
fi

echo -e "\n${YELLOW}Installing Certbot...${NC}"
apt update -qq
apt install -y certbot python3-certbot-nginx

echo -e "\n${YELLOW}Obtaining SSL certificate...${NC}"
certbot --nginx -d $DOMAIN --email $EMAIL --agree-tos --non-interactive

echo -e "\n${YELLOW}Configuring Nginx for SSL...${NC}"

# Create SSL configuration
cat > /etc/nginx/sites-available/vpnmaster-ssl << EOF
# HTTPS Frontend
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name $DOMAIN;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Frontend
    root /opt/vpn-master-panel/frontend/dist;
    index index.html;

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript;

    # Cache static files
    location ~* \\.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # API proxy
    location /api {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # WebSocket proxy
    location /ws {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    # SPA fallback
    location / {
        try_files \$uri \$uri/ /index.html;
    }
}

# HTTP to HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;
    return 301 https://\$server_name\$request_uri;
}
EOF

# Enable SSL configuration
ln -sf /etc/nginx/sites-available/vpnmaster-ssl /etc/nginx/sites-enabled/

# Test nginx configuration
nginx -t

# Reload nginx
systemctl reload nginx

echo -e "\n${GREEN}✅ SSL certificate installed successfully!${NC}"
echo -e "\n${YELLOW}Your panel is now accessible at:${NC}"
echo -e "${GREEN}https://$DOMAIN${NC}"

echo -e "\n${YELLOW}Setting up auto-renewal...${NC}"

# Create renewal script
cat > /opt/vpn-master-panel/scripts/renew-ssl.sh << 'EOF'
#!/bin/bash
certbot renew --quiet
systemctl reload nginx
EOF

chmod +x /opt/vpn-master-panel/scripts/renew-ssl.sh

# Create systemd timer for auto-renewal
cat > /etc/systemd/system/certbot-renew.service << EOF
[Unit]
Description=Certbot Renewal

[Service]
Type=oneshot
ExecStart=/opt/vpn-master-panel/scripts/renew-ssl.sh
EOF

cat > /etc/systemd/system/certbot-renew.timer << EOF
[Unit]
Description=Certbot Renewal Timer

[Timer]
OnCalendar=daily
RandomizedDelaySec=1h
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Enable and start timer
systemctl daemon-reload
systemctl enable certbot-renew.timer
systemctl start certbot-renew.timer

echo -e "\n${GREEN}✅ Auto-renewal configured!${NC}"
echo -e "${YELLOW}Certificate will auto-renew every 60 days${NC}"

echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "\n${YELLOW}Access your panel:${NC} ${GREEN}https://$DOMAIN${NC}"
echo -e "${YELLOW}Certificate expires:${NC} $(certbot certificates | grep 'Expiry Date' | head -1)"
echo -e "${YELLOW}Auto-renewal:${NC} ${GREEN}Enabled${NC}"
