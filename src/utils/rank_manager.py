"""
Rank Management Utilities for AFDFBorderBot

This module provides utilities for managing the flexible rank system.
Handles rank validation, promotion logic, and rank hierarchy operations.
"""

import json
import os
from typing import Dict, List, Optional, Tuple
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
    
    def refresh_cache(self):
        """Refresh the ranks cache from file."""
        self._ranks_cache = None
        self._load_ranks()
    
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
    
    def get_rank_by_role_id(self, role_id: str) -> Optional[Tuple[int, Dict]]:
        """Get rank level and information by Discord role ID."""
        ranks = self.get_all_ranks()
        for level, rank_info in ranks.items():
            if rank_info['role_id'] == str(role_id):
                return level, rank_info
        return None
    
    def is_valid_promotion(self, current_level: int, target_level: int) -> bool:
        """Check if a promotion from current to target level is valid."""
        ranks = self.get_all_ranks()
        max_level = max(ranks.keys()) if ranks else 0
        
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
    
    def get_promotable_ranks(self, current_level: int) -> List[Tuple[int, Dict]]:
        """Get list of ranks that someone can be promoted to from current level."""
        ranks = self.get_all_ranks()
        promotable = []
        
        for level, rank_info in ranks.items():
            if self.is_valid_promotion(current_level, level):
                promotable.append((level, rank_info))
        
        return promotable
    
    def get_rank_choices(self) -> List[str]:
        """Get list of rank names for slash command choices."""
        ranks = self.get_all_ranks()
        return [f"{rank_info['name']} ({rank_info['code']})" for rank_info in ranks.values()]
    
    def parse_rank_choice(self, choice: str) -> Optional[Tuple[int, Dict]]:
        """Parse a rank choice string back to level and rank info."""
        # Extract the code from the choice string
        if '(' in choice and ')' in choice:
            code = choice.split('(')[-1].split(')')[0]
            return self.get_rank_by_code(code)
        else:
            # Try to match by name
            return self.get_rank_by_name(choice)
    
    def format_rank_display(self, level: int, rank_info: Dict) -> str:
        """Format rank for display purposes."""
        return f"**{rank_info['name']}** ({rank_info['code']}) - Level {level}"
    
    def get_rank_hierarchy_display(self) -> str:
        """Get formatted string of entire rank hierarchy."""
        ranks = self.get_all_ranks()
        hierarchy = []
        
        for level in sorted(ranks.keys(), reverse=True):  # Highest to lowest
            rank_info = ranks[level]
            hierarchy.append(f"**Level {level}:** {rank_info['name']} ({rank_info['code']})")
        
        return "\n".join(hierarchy)


# Global instance for easy access
rank_manager = RankManager()
