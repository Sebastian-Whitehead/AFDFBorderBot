from unittest.mock import AsyncMock, MagicMock

import pytest

import afdfbot.utils.confirm as c

pytestmark = pytest.mark.asyncio


def _interaction():
    i = MagicMock()
    i.user.id = 1
    i.followup.send = AsyncMock()
    i.edit_original_response = AsyncMock()
    return i


def _fake_view(approved):
    class V:
        def __init__(self, user_id):
            self.approved = approved

        async def wait(self):
            pass
    return V


@pytest.mark.parametrize("approved,ok,text", [(True, True, None), (False, False, "no"), (None, False, "late")])
async def test_confirm(monkeypatch, approved, ok, text):
    monkeypatch.setattr(c, "_Confirm", _fake_view(approved))
    i = _interaction()
    assert await c.confirm(i, "end_session_warning.json", declined="no", timed_out="late") is ok
    assert "Are you sure" in i.followup.send.call_args.kwargs["embeds"][0].description
    if ok:
        i.edit_original_response.assert_not_awaited()
    else:
        assert i.edit_original_response.call_args.kwargs["content"] == text


async def test_placeholders_filled(monkeypatch):
    monkeypatch.setattr(c, "_Confirm", _fake_view(True))
    i = _interaction()
    await c.confirm(i, "attendance_absent_warning.json", {"{absent_list}": "- <@8>"})
    assert "- <@8>" in i.followup.send.call_args.kwargs["embeds"][0].description
