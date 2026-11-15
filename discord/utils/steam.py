import re
from typing import Optional

_PROFILE_URL = re.compile(r"(?:https?://)?(?:www\.)?steamcommunity\.com/profiles/(\d{17})/?(?:[?#].*)?")


def parse_steam_id(text: str) -> Optional[str]:
    """SteamID64 from a steamcommunity.com/profiles/<id> URL or a bare numeric ID, else None.
    shortcut: /id/<vanity> URLs need the Steam Web API to resolve, so they return None."""
    text = text.strip()
    m = _PROFILE_URL.fullmatch(text)
    if m:
        return m.group(1)
    return text if text.isdigit() else None
