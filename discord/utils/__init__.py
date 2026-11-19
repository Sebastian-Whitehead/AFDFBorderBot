"""
Utilities package for Discord bot

Contains utilities for Discord functionality including rank management and embed processing.
"""

from .rank_manager import RankManager
from .embed_processor import EmbedProcessor, send_processed_embed, load_embeds, member_replacements

__all__ = [
    'RankManager',
    'EmbedProcessor',
    'member_replacements',
    'send_processed_embed',
    'load_embeds'
]
