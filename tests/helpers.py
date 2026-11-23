STEAM_BASE = 76561190000000000      # not a real Steam64 range
DISCORD_BASE = 900000000000000000


def ids(n):
    """Return (steam_id, discord_id) strings for test slot n."""
    return str(STEAM_BASE + n), str(DISCORD_BASE + n)


async def cleanup():
    """Delete test settings rows from the current DATABASE_URL DB."""
    from database.db_manager import get_db_manager
    db = await get_db_manager()
    await db.execute_raw_query("DELETE FROM bot_settings WHERE setting_key LIKE 'zz_test_%'")


_MATCH = ("(steam_id BETWEEN 76561190000000000 AND 76561190000999999 "
          "OR discord_id BETWEEN 900000000000000000 AND 900000000000999999 "
          "OR alias LIKE 'zz_test_%')")


async def cleanup_shared():
    """Delete test players and their records from the shadow DB (never production)."""
    import os
    from urllib.parse import urlparse
    assert urlparse(os.environ["SUPABASE_DATABASE_URL"]).hostname == "localhost", "refusing: not localhost"
    from database.db_manager import get_shared_db_manager
    db = await get_shared_db_manager()
    pids = f"SELECT id FROM public.identities_player WHERE {_MATCH}"
    recs = f"SELECT id FROM military.service_records WHERE player_identity_id IN ({pids})"
    for q in (
        f"DELETE FROM military.attendance WHERE service_record_id IN ({recs})",
        "DELETE FROM military.sessions WHERE session_name LIKE 'zz_test_%'",
        f"DELETE FROM military.leave_requests WHERE service_record_id IN ({recs})",
        f"DELETE FROM military.service_events WHERE service_record_id IN ({recs})",
        f"DELETE FROM military.service_records WHERE player_identity_id IN ({pids})",
        f"DELETE FROM economy.accounts WHERE player_identity_id IN ({pids})",  # shadow-only; FK requires it
        f"DELETE FROM public.identities_player WHERE {_MATCH}",
    ):
        await db.execute_raw_query(q)
