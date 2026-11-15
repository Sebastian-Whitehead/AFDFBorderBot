import pytest

from database.db_manager import get_db_manager
from database.settings_manager import (
    get_all_settings,
    get_setting,
    get_settings_manager,
    update_setting,
)

KEY = "zz_test_setting"


@pytest.fixture
async def clean_settings(local_db):
    async def wipe():
        db = await get_db_manager()
        await db.execute_dml_query("DELETE FROM bot_settings WHERE setting_key LIKE 'zz_test_%'")
        (await get_settings_manager())._cache.pop(KEY, None)

    await wipe()
    yield
    await wipe()


async def test_s1_setting_round_trip(clean_settings):
    assert await get_setting(KEY, "missing") == "missing"

    assert await update_setting(KEY, {"a": 1, "b": [1, 2]}) is True
    assert await get_setting(KEY) == {"a": 1, "b": [1, 2]}

    # Overwrite, then drop the cache so the value must come back from the DB.
    assert await update_setting(KEY, "second") is True
    (await get_settings_manager())._cache.pop(KEY, None)
    assert await get_setting(KEY) is None
    assert (await get_all_settings())[KEY] == "second"
    assert await get_setting(KEY) == "second"
