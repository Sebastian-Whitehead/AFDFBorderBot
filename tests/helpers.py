STEAM_BASE = 76561190000000000      # not a real Steam64 range
DISCORD_BASE = 900000000000000000
NAME_PREFIX = "zz_test_"


def ids(n):
    """Return (steam_id, discord_id) strings for test slot n."""
    return str(STEAM_BASE + n), str(DISCORD_BASE + n)


async def cleanup():
    """Delete test rows (matched by reserved prefixes/ranges) from the current DATABASE_URL DB."""
    from database.db_manager import get_db_manager
    db = await get_db_manager()
    await db.execute_dml_query(
        "DELETE FROM users WHERE name LIKE 'zz_test_%' OR steam_id LIKE '765611900000%'"
    )
    await db.execute_dml_query(
        "DELETE FROM loa_requests WHERE discord_id LIKE '9000000000000%'"
    )
