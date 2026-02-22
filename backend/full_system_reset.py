
import os
import shutil
import subprocess
import sys
import datetime
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "openvpn")
SERVER_CONF = "/etc/openvpn/server.conf"

def run_cmd(cmd, check=True):
    print(f"👉 Running: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=check)
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")
        if check:
            raise e

def generate_key():
    """Generate a private key."""
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

def save_key(key, path):
    """Save private key to file (Unencrypted)."""
    with open(path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption() # CRITICAL: No Password
        ))
    os.chmod(path, 0o600)

def save_cert(cert, path):
    """Save certificate to file."""
    with open(path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    os.chmod(path, 0o644)

def main():
    if os.geteuid() != 0:
        print("❌ Must run as root!")
        sys.exit(1)

    print("🚀 Starting Full System Reset (OpenVPN Fix)...")

    # 1. Stop Services
    print("🛑 Stopping services...")
    run_cmd(["systemctl", "stop", "openvpn@server"], check=False)
    run_cmd(["systemctl", "stop", "openvpn"], check=False)
    
    # 2. Backup
    if os.path.exists(DATA_DIR):
        backup_path = f"{DATA_DIR}_backup_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        print(f"💾 Backing up {DATA_DIR} to {backup_path}...")
        shutil.copytree(DATA_DIR, backup_path)
    
    # 3. Wipe PKI (Force Clean Slate)
    print("🧹 Wiping old PKI...")
    if os.path.exists(DATA_DIR):
        shutil.rmtree(DATA_DIR)
    os.makedirs(DATA_DIR, mode=0o755)

    # 4. Generate New PKI (Pure Python)
    print("🔐 Generating New PKI (Python Cryptography)...")
    
    # CA
    print("  - Generating CA...")
    ca_key = generate_key()
    ca_subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"VPN-Master-Root-CA"),
    ])
    ca_cert = x509.CertificateBuilder().subject_name(
        ca_subject
    ).issuer_name(
        ca_subject
    ).public_key(
        ca_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=3650)
    ).add_extension(
        x509.BasicConstraints(ca=True, path_length=None), critical=True,
    ).sign(ca_key, hashes.SHA256(), default_backend())

    save_key(ca_key, os.path.join(DATA_DIR, "ca.key"))
    save_cert(ca_cert, os.path.join(DATA_DIR, "ca.crt"))

    # Server Key/Cert
    print("  - Generating Server Key & Cert...")
    server_key = generate_key()
    server_subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"server"),
    ])
    server_cert = x509.CertificateBuilder().subject_name(
        server_subject
    ).issuer_name(
        ca_subject
    ).public_key(
        server_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=3650)
    ).add_extension(
        x509.BasicConstraints(ca=False, path_length=None), critical=True,
    ).add_extension(
        x509.KeyUsage(
            digital_signature=True,
            content_commitment=False,
            key_encipherment=True,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=False,
            crl_sign=False,
            encipher_only=False,
            decipher_only=False
        ), critical=True
    ).add_extension(
        x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=True
    ).sign(ca_key, hashes.SHA256(), default_backend()) # Sign with CA Key!

    save_key(server_key, os.path.join(DATA_DIR, "server.key"))
    save_cert(server_cert, os.path.join(DATA_DIR, "server.crt"))

    # DH Params (Fast)
    print("  - Generating DH Params (Using OpenSSL for speed)...")
    run_cmd(["openssl", "dhparam", "-out", os.path.join(DATA_DIR, "dh.pem"), "2048"])

    # TA Key
    print("  - Generating TA Key...")
    run_cmd(["openvpn", "--genkey", "secret", os.path.join(DATA_DIR, "ta.key")])
    os.chmod(os.path.join(DATA_DIR, "ta.key"), 0o600)

    # 5. Deploy Keys to /etc/openvpn
    print("📂 Deploying keys to /etc/openvpn...")
    if not os.path.exists("/etc/openvpn"):
        os.makedirs("/etc/openvpn")
    
    for f in ["ca.crt", "server.crt", "server.key", "ta.key", "dh.pem"]:
        src = os.path.join(DATA_DIR, f)
        dst = os.path.join("/etc/openvpn", f)
        shutil.copy2(src, dst)
        # Mirror permissions
        if f.endswith(".key"):
            os.chmod(dst, 0o600)
        else:
            os.chmod(dst, 0o644)

    # 6. Fix Auth Script
    print("🔧 Fixing Auth Script...")
    auth_src = os.path.join(BASE_DIR, "auth.py")
    auth_dst = "/etc/openvpn/scripts/auth.py"
    if not os.path.exists("/etc/openvpn/scripts"):
        os.makedirs("/etc/openvpn/scripts")
    
    if os.path.exists(auth_src):
        shutil.copy2(auth_src, auth_dst)
        os.chmod(auth_dst, 0o755)
        print("  - Auth script deployed.")
    else:
        print(f"⚠️ Warning: {auth_src} not found!")

    # 7. Patch Server Config
    print("🔧 Patching server.conf...")
    if os.path.exists(SERVER_CONF):
        with open(SERVER_CONF, "r") as f:
            conf = f.read()
        
        # Ensure correct auth path
        new_conf = conf.replace("/opt/vpn-master-panel/backend/auth.py", "/etc/openvpn/scripts/auth.py")
        
        if new_conf != conf:
            with open(SERVER_CONF, "w") as f:
                f.write(new_conf)
            print("  - server.conf patched.")
    
    # 8. Restart
    print("🔄 Restarting Services...")
    run_cmd(["systemctl", "daemon-reload"])
    run_cmd(["systemctl", "start", "openvpn@server"])
    
    # Check
    print("🔍 Verify...")
    try:
        subprocess.run(["systemctl", "is-active", "--quiet", "openvpn@server"], check=True)
        print("✅ OpenVPN is RUNNING!")
    except:
        print("❌ OpenVPN failed to start. Check logs.")
        run_cmd(["journalctl", "-u", "openvpn@server", "-n", "20", "--no-pager"], check=False)

if __name__ == "__main__":
    main()
