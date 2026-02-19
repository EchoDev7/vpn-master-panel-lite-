#!/bin/bash
# Force Configure UFW for NAT

echo "Checking UFW NAT configuration..."

# 1. Enable Forwarding
sed -i 's/DEFAULT_FORWARD_POLICY="DROP"/DEFAULT_FORWARD_POLICY="ACCEPT"/g' /etc/default/ufw
sed -i 's/DEFAULT_FORWARD_POLICY="REJECT"/DEFAULT_FORWARD_POLICY="ACCEPT"/g' /etc/default/ufw

# 2. Add NAT rules
MAIN_IFACE=$(ip route | grep '^default' | awk '{print $5}' | head -n1)
echo "Main Interface: $MAIN_IFACE"

if ! grep -q "*nat" /etc/ufw/before.rules; then
    echo "Injecting NAT rules..."
    
    cat <<EOT > /tmp/nat_rules
*nat
:POSTROUTING ACCEPT [0:0]
-A POSTROUTING -s 10.8.0.0/8 -o $MAIN_IFACE -j MASQUERADE
COMMIT
EOT
    
    # Prepend to file
    cat /etc/ufw/before.rules >> /tmp/nat_rules
    # Wait, the logic above in update.sh was slightly risky with cat/mv order.
    # Let's do it safer here: read original, prepend new.
    cat /tmp/nat_rules /etc/ufw/before.rules > /etc/ufw/before.rules.new
    mv /etc/ufw/before.rules.new /etc/ufw/before.rules
    
    echo "NAT rules added."
else
    echo "NAT rules already present."
fi

echo "Reloading UFW..."
ufw disable
ufw enable
