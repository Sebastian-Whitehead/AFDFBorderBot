"""Rank codes (stored in Supabase and used by the bot), ordered low -> high, from ids.json."""
import json
from pathlib import Path

RANKS: dict[str, dict] = json.loads(
    (Path(__file__).parent.parent / "ids.json").read_text(encoding="utf-8"))["roles"]["ranks"]
_INDEX = {code: i for i, code in enumerate(RANKS)}


def is_valid_rank(code: str) -> bool:
    return code in RANKS


def rank_index(code: str) -> int:
    return _INDEX[code]  # KeyError -> invalid rank


def rank_choices() -> dict[str, str]:
    """Slash-command choices: label -> code."""
    return {f"{c} · {r['abbr']} – {r['name']}": c for c, r in RANKS.items()}
