"""
SQLAlchemy models for AFDFBorderBot database.
"""

from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, DateTime, Date, Text, ARRAY
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


class LOARequest(Base):
    """LOA request model."""
    __tablename__ = 'loa_requests'
    
    id = Column(Integer, primary_key=True)
    discord_id = Column(Text, nullable=False)
    username = Column(Text, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Text, nullable=False)
    reason = Column(Text)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    last_modified = Column(DateTime, default=datetime.utcnow)
    status = Column(Text, default='active')
    created_at = Column(DateTime, default=datetime.utcnow)


class TransactionLog(Base):
    """Transaction log model."""
    __tablename__ = 'transaction_log'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    from_user_id = Column(Text)
    to_user_id = Column(Text)
    amount = Column(DECIMAL(15, 2), nullable=False)
    transaction_type = Column(Text, nullable=False)
    description = Column(Text)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
