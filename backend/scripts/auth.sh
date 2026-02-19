#!/bin/bash
# Wrapper to run auth.py with the correct virtual environment
# OpenVPN passes the password file as the first argument

LOG_FILE="/var/log/openvpn/auth_wrapper.log"
exec >> "$LOG_FILE" 2>&1
echo "========== $(date) =========="
echo "Auth wrapper called with args: $@"

# Ensure the log file is writable by the openvpn user (nobody/nogroup usually)
# But this script runs as root usually due to openvpn dropping privs later or script-security
# checking permissions...

/opt/vpn-master-panel/backend/venv/bin/python /etc/openvpn/scripts/auth.py "$@"
EXIT_CODE=$?
echo "Python script exited with code: $EXIT_CODE"
exit $EXIT_CODE
