
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.openvpn import openvpn_service

print("Regenerating PKI...")
try:
    openvpn_service.regenerate_pki()
    print("PKI Regenerated.")
    
    # Check ca.crt content
    with open(openvpn_service.CA_PATH, 'r') as f:
        content = f.read()
        
    print(f"CA Path: {openvpn_service.CA_PATH}")
    if "BEGIN PRIVATE KEY" in content:
        print("❌ FAILURE: Private key found in CA Certificate!")
    else:
        print("✅ SUCCESS: CA Certificate is clean (No private key).")
        
    if "BEGIN CERTIFICATE" in content:
        print("✅ SUCCESS: Certificate block found.")
    else:
        print("❌ FAILURE: Certificate block missing!")
        
except Exception as e:
    print(f"❌ Error: {e}")
