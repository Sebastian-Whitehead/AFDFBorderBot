import json
import logging
import sys
import os

# Add the parent directory to the path so we can import from database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.settings_manager import update_setting as update_db_setting, get_settings_manager

# Set up logging for config issues
logger = logging.getLogger(__name__)

# Load IDS with error handling
try:
    with open('ids.json') as f:
        IDS = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    logger.error(f"Error loading ids.json: {e}")
    IDS = {}

# Settings will be loaded from database - initialize placeholders
SETTINGS = {}

# Extract configuration with safe defaults
ROLES = IDS.get('roles', {})
CHANNELS = IDS.get('channels', {})

# Provide safe defaults for critical configurations
TESTING_GUILD_ID = IDS.get('testing_guild', None)

# Role IDs
LEADERSHIP_ROLE_ID = ROLES.get('leadership', None)
BORDER_OFFICER_ROLE_ID = ROLES.get('border_officer', None)
CIVIL_SERVANT_ROLE_ID = ROLES.get('civil_servant', None)
JOIN_ROLE_ID = ROLES.get('join_role', None)
CITIZEN_ROLE_IDS = ROLES.get('citizen', [])
ENLISTED_ROLE_IDS = ROLES.get('enlisted', [])
MILITARY_PERSONNEL_ROLE_ID = ROLES.get('military_personnel', None)
DISTINGUISHED_CITIZEN_ROLE_ID = ROLES.get('distinguished_citizen', None)
RANKS = ROLES.get('ranks', {})

# Channel IDs
LOG_CHANNEL_ID = CHANNELS.get('log_txt', None)
MAIN_CHANNEL_ID = CHANNELS.get('main_txt', None)
CHECKPOINT_CHANNEL_ID = CHANNELS.get('checkpoint_txt', None)
EVENTS_CHANNEL_ID = CHANNELS.get('events_vc', None)
WELCOME_CHANNEL_ID = CHANNELS.get('welcome_txt', None)
LOA_CHANNEL_ID = CHANNELS.get('loa_txt', None)
ANNOUNCEMENTS_CHANNEL_ID = CHANNELS.get('announcements_txt', None)
INFORMATION_DB_CHANNEL_ID = CHANNELS.get('information_db_txt', None)
EVENTS_TXT_CHANNEL_ID = CHANNELS.get('events_txt', None)
VIETNAM_CAMPAIGN_CHANNEL_ID = CHANNELS.get('vietnam_campaign_txt', None)

# Async function to load settings from database
async def load_settings():
    """Load settings from database and update global variables."""
    global SETTINGS
    
    try:
        manager = await get_settings_manager()
        SETTINGS = await manager.get_all_settings()
        
        logger.info("Settings loaded from database")
    except Exception as e:
        logger.error(f"Error loading settings from database: {e}")
        # Keep default values if database fails

def get_setting(key: str, default=None):
    """Get a setting value from the cached settings."""
    return SETTINGS.get(key, default)

async def update_setting(key: str, value) -> bool:
    """Update a setting."""
    try:
        await update_db_setting(key, value) #update the setting in the database
        await load_settings() # Reload settings from database to update cache
        
        logger.info(f"Setting {key} updated")
        return True
    except Exception as e:
        logger.error(f"Error updating setting {key}: {e}")
        return False