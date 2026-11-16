"""
Database package for AFDFBorderBot

Contains database management utilities and functions.
"""

from .db_manager import get_db_manager, get_shared_db_manager
from .user_functions import create_user, get_user_info, modify_user, ensure_player_identity, enlist_member, discharge_member, set_steam_id, create_service_record, add_reprimand, add_service_event, get_service_events
from .session_functions import create_session, end_latest_session
from .loa_functions import LOAManager
from .settings_manager import get_setting, update_setting, get_all_settings

__all__ = [
    'get_db_manager',
    'get_shared_db_manager',
    'create_user',
    'get_user_info', 
    'modify_user',
    'ensure_player_identity',
    'enlist_member',
    'discharge_member',
    'set_steam_id',
    'create_service_record',
    'add_reprimand',
    'add_service_event',
    'get_service_events',
    'create_session',
    'end_latest_session',
    'LOAManager',
    'get_setting',
    'update_setting',
    'get_all_settings'
]
