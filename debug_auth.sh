#!/bin/bash
# Test script to debug auth.sh execution manually

USER_NAME="testuser"
USER_PASS="testpass"

echo "Creating temporary auth file..."
echo "$USER_NAME" > /tmp/auth_test_creds
echo "$USER_PASS" >> /tmp/auth_test_creds

echo "Running auth.sh manually..."
export untrusted_ip="1.2.3.4"
/etc/openvpn/scripts/auth.sh /tmp/auth_test_creds

EXIT_CODE=$?
echo "Auth script exit code: $EXIT_CODE"

echo "Checking wrapper log:"
tail -n 20 /var/log/openvpn/auth_wrapper.log

echo "Checking python auth log:"
tail -n 20 /var/log/openvpn/auth.log

rm /tmp/auth_test_creds
