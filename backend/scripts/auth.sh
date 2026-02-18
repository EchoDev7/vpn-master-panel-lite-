#!/bin/bash
# Wrapper to run auth.py with the correct virtual environment
# OpenVPN passes the password file as the first argument

LOG_FILE="/var/log/openvpn/auth_wrapper.log"
# exec >> "$LOG_FILE" 2>&1
# echo "$(date) Auth wrapper called with args: $@"

/opt/vpn-master-panel/backend/venv/bin/python /etc/openvpn/scripts/auth.py "$@"
exit $?
