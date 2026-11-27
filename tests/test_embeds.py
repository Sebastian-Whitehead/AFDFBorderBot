import json
import yaml
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from afdfbot.config import CHANNELS, ROLES
from afdfbot.utils.embed_processor import EmbedProcessor, member_replacements

EMBEDS = Path(__file__).parent.parent / "embeds"
SPEC = yaml.safe_load((EMBEDS / "placeholders.yml").read_text(encoding="utf-8"))
PLACEHOLDER = re.compile(r"\{([^{}\s]+)\}")
MEMBER_KEYS = {k.strip("{}") for k in member_replacements(SimpleNamespace(mention="", display_name="", id=0)).keys()}


def _strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, list):
        for item in node:
            yield from _strings(item)
    elif isinstance(node, dict):
        for item in node.values():
            yield from _strings(item)


def test_every_embed_is_listed():
    assert {p.name for p in EMBEDS.glob("*.json")} == set(SPEC)


@pytest.mark.parametrize("name", sorted(SPEC))
def test_placeholders_are_known(name):
    allowed = MEMBER_KEYS if SPEC[name] == "member" else set(SPEC[name])
    data = json.loads((EMBEDS / name).read_text(encoding="utf-8"))
    for text in _strings(data):
        for ph in PLACEHOLDER.findall(text):
            kind, _, key = ph.partition(":")
            if key:
                assert kind in ("channel", "role", "setting"), f"{name}: unknown {{{ph}}}"
                if kind != "setting":
                    assert isinstance((CHANNELS if kind == "channel" else ROLES).get(key), int), f"{name}: no single id for {{{ph}}} in ids.yml"
            else:
                assert ph in allowed, f"{name}: {{{ph}}} is not a known placeholder (add it to placeholders.yml or fix the typo)"


def test_generic_placeholders_resolve():
    out = EmbedProcessor.replace_placeholders("{channel:loa_txt} {role:leadership} {setting:modpack-url} {role:nope}", {})
    assert f"<#{CHANNELS['loa_txt']}>" in out
    assert f"<@&{ROLES['leadership']}>" in out
    assert "https://" in out
    assert out.endswith("{role:nope}")  # unknown stays literal


async def test_only_office_hours_is_sent_silently():
    channel = AsyncMock()
    for name, silent in (("office_hours.json", True), ("newcitizen-main.json", False)):
        assert await EmbedProcessor.send_embed(channel, EmbedProcessor.load_embed_data(name))
        assert channel.send.await_args.kwargs["silent"] is silent
