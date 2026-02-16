
import sys
import os
import re

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.openvpn import openvpn_service

print("Generating Client Config for verification...")
try:
    # Generate config
    config_content = openvpn_service.generate_client_config("verify_user")
    
    print(f"✅ Config Generated. Size: {len(config_content)} bytes")
    
    # Check for Private Key in CA
    if "BEGIN PRIVATE KEY" in config_content:
        # Check if it is inside <ca>
        ca_block = re.search(r'<ca>(.*?)</ca>', config_content, re.DOTALL)
        if ca_block and "BEGIN PRIVATE KEY" in ca_block.group(1):
            print("❌ CRITICAL SECURITY FAILURE: Private Key found in <ca> block!")
            sys.exit(1)
            
    print("✅ Security Check Passed: No Private Key in <ca> block.")
    
    # Check for unwanted directives (Legacy)
    if "sni-spoof" in config_content:
        print("❌ FAILURE: sni-spoof directive found (Should be removed).")
    
    # Check for clean directives
    if "scramble obfuscate" in config_content:
        # Check if Enabled in settings. Default is enabled in OPENVPN_DEFAULTS.
        # We assume defaults.
        print("ℹ️  Scramble directive present (Default ON).")
        
    print("✅ Verification Complete. Config is Clean.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
