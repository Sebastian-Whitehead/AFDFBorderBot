"""
Database package for AFDFBorderBot

Contains database management utilities and functions.
"""

from .user_functions import create_user, get_user_info, modify_user, ensure_player_identity, enlist_member, discharge_member, merge_identities, merge_service_records, get_merge_preview, create_service_record, add_reprimand, add_service_event, get_service_events

__all__ = [
    'create_user',
    'get_user_info', 
    'modify_user',
    'ensure_player_identity',
    'enlist_member',
    'discharge_member',
    'merge_identities',
    'merge_service_records',
    'get_merge_preview',
    'create_service_record',
    'add_reprimand',
    'add_service_event',
    'get_service_events'
]
