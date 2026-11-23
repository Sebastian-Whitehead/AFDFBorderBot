"""Rank lookups and promotion rules, over the ordered rank codes in ids.yml."""
from typing import Dict, Optional

from database.rank_codes import RANKS, is_valid_rank, rank_index


class RankManager:
    def get_rank(self, code: str) -> Optional[Dict]:
        if not is_valid_rank(code):
            return None
        return {"code": code, **RANKS[code]}

    def is_valid_promotion(self, current_code: str, target_code: str) -> bool:
        if not (is_valid_rank(current_code) and is_valid_rank(target_code)):
            return False
        return 0 < rank_index(target_code) - rank_index(current_code) <= 2

    def rank_text(self, code: str) -> str:
        info = self.get_rank(code)
        return f"{info['name']} ({info['code']})"
