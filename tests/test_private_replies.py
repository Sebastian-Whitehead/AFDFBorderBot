import pathlib
import re

# Replies are private by default: a deferred reply is only ephemeral if the defer says so.
# (utils/confirm.py defers button clicks, which is a different thing.)
COMMANDS = pathlib.Path(__file__).parent.parent / "discord" / "commands"


def test_commands_defer_ephemerally():
    bad = [f"{p.name}:{n}" for p in COMMANDS.glob("*.py")
           for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
           if re.search(r"response\.defer\(\s*\)", line) and not line.lstrip().startswith("#")]
    assert not bad, f"public defer(): {bad}"


def test_commands_send_message_is_ephemeral():
    bad = [p.name for p in COMMANDS.glob("*.py")
           for m in re.finditer(r"response\.send_message\((.*?)\n\s*\)\n", p.read_text(encoding="utf-8"), re.S)
           if "ephemeral=True" not in m.group(1) and not m.group(0).lstrip().startswith("#")]
    assert not bad, f"public send_message in {bad}"
