"""
Database package for AFDFBorderBot

Contains database management utilities and user functions.
"""

from .db_manager import get_db_manager
from .user_functions import create_user, get_user_info, modify_user, search_users, get_user_stats

__all__ = [
    'get_db_manager',
    'create_user',
    'get_user_info', 
    'modify_user',
    'search_users',
    'get_user_stats'
]
