"""
SQLAlchemy models for AFDFBorderBot database.
"""

from sqlalchemy import Column, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class BotSetting(Base):
    """Bot settings model."""
    __tablename__ = 'bot_settings'
    
    setting_key = Column(Text, primary_key=True)
    setting_value = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
