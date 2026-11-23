"""Small parsers shared by the slash commands."""
import datetime
import json

DATETIME_FMT = ("%Y-%m-%d %H:%M",)
DATE_OR_DATETIME_FMT = ("%Y-%m-%d %H:%M", "%Y-%m-%d")


def parse_utc(text: str, formats=DATETIME_FMT):
    """Timezone-aware UTC datetime from text in the first matching format, else None."""
    for fmt in formats:
        try:
            return datetime.datetime.strptime(text, fmt).replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            pass
    return None


def valid_json_object(text: str) -> bool:
    try:
        return isinstance(json.loads(text), dict)
    except ValueError:
        return False
