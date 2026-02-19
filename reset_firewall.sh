#!/bin/bash
# Reset UFW and Force NAT

echo "Resetting UFW..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing

echo "Allowing SSH and VPN ports..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8000/tcp
ufw allow 3000/tcp
ufw allow 1194/udp
ufw allow 51820/udp

echo "Enabling Forwarding..."
sed -i 's/DEFAULT_FORWARD_POLICY="DROP"/DEFAULT_FORWARD_POLICY="ACCEPT"/g' /etc/default/ufw
sed -i 's/DEFAULT_FORWARD_POLICY="REJECT"/DEFAULT_FORWARD_POLICY="ACCEPT"/g' /etc/default/ufw
sysctl -w net.ipv4.ip_forward=1

echo "Applying NAT Rules..."
MAIN_IFACE=$(ip route | grep '^default' | awk '{print $5}' | head -n1)
echo "Main Interface: $MAIN_IFACE"

# Append NAT rules to before.rules if missing
if ! grep -q "*nat" /etc/ufw/before.rules; then
    cat <<EOT >> /etc/ufw/before.rules

# NAT table rules
*nat
:POSTROUTING ACCEPT [0:0]
-A POSTROUTING -s 10.8.0.0/8 -o $MAIN_IFACE -j MASQUERADE
COMMIT
EOT
    echo "NAT rules appended."
else
    echo "NAT rules already exist."
fi

echo "Enabling UFW..."
ufw --force enable
ufw status verbose
