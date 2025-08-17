"""
Database-backed Settings Manager for AFDFBorderBot

Provides centralized settings management using PostgreSQL.
"""

import json
import logging
from typing import Any, Optional, Dict
from .db_manager import get_db_manager

logger = logging.getLogger(__name__)

class SettingsManager:
    """Database-backed settings manager."""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_loaded = False
    
    async def _ensure_cache_loaded(self):
        """Ensure settings cache is loaded from database."""
        if not self._cache_loaded:
            await self._load_cache()
    
    async def _load_cache(self):
        """Load all settings from database into cache."""
        try:
            db = await get_db_manager()
            query = "SELECT setting_key, setting_value FROM bot_settings"
            results = await db.execute_select_query(query)
            
            self._cache = {}
            for row in results:
                # setting_value is stored as JSONB, so we need to parse it
                key = row['setting_key']
                value = row['setting_value']
                # If it's a boolean stored as JSON, convert it
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        pass
                elif isinstance(value, bool):
                    pass  # Already a boolean
                else:
                    # For other JSON values, keep as-is
                    pass
                
                self._cache[key] = value
            
            self._cache_loaded = True
            logger.info(f"Loaded {len(self._cache)} settings from database")
            
        except Exception as e:
            logger.error(f"Failed to load settings cache: {e}")
            # Fallback to empty cache
            self._cache = {}
            self._cache_loaded = True
    
    async def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        await self._ensure_cache_loaded()
        return self._cache.get(key, default)
    
    async def update_setting(self, key: str, value: Any) -> bool:
        """Update a setting value in database and cache."""
        try:
            db = await get_db_manager()
            
            # Convert value to JSON for storage
            json_value = json.dumps(value)
            
            # Use UPSERT (INSERT ... ON CONFLICT) to handle both new and existing settings
            query = """
                INSERT INTO bot_settings (setting_key, setting_value, updated_at) 
                VALUES (:key, :value, CURRENT_TIMESTAMP)
                ON CONFLICT (setting_key) 
                DO UPDATE SET 
                    setting_value = EXCLUDED.setting_value,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            await db.execute_dml_query(query, {"key": key, "value": json_value})
            
            # Update cache
            self._cache[key] = value
            
            logger.info(f"Updated setting '{key}' to '{value}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update setting '{key}': {e}")
            return False
    
    async def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings as a dictionary."""
        await self._ensure_cache_loaded()
        return self._cache.copy()
    
    async def reload_cache(self):
        """Force reload settings cache from database."""
        self._cache_loaded = False
        await self._load_cache()

# Global settings manager instance
_settings_manager: Optional[SettingsManager] = None

async def get_settings_manager() -> SettingsManager:
    """Get the global settings manager instance."""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager

# Convenience functions for backward compatibility
async def get_setting(key: str, default: Any = None) -> Any:
    """Get a setting value."""
    manager = await get_settings_manager()
    return await manager.get_setting(key, default)

async def update_setting(key: str, value: Any) -> bool:
    """Update a setting value."""
    manager = await get_settings_manager()
    return await manager.update_setting(key, value)
