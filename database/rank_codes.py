"""Rank level (int, used by the bot) <-> rank code (text, stored in Supabase), from ids.json."""
import json
from pathlib import Path

_RANKS = {int(k): v["code"].strip() for k, v in
          json.loads((Path(__file__).parent.parent / "ids.json").read_text(encoding="utf-8"))["roles"]["ranks"].items()}

def level_to_code(level: int) -> str:
    return _RANKS[level]          # KeyError -> caller treats as invalid rank

def code_to_level(code: str) -> int:
    for level, c in _RANKS.items():
        if c == code:
            return level
    raise KeyError(code)
