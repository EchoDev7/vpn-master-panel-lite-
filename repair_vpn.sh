#!/bin/bash

# Define Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

DATA_DIR="/opt/vpn-master-panel/backend/data/openvpn"
SERVER_CONF="/etc/openvpn/server.conf"

echo -e "${YELLOW}🚀 Starting Emergency VPN Repair...${NC}"

# 1. Stop Services
echo -e "${YELLOW}🛑 Stopping OpenVPN...${NC}"
systemctl stop openvpn@server
systemctl stop openvpn

# 2. Backup Existing Config/Data (Just in case)
echo -e "${YELLOW}💾 Backing up existing data...${NC}"
cp -r $DATA_DIR "${DATA_DIR}_backup_$(date +%s)"
cp $SERVER_CONF "${SERVER_CONF}.bak"

# 3. Clean Old Keys (Force Fresh Start)
echo -e "${YELLOW}🧹 Cleaning old certificates...${NC}"
rm -f $DATA_DIR/ca.crt $DATA_DIR/ca.key
rm -f $DATA_DIR/server.crt $DATA_DIR/server.key $DATA_DIR/server.csr
rm -f $DATA_DIR/ta.key $DATA_DIR/dh.pem

# 4. Generate New PKI (Manual OpenSSL)
echo -e "${GREEN}🔐 Generating New CA...${NC}"
openssl req -new -x509 -days 3650 -nodes \
    -out $DATA_DIR/ca.crt \
    -keyout $DATA_DIR/ca.key \
    -subj "/CN=VPN-Master-CA" 2>/dev/null

echo -e "${GREEN}🔐 Generating Server Key & CSR...${NC}"
openssl req -new -nodes \
    -out $DATA_DIR/server.csr \
    -keyout $DATA_DIR/server.key \
    -subj "/CN=server" 2>/dev/null

# Create Extensions File for Server Auth
cat > $DATA_DIR/server.ext << EOF
basicConstraints=CA:FALSE
nsCertType=server
keyUsage=digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid,issuer
EOF

echo -e "${GREEN}🔐 Signing Server Certificate...${NC}"
openssl x509 -req \
    -in $DATA_DIR/server.csr \
    -CA $DATA_DIR/ca.crt \
    -CAkey $DATA_DIR/ca.key \
    -CAcreateserial \
    -out $DATA_DIR/server.crt \
    -days 3650 \
    -extfile $DATA_DIR/server.ext 2>/dev/null

echo -e "${GREEN}🔐 Generating DH Parameters (Fast)...${NC}"
openssl dhparam -out $DATA_DIR/dh.pem 2048 2>/dev/null

echo -e "${GREEN}🔐 Generating TLS-Auth Key...${NC}"
openvpn --genkey secret $DATA_DIR/ta.key

# 5. Fix Permissions
echo -e "${YELLOW}🛡️  Setting Permissions...${NC}"
chmod 600 $DATA_DIR/server.key $DATA_DIR/ta.key $DATA_DIR/ca.key
chmod 644 $DATA_DIR/ca.crt $DATA_DIR/server.crt $DATA_DIR/dh.pem

# 6. Verify Modulus Match
MOD_CRT=$(openssl x509 -noout -modulus -in $DATA_DIR/server.crt | openssl md5)
MOD_KEY=$(openssl rsa -noout -modulus -in $DATA_DIR/server.key | openssl md5)

if [ "$MOD_CRT" == "$MOD_KEY" ]; then
    echo -e "${GREEN}✅ Certificate and Key Modulus MATCH!${NC}"
else
    echo -e "${RED}❌ FATAL: Certificate and Key Modulus MISMATCH! Fix failed.${NC}"
    exit 1
fi

# 7. Ensure Auth Script (Double Check)
mkdir -p /etc/openvpn/scripts
if [ -f "/opt/vpn-master-panel/backend/auth.py" ]; then
    cp /opt/vpn-master-panel/backend/auth.py /etc/openvpn/scripts/auth.py
    chmod +x /etc/openvpn/scripts/auth.py
    echo -e "${GREEN}✅ Auth script updated.${NC}"
fi

# 8. Start Service
echo -e "${GREEN}🔄 Restarting OpenVPN...${NC}"
systemctl start openvpn@server

# Check status
if systemctl is-active --quiet openvpn@server; then
     echo -e "${GREEN}✅ OpenVPN Service is RUNNING!${NC}"
else
     echo -e "${RED}❌ OpenVPN Service failed to start. Check logs.${NC}"
     journalctl -u openvpn@server -n 20 --no-pager
fi
