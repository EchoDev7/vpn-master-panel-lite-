
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
    
    # Check for unwanted directives (Legacy/Incompatible)
    if "sni-spoof" in config_content:
        print("❌ FAILURE: sni-spoof directive found (Should be removed).")
        sys.exit(1)

    if "block-outside-dns" in config_content:
        print("❌ FAILURE: block-outside-dns found! This breaks mobile clients.")
        sys.exit(1)

    # Check for Correct Server IP
    if "remote 89.167.0.72" not in config_content:
        print("❌ FAILURE: Config points to WRONG IP (Expected 89.167.0.72).")
        # Extract what it points to
        import re
        match = re.search(r"remote\s+([\d\.]+)", config_content)
        if match:
            print(f"   Found: remote {match.group(1)}")
        sys.exit(1)

    
    # Check for clean directives
    if "scramble obfuscate" in config_content:
        # Check if Enabled in settings. Default is enabled in OPENVPN_DEFAULTS.
        # We assume defaults.
        print("ℹ️  Scramble directive present (Default ON).")
        
    print("✅ Verification Complete. Config is Clean.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
