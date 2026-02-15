"""
VPN Master Panel - Configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # App Info
    APP_NAME: str = "VPN Master Panel"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_PORT: int = 8000  # Alias for PORT
    WEB_PORT: int = 3000  # Frontend port
    
    # VPN Ports
    OPENVPN_PORT: int = 1194
    WIREGUARD_PORT: int = 51820
    L2TP_PSK: str = "vpnmaster"
    CISCO_PORT: int = 4443
    
    # Security
    SECRET_KEY: str = "CHANGE_THIS_IN_PRODUCTION_USE_OPENSSL_RAND_HEX_32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # Database
    DATABASE_URL: str = "postgresql://vpnmaster:vpnmaster@postgres:5432/vpnmaster"
    DATABASE_ECHO: bool = False
    
    # SQLite fallback
    SQLITE_URL: str = "sqlite:///./vpnmaster.db"
    USE_SQLITE: bool = False
    
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    REDIS_PASSWORD: Optional[str] = None
    
    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"
    
    # Monitoring
    PROMETHEUS_ENABLED: bool = True
    GRAFANA_ENABLED: bool = False
    
    # VPN Service Paths
    OPENVPN_CONFIG_DIR: str = "/etc/openvpn/server"
    WIREGUARD_CONFIG_DIR: str = "/etc/wireguard"
    L2TP_CONFIG_DIR: str = "/etc/xl2tpd"
    CISCO_CONFIG_DIR: str = "/etc/ocserv"
    
    # Tunnel Settings
    TUNNEL_HEALTH_CHECK_INTERVAL: int = 60  # seconds
    TUNNEL_RECONNECT_ATTEMPTS: int = 3
    TUNNEL_TIMEOUT: int = 30
    
    # Traffic Monitoring
    TRAFFIC_UPDATE_INTERVAL: int = 5  # seconds
    TRAFFIC_RETENTION_DAYS: int = 30
    
    # Iran Bypass Features
    IRAN_BYPASS_ENABLED: bool = True
    DOMAIN_FRONTING_ENABLED: bool = True
    TLS_OBFUSCATION_ENABLED: bool = True
    AUTO_SWITCH_ON_BLOCK: bool = True
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "/var/log/vpnmaster/app.log"
    
    # Admin
    INITIAL_ADMIN_USERNAME: str = "admin"
    INITIAL_ADMIN_PASSWORD: str = "admin"
    INITIAL_ADMIN_EMAIL: str = "admin@vpnmaster.local"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields from .env file


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
