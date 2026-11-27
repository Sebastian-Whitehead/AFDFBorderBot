import yaml
import logging

from database.settings_manager import update_setting as update_db_setting, get_settings_manager

# Set up logging for config issues
logger = logging.getLogger(__name__)

# Load IDS with error handling
try:
    with open('ids.yml', encoding='utf-8') as f:
        IDS = yaml.safe_load(f)
except (FileNotFoundError, yaml.YAMLError) as e:
    logger.error(f"Error loading ids.yml: {e}")
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
MILITARY_PERSONNEL_ROLE_ID = ROLES.get('military_personnel', None)
DISTINGUISHED_CITIZEN_ROLE_ID = ROLES.get('distinguished_citizen', None)

# Channel IDs
MAIN_CHANNEL_ID = CHANNELS.get('main_txt', None)
MILITARY_MAIN_CHANNEL_ID = CHANNELS.get('military_main_txt', None)
CHECKPOINT_CHANNEL_ID = CHANNELS.get('checkpoint_txt', None)
WELCOME_CHANNEL_ID = CHANNELS.get('welcome_txt', None)
LOA_CHANNEL_ID = CHANNELS.get('loa_txt', None)

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

# Used when a setting isn't in the DB (existing databases predate these keys)
SETTING_DEFAULTS = {
    'modpack-url': "https://discord.com/channels/1140569342619168778/1229466005059801179",
}

def get_setting(key: str, default=None):
    """Get a setting value from the cached settings."""
    return SETTINGS.get(key, SETTING_DEFAULTS.get(key, default))

async def update_setting(key: str, value) -> bool:
    """Update a setting."""
    try:
        if not await update_db_setting(key, value):
            return False
        SETTINGS[key] = value
        logger.info(f"Setting {key} updated")
        return True
    except Exception as e:
        logger.error(f"Error updating setting {key}: {e}")
        return False