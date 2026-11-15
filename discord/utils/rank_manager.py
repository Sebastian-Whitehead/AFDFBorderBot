"""
Rank Management Utilities for AFDFBorderBot

This module provides utilities for managing the flexible rank system.
Handles rank validation, promotion logic, and rank hierarchy operations.
"""

import json
from typing import Dict, Optional, Tuple
from pathlib import Path

class RankManager:
    """Manages the flexible rank system."""
    
    def __init__(self, ids_file_path: str = None):
        if ids_file_path is None:
            # Default to ids.json in the project root
            self.ids_file_path = Path(__file__).parent.parent.parent / "ids.json"
        else:
            self.ids_file_path = Path(ids_file_path)
        
        self._ranks_cache = None
    
    def _load_ranks(self) -> Dict:
        """Load ranks from the ids.json file."""
        if self._ranks_cache is None:
            try:
                with open(self.ids_file_path, 'r') as f:
                    data = json.load(f)
                    self._ranks_cache = data.get('roles', {}).get('ranks', {})
            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"Error loading ranks: {e}")
                self._ranks_cache = {}
        return self._ranks_cache
    
    def get_all_ranks(self) -> Dict[int, Dict]:
        """Get all ranks ordered by hierarchy level."""
        ranks = self._load_ranks()
        # Convert string keys to integers and sort
        return {int(k): v for k, v in sorted(ranks.items(), key=lambda x: int(x[0]))}
    
    def get_rank_by_level(self, level: int) -> Optional[Dict]:
        """Get rank information by hierarchy level."""
        ranks = self.get_all_ranks()
        return ranks.get(level)
    
    def get_rank_by_name(self, name: str) -> Optional[Tuple[int, Dict]]:
        """Get rank level and information by name (case-insensitive)."""
        ranks = self.get_all_ranks()
        for level, rank_info in ranks.items():
            if rank_info['name'].lower() == name.lower():
                return level, rank_info
        return None
    
    def get_rank_by_code(self, code: str) -> Optional[Tuple[int, Dict]]:
        """Get rank level and information by code (case-insensitive)."""
        ranks = self.get_all_ranks()
        for level, rank_info in ranks.items():
            if rank_info['code'].lower() == code.lower():
                return level, rank_info
        return None
    
    def is_valid_promotion(self, current_level: int, target_level: int) -> bool:
        """Check if a promotion from current to target level is valid."""
        ranks = self.get_all_ranks()
        # Must be promoting to a higher level
        if target_level <= current_level:
            return False
        
        # Target level must exist
        if target_level not in ranks:
            return False
        
        # Can't skip more than 2 levels (configurable)
        if target_level - current_level > 2:
            return False
        
        return True
    


# Global instance for easy access
rank_manager = RankManager()
