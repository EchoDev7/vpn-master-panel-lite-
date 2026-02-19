import sys
import logging
logging.basicConfig(level=logging.DEBUG)

sys.path.append("/Users/majlotfi/.gemini/antigravity/playground/radiant-kuiper/vpn-master-panel-lite/backend")
try:
    from app.services.openvpn import OpenVPNService
    svc = OpenVPNService()
    print("IP:", svc._get_public_ip())
except Exception as e:
    print("ERROR:", e)
