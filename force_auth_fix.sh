#!/bin/bash
# Force fix auth settings in server.conf

CONF="/etc/openvpn/server.conf"

echo "Backing up server.conf..."
cp $CONF $CONF.bak

echo "Removing old auth directives..."
sed -i '/auth-user-pass-verify/d' $CONF
sed -i '/script-security/d' $CONF

echo "Injecting new auth settings..."
echo "script-security 2" >> $CONF
echo "auth-user-pass-verify /etc/openvpn/scripts/auth.sh via-file" >> $CONF

echo "Restarting OpenVPN..."
systemctl restart openvpn@server
systemctl status openvpn@server --no-pager
