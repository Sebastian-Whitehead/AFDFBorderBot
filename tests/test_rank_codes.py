import pytest

from database.rank_codes import RANKS, is_valid_rank, rank_choices, rank_index
from discord.utils.rank_manager import RankManager


def test_codes_and_order():
    codes = list(RANKS)
    assert codes == [f"EN{i}" for i in range(9)] + [f"OF{i}" for i in range(12)] + ["PRES"]
    assert is_valid_rank("EN2") and RANKS["EN2"]["name"] == "Private"
    assert not is_valid_rank("UO") and not is_valid_rank("nope")
    assert rank_index("EN0") == 0 and rank_index("PRES") == len(codes) - 1
    with pytest.raises(KeyError):
        rank_index("UO")


def test_rank_choices():
    ch = rank_choices()
    assert len(ch) == 22
    assert all(len(k) <= 100 for k in ch)
    assert set(ch.values()) == set(RANKS)
    assert ch["EN6 · SSGT – Staff Sergeant"] == "EN6"


def test_is_valid_promotion():
    rm = RankManager()
    assert rm.is_valid_promotion("EN1", "EN3")
    assert not rm.is_valid_promotion("EN1", "EN4")
    assert not rm.is_valid_promotion("EN3", "EN3")
    assert rm.is_valid_promotion("EN8", "OF0")
    assert not rm.is_valid_promotion("EN1", "bogus")
    assert rm.get_rank("EN5")["abbr"] == "SGT" and rm.get_rank("UO") is None
