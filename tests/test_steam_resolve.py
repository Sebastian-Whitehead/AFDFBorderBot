import json
from unittest.mock import AsyncMock

import pytest

from discord.utils import steam

pytestmark = pytest.mark.asyncio
SID = "76561197960287930"


async def test_direct_inputs_need_no_network(monkeypatch):
    fetch = AsyncMock()
    monkeypatch.setattr(steam, "_fetch", fetch)
    assert await steam.resolve_steam_id(SID) == SID
    assert await steam.resolve_steam_id(f"https://steamcommunity.com/profiles/{SID}") == SID
    assert await steam.resolve_steam_id("not a steam thing") is None
    fetch.assert_not_awaited()


async def test_vanity_via_xml_without_key(monkeypatch):
    monkeypatch.delenv("STEAM_API_KEY", raising=False)
    fetch = AsyncMock(return_value=f"<profile><steamID64>{SID}</steamID64></profile>")
    monkeypatch.setattr(steam, "_fetch", fetch)
    assert await steam.resolve_steam_id("https://steamcommunity.com/id/gaben/") == SID
    assert fetch.await_args.args[0] == "https://steamcommunity.com/id/gaben"


async def test_vanity_via_api_with_key(monkeypatch):
    monkeypatch.setenv("STEAM_API_KEY", "k")
    fetch = AsyncMock(return_value=json.dumps({"response": {"steamid": SID, "success": 1}}))
    monkeypatch.setattr(steam, "_fetch", fetch)
    assert await steam.resolve_steam_id("steamcommunity.com/id/gaben") == SID
    assert fetch.await_args.args[1] == {"key": "k", "vanityurl": "gaben"}
    fetch.return_value = json.dumps({"response": {"success": 42, "message": "No match"}})
    assert await steam.resolve_steam_id("steamcommunity.com/id/nobody_here") is None


async def test_lookup_failure_returns_none(monkeypatch):
    monkeypatch.delenv("STEAM_API_KEY", raising=False)
    monkeypatch.setattr(steam, "_fetch", AsyncMock(side_effect=TimeoutError()))
    assert await steam.resolve_steam_id("steamcommunity.com/id/gaben") is None
