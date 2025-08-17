"""
Simple database-backed settings manager using SQLAlchemy.
"""

import logging
import asyncio
from typing import Any, Dict
from datetime import datetime

from sqlalchemy.future import select

from .db_manager import get_db_manager
from .models import BotSetting

logger = logging.getLogger(__name__)


class SettingsManager:
    """Simple settings manager with database persistence."""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_loaded = False
    
    async def _load_cache(self):
        """Load all settings from database using SQLAlchemy ORM."""
        try:
            db = await get_db_manager()
            async with db.get_session() as session:
                result = await session.execute(select(BotSetting))
                settings = result.scalars().all()
                
                for setting in settings:
                    # JSONB field handles JSON automatically, no manual parsing needed
                    self._cache[setting.setting_key] = setting.setting_value
                    
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
    
    async def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self._cache.get(key, default)
    
    async def update_setting(self, key: str, value: Any) -> bool:
        """Update a setting value using SQLAlchemy ORM with optimized upsert."""
        try:
            db = await get_db_manager()
            
            async with db.get_session() as session:
                # Try to find existing setting
                result = await session.execute(
                    select(BotSetting).where(BotSetting.setting_key == key)
                )
                existing_setting = result.scalar_one_or_none()
                
                if existing_setting:
                    # Update existing setting
                    existing_setting.setting_value = value
                    existing_setting.updated_at = datetime.utcnow()
                else:
                    # Create new setting
                    new_setting = BotSetting(
                        setting_key=key,
                        setting_value=value,
                        updated_at=datetime.utcnow()
                    )
                    session.add(new_setting)
                
                await session.commit()
            
            # Update cache
            self._cache[key] = value
            return True
            
        except Exception as e:
            logger.error(f"Failed to update setting '{key}': {e}")
            return False
    
    async def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings."""
        return self._cache.copy()


# Global instance
_manager = SettingsManager()

async def get_setting(key: str, default: Any = None) -> Any:
    """Get a setting value."""
    return await _manager.get_setting(key, default)

async def update_setting(key: str, value: Any) -> bool:
    """Update a setting value."""
    return await _manager.update_setting(key, value)

async def get_all_settings() -> Dict[str, Any]:
    """Get all settings."""
    return await _manager.get_all_settings()

async def get_settings_manager() -> SettingsManager:
    """Get the global settings manager instance."""
    return _manager
