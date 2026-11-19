"""Rank codes (stored in Supabase and used by the bot), ordered low -> high, from ids.yml."""
import yaml
from pathlib import Path

RANKS: dict[str, dict] = yaml.safe_load(
    (Path(__file__).parent.parent / "ids.yml").read_text(encoding="utf-8"))["roles"]["ranks"]
_INDEX = {code: i for i, code in enumerate(RANKS)}


def is_valid_rank(code: str) -> bool:
    return code in RANKS


def rank_index(code: str) -> int:
    return _INDEX[code]  # KeyError -> invalid rank


def rank_choices() -> dict[str, str]:
    """Slash-command choices: label -> code."""
    return {f"{c} · {r['abbr']} – {r['name']}": c for c, r in RANKS.items()}
