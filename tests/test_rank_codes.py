import pytest

from database.rank_codes import code_to_level, level_to_code


def test_r1_rank_codes():
    assert level_to_code(0) == "EN0"
    assert level_to_code(7) == "EN7"  # ids.json name has a leading space; code must not
    assert level_to_code(9) == "UO"
    assert level_to_code(10) == "PRES"
    for n in range(11):
        assert code_to_level(level_to_code(n)) == n
    with pytest.raises(KeyError):
        level_to_code(99)
    with pytest.raises(KeyError):
        code_to_level("nope")
