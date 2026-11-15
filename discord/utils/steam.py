import json
import logging
import os
import re
from typing import Optional

import aiohttp

_PROFILE_URL = re.compile(r"(?:https?://)?(?:www\.)?steamcommunity\.com/profiles/(\d{17})/?(?:[?#].*)?")


def parse_steam_id(text: str) -> Optional[str]:
    """SteamID64 from a steamcommunity.com/profiles/<id> URL or a bare numeric ID, else None.
    shortcut: /id/<vanity> URLs need the Steam Web API to resolve, so they return None."""
    text = text.strip()
    m = _PROFILE_URL.fullmatch(text)
    if m:
        return m.group(1)
    return text if text.isdigit() else None


_VANITY_URL = re.compile(r"(?:https?://)?(?:www\.)?steamcommunity\.com/id/([A-Za-z0-9_-]{2,32})/?(?:[?#].*)?")
_XML_ID = re.compile(r"<steamID64>(\d{17})</steamID64>")


async def _fetch(url: str, params: Optional[dict] = None) -> str:
    # short timeout: slash commands must respond within 3 seconds
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
        async with session.get(url, params=params) as resp:
            resp.raise_for_status()
            return await resp.text()


async def resolve_steam_id(text: str) -> Optional[str]:
    """SteamID64 from a numeric ID, a /profiles/ URL or a custom /id/<name> URL (looked up on Steam).
    Uses the Web API when STEAM_API_KEY is set, else the keyless profile XML. None if it can't be resolved."""
    direct = parse_steam_id(text)
    if direct or not (m := _VANITY_URL.fullmatch(text.strip())):
        return direct
    name = m.group(1)
    try:
        key = os.getenv("STEAM_API_KEY")
        if key:
            body = json.loads(await _fetch(
                "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/",
                {"key": key, "vanityurl": name},
            ))["response"]
            return body["steamid"] if body.get("success") == 1 else None
        xml = _XML_ID.search(await _fetch(f"https://steamcommunity.com/id/{name}", {"xml": "1"}))
        return xml.group(1) if xml else None
    except Exception as e:
        logging.getLogger(__name__).warning(f"Steam vanity lookup failed for {name!r}: {e}")
        return None
