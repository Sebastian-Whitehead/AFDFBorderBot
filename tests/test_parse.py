import datetime

from discord.utils.parse import DATE_OR_DATETIME_FMT, parse_utc, valid_json_object


def test_parse_utc():
    utc = datetime.timezone.utc
    assert parse_utc("2026-11-20 19:00") == datetime.datetime(2026, 11, 20, 19, 0, tzinfo=utc)
    assert parse_utc("2026-11-20") is None
    assert parse_utc("2026-11-20", DATE_OR_DATETIME_FMT) == datetime.datetime(2026, 11, 20, tzinfo=utc)
    assert parse_utc("nope", DATE_OR_DATETIME_FMT) is None


def test_valid_json_object():
    assert valid_json_object('{"a": 1}')
    assert not valid_json_object("[1]") and not valid_json_object("x")
