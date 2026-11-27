"""Slash-command choice lists."""
from discord import app_commands


def to_choices(values) -> list:
    """Choices from a {label: value} dict or a list of values."""
    pairs = values.items() if isinstance(values, dict) else ((v, v) for v in values)
    return [app_commands.Choice(name=label, value=value) for label, value in pairs]
