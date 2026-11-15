"""
Database package for AFDFBorderBot

Contains database management utilities and functions.
"""

from .db_manager import get_db_manager, get_shared_db_manager
from .user_functions import create_user, get_user_info, modify_user, search_users, get_user_stats
from .transaction_log import add_transaction, get_unprocessed_transactions, mark_transaction_processed
from .loa_functions import LOAManager
from .settings_manager import get_setting, update_setting, get_all_settings

__all__ = [
    'get_db_manager',
    'get_shared_db_manager',
    'create_user',
    'get_user_info', 
    'modify_user',
    'search_users',
    'get_user_stats',
    'add_transaction',
    'get_unprocessed_transactions', 
    'mark_transaction_processed',
    'LOAManager',
    'get_setting',
    'update_setting',
    'get_all_settings'
]
