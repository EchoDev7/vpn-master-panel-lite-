import os
import sys
import logging
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("fix_pki")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "openvpn")
CA_PATH = os.path.join(DATA_DIR, "ca.crt")
CA_KEY_PATH = os.path.join(DATA_DIR, "ca.key")
SERVER_CERT_PATH = os.path.join(DATA_DIR, "server.crt")
SERVER_KEY_PATH = os.path.join(DATA_DIR, "server.key")
TA_PATH = os.path.join(DATA_DIR, "ta.key")

def generate_private_key():
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

def save_key(key, path):
    logger.info(f"Saving key to {path}...")
    with open(path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    os.chmod(path, 0o600)

def save_cert(cert, path):
    logger.info(f"Saving cert to {path}...")
    with open(path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

def generate_self_signed_ca(key):
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"VPN-Master-Root-CA"),
    ])
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=3650)
    ).add_extension(
        x509.BasicConstraints(ca=True, path_length=None), critical=True,
    ).sign(key, hashes.SHA256(), default_backend())
    return cert

def generate_server_cert(ca_cert, ca_key, server_key):
    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"VPN-Master-Server"),
    ])
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        ca_cert.subject
    ).public_key(
        server_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=3650)
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
         x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]), critical=True
    ).sign(ca_key, hashes.SHA256(), default_backend())
    return cert

def generate_tls_auth_key(path):
    import secrets
    logger.info(f"Generating TLS key to {path}...")
    key_data = secrets.token_bytes(256)
    hex_data = key_data.hex()
    content = "-----BEGIN OpenVPN Static key V1-----\n"
    for i in range(0, len(hex_data), 32):
        content += hex_data[i:i+32] + "\n"
    content += "-----END OpenVPN Static key V1-----\n"
    with open(path, "w") as f:
        f.write(content)
    os.chmod(path, 0o600)

def main():
    print("🚀 Starting Standalone PKI Regeneration...")
    
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"Created directory: {DATA_DIR}")

    try:
        # CA
        print("Generating CA...")
        ca_key = generate_private_key()
        ca_cert = generate_self_signed_ca(ca_key)
        save_key(ca_key, CA_KEY_PATH)
        save_cert(ca_cert, CA_PATH)

        # Server
        print("Generating Server Key/Cert...")
        server_key = generate_private_key()
        server_cert = generate_server_cert(ca_cert, ca_key, server_key)
        save_key(server_key, SERVER_KEY_PATH)
        save_cert(server_cert, SERVER_CERT_PATH)

        # TLS
        print("Generating TLS Key...")
        generate_tls_auth_key(TA_PATH)
        
        print("\n✅ PKI Generation Complete!")
        print(f"Files created in {DATA_DIR}")
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
