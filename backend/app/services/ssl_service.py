import os
import subprocess
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class SSLService:
    def __init__(self):
        self.nginx_conf_dir = "/etc/nginx/sites-available"
        self.certbot_path = "/usr/bin/certbot"
        
    def _run_cmd(self, cmd: str) -> Tuple[bool, str]:
        try:
            result = subprocess.run(
                cmd, shell=True, check=True, 
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {cmd}\nError: {e.stderr}")
            return False, e.stderr

    def issue_letsencrypt_cert(self, domain: str, email: str) -> Tuple[bool, str]:
        """
        Request a Let's Encrypt certificate using certbot webroot or standalone plugin.
        Assumes Nginx is installed and running on port 80 for challenges.
        """
        if not domain or not email:
            return False, "Domain and email are required."
            
        # 1. Ensure certbot is installed
        if not os.path.exists(self.certbot_path):
             # Try falling back to simply 'certbot'
             self.certbot_path = "certbot"
            
        logger.info(f"Requesting SSL for {domain} with email {email}")
        
        # We use the nginx plugin if available, otherwise webroot.
        # Assuming the standard VPN Master Panel Nginx setup
        cmd = (
            f"{self.certbot_path} certonly --non-interactive --agree-tos "
            f"-m {email} -d {domain} --nginx"
        )
        
        success, output = self._run_cmd(cmd)
        
        if success:
             # Verify certs exist
             cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
             if os.path.exists(cert_path):
                 return True, f"SSL Certificate successfully issued for {domain}."
             else:
                 return False, f"Certbot reported success, but cert files not found at {cert_path}"
                 
        # If Nginx plugin failed, it might be due to missing server block. 
        # Fallback to standalone (requires killing Nginx temporarily)
        logger.info("Nginx plugin failed, attempting standalone fallback...")
        self._run_cmd("systemctl stop nginx")
        
        cmd_fallback = (
            f"{self.certbot_path} certonly --standalone --non-interactive --agree-tos "
            f"-m {email} -d {domain}"
        )
        success_fb, output_fb = self._run_cmd(cmd_fallback)
        
        self._run_cmd("systemctl start nginx") # Restart regardless
        
        if success_fb:
             return True, f"SSL Certificate successfully issued for {domain} (Standalone fallback)."
        else:
             return False, f"Certbot request failed. Is port 80 open and domain pointed to IP? \nLogs: {output_fb}"
