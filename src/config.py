import json
import logging

# Set up logging for config issues
logger = logging.getLogger(__name__)

# Load IDS with error handling
try:
    with open('ids.json') as f:
        IDS = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    logger.error(f"Error loading ids.json: {e}")
    IDS = {}

# Load SETTINGS with error handling
try:
    with open('Settings.json') as f:
        SETTINGS = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    logger.error(f"Error loading Settings.json: {e}")
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
RANKS = ROLES.get('ranks', {})

# Channel IDs
LOG_CHANNEL_ID = CHANNELS.get('log_txt', None)
MAIN_CHANNEL_ID = CHANNELS.get('main_txt', None)
CHECKPOINT_CHANNEL_ID = CHANNELS.get('checkpoint_txt', None)
EVENTS_CHANNEL_ID = CHANNELS.get('events_vc', None)
WELCOME_CHANNEL_ID = CHANNELS.get('welcome_txt', None)

# Settings (Feature Flags)
ENABLE_JOIN_LEAVE = SETTINGS.get('listen-for-join-leave', True)
ENABLE_BORDER_OFFICER = SETTINGS.get('listen-for-border-officer', True)
ENABLE_EVENT_START = SETTINGS.get('listen-for-event-start', False)