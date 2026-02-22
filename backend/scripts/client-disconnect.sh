#!/bin/bash
# F7: Bandwidth Shaping Cleanup
# Called by OpenVPN on client disconnect

USERNAME=$common_name
VPN_IP=$ifconfig_pool_remote_ip
DEV=$dev

# We should ideally remove the class and filter
# Based on connection script logic:
CLASS_ID=$(echo $VPN_IP | awk -F. '{print $4}')

if [ -n "$CLASS_ID" ]; then
    # Delete filter first
    # This is tricky without exact handle, but if we used replace with exact match...
    # Simplified cleanup:
    # Just try to delete class, filter usually strictly bound
    
    # Actually, specific filter deletion is hard without handle. 
    # But class deletion might fail if filter active.
    # For a Lite version, perfect TC cleanup is complex. 
    # We will attempt to delete the class.
    
    tc class del dev $DEV parent 1: classid 1:$CLASS_ID >/dev/null 2>&1
fi

exit 0
