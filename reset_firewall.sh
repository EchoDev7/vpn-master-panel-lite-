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

# Allow VPN Interface Traffic
echo "Allowing tun0 traffic..."
ufw allow in on tun0
ufw allow out on tun0

# Allow Forwarding (Explicitly)
echo "Allowing Forwarding..."
ufw route allow in on tun0 out on $MAIN_IFACE
ufw route allow in on $MAIN_IFACE out on tun0

echo "Applying NAT Rules..."
# Append NAT rules to before.rules if missing
if ! grep -q "*nat" /etc/ufw/before.rules; then
    cat <<EOT >> /etc/ufw/before.rules

# NAT table rules
*nat
:POSTROUTING ACCEPT [0:0]
# Use /24 for the default OpenVPN subnet
-A POSTROUTING -s 10.8.0.0/24 -o $MAIN_IFACE -j MASQUERADE
COMMIT
EOT
    echo "NAT rules appended."
else
    echo "NAT rules already exist."
    # Fix potential CIDR issues in existing rules if necessary (optional)
fi

echo "Enabling UFW..."
ufw --force enable
ufw status verbose
