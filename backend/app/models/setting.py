"""
Settings Model - Dynamic system configuration
"""
from sqlalchemy import Column, String, Text
from ..database import Base

class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(Text, nullable=True)
    description = Column(String, nullable=True)
    category = Column(String, default="general") # general, openvpn, wireguard, security

    def __repr__(self):
        return f"<Setting {self.key}={self.value}>"
