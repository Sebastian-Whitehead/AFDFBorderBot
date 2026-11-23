"""
Core User Database Functions for AFDFBorderBot

Bot users live in the shared Supabase DB: a public.identities_player row with a
military.service_records row in the AFDF-Para Raiders org.
"""

from datetime import date
import logging
from typing import Optional, Dict, Any

from sqlalchemy import text

from .db_manager import get_shared_db_manager
from .rank_codes import is_valid_rank

logger = logging.getLogger(__name__)

ORG = "AFDF-Para Raiders"

_LATEST_EVENT_FILTER = """
    WHERE e.service_record_id = sr.id
      AND e.event_type IN ('enlisted', 'reenlisted', 'discharged', 'retired')
    ORDER BY e.occured_at DESC, e.id DESC LIMIT 1
"""

_INSERT_RECORD = """INSERT INTO military.service_records
                            (player_identity_id, organization_id, current_rank, service_status)
                            SELECT :pid, o.id, :code, 'active'
                            FROM public.identities_organizations o WHERE o.name = :org
                            RETURNING id"""

SET_NOTES = """UPDATE public.identities_player
                            SET details = coalesce(details, '{}'::jsonb) || jsonb_build_object('notes', CAST(:notes AS text))
                            WHERE id = :id"""

# One row per bot user; ev = newest enlisted/reenlisted/discharged event (decision D3).
_BOT_USER = """
SELECT p.id, p.alias, p.steam_id, p.discord_id, p.created_at, p.details,
       sr.id AS sr_id, sr.current_rank, ev.event_type, ev.occured_at
FROM public.identities_player p
JOIN military.service_records sr ON sr.player_identity_id = p.id
JOIN public.identities_organizations o ON o.id = sr.organization_id AND o.name = :org
LEFT JOIN LATERAL (
    SELECT e.event_type, e.occured_at FROM military.service_events e
""" + _LATEST_EVENT_FILTER + """) ev ON true
"""


def _is_enlisted(row) -> bool:
    return row.event_type in ("enlisted", "reenlisted")


def _brief(row) -> Dict[str, Any]:
    return {
        "id": row.id,
        "name": row.alias,
        "steam_id": str(row.steam_id) if row.steam_id is not None else None,
        "discord_id": str(row.discord_id) if row.discord_id is not None else None,
        "rank": row.current_rank,
        "enlisted": _is_enlisted(row),
    }


def _full(row) -> Dict[str, Any]:
    d = row.details or {}
    last_death = d.get("last_death")
    if isinstance(last_death, str):
        last_death = date.fromisoformat(last_death)
    out = _brief(row)
    out.update({
        "joined_at": row.created_at,
        "enlisted_at": row.occured_at if _is_enlisted(row) else None,
        "notes": d.get("notes"),
        "achievements": d.get("achievements"),
        "last_death": last_death,
        "deaths": d.get("deaths", 0),
        "reprimands": d.get("reprimands"),
        "extra_data": d.get("extra_data"),
    })
    return out


async def _find(session, identifier: str):
    n = int(identifier)
    res = await session.execute(
        text(_BOT_USER + " WHERE p.discord_id = :n OR p.steam_id = :n"), {"org": ORG, "n": n}
    )
    return res.first()


async def create_user(
    name: str,
    steam_id: Optional[str],
    discord_id: Optional[str] = None,
    rank: str = "EN0",
    notes: Optional[str] = None,
    enlisted: bool = False,
    service_record: bool = True
) -> Optional[Dict[str, Any]]:
    """Create a new user in the database. steam_id may be None if discord_id is given.
    service_record=False creates the player identity only (enlisted is then ignored)."""
    try:
        steam = int(steam_id) if steam_id else None
        discord = int(discord_id) if discord_id else None
    except (ValueError, TypeError):
        return None
    if not is_valid_rank(rank) or (steam is None and discord is None):
        return None
    code = rank
    if steam is None and not await ensure_player_identity(name, None, discord_id):
        return None

    try:
        db = await get_shared_db_manager()

        async with db.get_session() as session:
            if steam is None:
                ident = (await session.execute(
                    text("SELECT id FROM public.identities_player WHERE discord_id = :d"), {"d": discord}
                )).one()
            else:
                if (await session.execute(
                    text(_BOT_USER + " WHERE p.steam_id = :n"), {"org": ORG, "n": steam}
                )).first():
                    return None
                if discord is not None:
                    await _claim_null_steam(session, discord, steam)
                if discord is not None and (await session.execute(
                    text("SELECT 1 FROM public.identities_player WHERE discord_id = :d AND steam_id IS DISTINCT FROM :s"),
                    {"d": discord, "s": steam},
                )).first():
                    return None

                await session.execute(
                    text("SELECT public.fab_ensure_player_account(:name, :steam, :discord)"),
                    {"name": name, "steam": steam, "discord": discord},
                )
                ident = (await session.execute(
                    text("SELECT id, discord_id FROM public.identities_player WHERE steam_id = :s"), {"s": steam}
                )).one()
                if discord is not None:
                    if ident.discord_id is None:
                        await session.execute(
                            text("UPDATE public.identities_player SET discord_id = :d WHERE id = :id"),
                            {"d": discord, "id": ident.id},
                        )
                    elif ident.discord_id != discord:
                        return None  # rolled back on session close

            if service_record:
                sr_id = (await session.execute(
                    text(_INSERT_RECORD),
                    {"pid": ident.id, "code": code, "org": ORG},
                )).scalar_one()
                if enlisted:
                    await session.execute(
                        text("""INSERT INTO military.service_events (service_record_id, event_type, rank, occured_at)
                                VALUES (:sr, 'enlisted', :code, now())"""),
                        {"sr": sr_id, "code": code},
                    )
            if notes:
                await session.execute(
                    text(SET_NOTES),
                    {"notes": notes, "id": ident.id},
                )
            await session.commit()

            return {
                "id": ident.id,
                "name": name,
                "steam_id": str(steam) if steam is not None else None,
                "discord_id": str(discord) if discord is not None else None,
                "rank": code if service_record else None,
                "enlisted": bool(enlisted and service_record),
            }

    except Exception as e:
        logger.exception(f"Error creating user: {e}")
        return None


async def get_user_info(identifier: str) -> Optional[Dict[str, Any]]:
    """Get user information by Discord ID or Steam ID."""
    try:
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            row = await _find(session, identifier)
            return _full(row) if row else None
    except Exception as e:
        logger.exception(f"Error getting user info: {e}")
        return None


async def modify_user(
    identifier: str,
    name: Optional[str] = None,
    rank: Optional[str] = None,
    notes: Optional[str] = None,
    enlisted: Optional[bool] = None,
    reason: Optional[str] = None
) -> bool:
    """Modify user information."""
    if rank is not None and not is_valid_rank(rank):
        return False
    try:
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            row = await _find(session, identifier)
            if not row:
                return False

            if name is not None:
                await session.execute(
                    text("UPDATE public.identities_player SET alias = :name WHERE id = :id"),
                    {"name": name, "id": row.id},
                )
            if rank is not None:
                code = rank
                await session.execute(
                    text("UPDATE military.service_records SET current_rank = :code, updated_at = now() WHERE id = :sr"),
                    {"code": code, "sr": row.sr_id},
                )
                await session.execute(
                    text("""INSERT INTO military.service_events (service_record_id, event_type, rank, notes, occured_at)
                            VALUES (:sr, 'rank_changed', :code, :reason, now())"""),
                    {"sr": row.sr_id, "code": code, "reason": reason},
                )
            if notes is not None:
                await session.execute(
                    text(SET_NOTES),
                    {"notes": notes, "id": row.id},
                )
            if enlisted is not None:
                if enlisted:
                    had_discharge = (await session.execute(
                        text("SELECT 1 FROM military.service_events WHERE service_record_id = :sr AND event_type = 'discharged' LIMIT 1"),
                        {"sr": row.sr_id},
                    )).first() is not None
                    etype = "reenlisted" if had_discharge else "enlisted"
                else:
                    etype = "discharged"
                await session.execute(
                    text("""INSERT INTO military.service_events (service_record_id, event_type, rank, occured_at)
                            VALUES (:sr, :etype, :code, now())"""),
                    {"sr": row.sr_id, "etype": etype, "code": row.current_rank if rank is None else rank},
                )
            await session.commit()
            return True

    except Exception as e:
        logger.exception(f"Error modifying user: {e}")
        return False


async def _claim_null_steam(session, discord: int, steam: int) -> None:
    """An identity made without a Steam ID (from /approve) gets it attached when one is later given."""
    await session.execute(
        text("""UPDATE public.identities_player SET steam_id = :s
                WHERE discord_id = :d AND steam_id IS NULL
                  AND NOT EXISTS (SELECT 1 FROM public.identities_player WHERE steam_id = :s)"""),
        {"s": steam, "d": discord},
    )


async def ensure_player_identity(name: str, steam_id: Optional[str], discord_id: str) -> bool:
    """Create or adopt the identity for steam_id (may be None) and link discord_id. No service record."""
    try:
        steam = int(steam_id) if steam_id else None
        discord = int(discord_id)
    except (ValueError, TypeError):
        return False

    try:
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            if steam is not None:
                await _claim_null_steam(session, discord, steam)
                if (await session.execute(
                    text("SELECT 1 FROM public.identities_player WHERE discord_id = :d AND steam_id IS DISTINCT FROM :s"),
                    {"d": discord, "s": steam},
                )).first():
                    return False
            # the SQL function takes steam and/or discord, links them, and raises on a conflict (-> False below)
            await session.execute(
                text("SELECT public.fab_ensure_player_account(:name, :steam, :discord)"),
                {"name": name, "steam": steam, "discord": discord},
            )
            await session.commit()
            return True
    except Exception as e:
        logger.exception(f"Error ensuring player identity: {e}")
        return False


async def create_service_record(discord_id: str, rank: str) -> str:
    """Create the service record plus a 'Service record created' event at that rank for an existing identity:
    'created', 'already_exists', 'no_identity' or 'error'."""
    try:
        discord = int(discord_id)
        if not is_valid_rank(rank):
            return "error"
        code = rank
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            pid = (await session.execute(
                text("SELECT id FROM public.identities_player WHERE discord_id = :d"), {"d": discord}
            )).scalar_one_or_none()
            if pid is None:
                return "no_identity"
            org = (await session.execute(
                text("SELECT id FROM public.identities_organizations WHERE name = :org"), {"org": ORG}
            )).scalar_one()
            if (await session.execute(
                text("SELECT 1 FROM military.service_records WHERE player_identity_id = :p AND organization_id = :o"),
                {"p": pid, "o": org},
            )).first():
                return "already_exists"
            sr_id = (await session.execute(
                text("""INSERT INTO military.service_records (player_identity_id, organization_id, current_rank, service_status)
                        VALUES (:p, :o, :r, 'active') RETURNING id"""),
                {"p": pid, "o": org, "r": code},
            )).scalar_one()
            # 'rank_changed' not 'enlisted': /enlist treats an enlisted event as already enlisted
            await session.execute(
                text("""INSERT INTO military.service_events (service_record_id, event_type, rank, notes, occured_at)
                        VALUES (:sr, 'rank_changed', :r, 'Service record created', now())"""),
                {"sr": sr_id, "r": code},
            )
            await session.commit()
            return "created"
    except Exception as e:
        logger.exception(f"Error creating service record: {e}")
        return "error"


async def add_reprimand(discord_id: str, reason: str, issued_by: str) -> str:
    """Log a 'reprimand' service event: 'recorded', 'no_record' (no identity or service record) or 'error'."""
    try:
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            row = await _find(session, discord_id)
            if row is None:
                return "no_record"
            await session.execute(
                text("""INSERT INTO military.service_events (service_record_id, event_type, rank, notes, details, occured_at)
                        VALUES (:sr, 'reprimand', :rank, :reason, jsonb_build_object('issued_by', CAST(:by AS text)), now())"""),
                {"sr": row.sr_id, "rank": row.current_rank, "reason": reason, "by": issued_by},
            )
            await session.commit()
            return "recorded"
    except Exception as e:
        logger.exception(f"Error adding reprimand: {e}")
        return "error"


async def add_service_event(discord_id: str, event_type: str, occured_at, rank: Optional[str] = None,
                             status: Optional[str] = None, notes: Optional[str] = None,
                             details: Optional[str] = None) -> str:
    """Insert a service event (details is a JSON string): 'created', 'no_record' (no identity or service record) or 'error'."""
    try:
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            row = await _find(session, discord_id)
            if row is None:
                return "no_record"
            await session.execute(
                text("""INSERT INTO military.service_events (service_record_id, event_type, rank, status, notes, details, occured_at)
                        VALUES (:sr, :type, :rank, :status, :notes, CAST(:details AS jsonb), :at)"""),
                {"sr": row.sr_id, "type": event_type, "rank": rank, "status": status,
                 "notes": notes, "details": details, "at": occured_at},
            )
            await session.commit()
            return "created"
    except Exception as e:
        logger.exception(f"Error adding service event: {e}")
        return "error"


async def get_service_events(discord_id: str, limit: int = 10) -> Optional[list]:
    """Newest-first service events for a user, or None if they have no service record (or on error)."""
    try:
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            row = await _find(session, discord_id)
            if row is None:
                return None
            res = await session.execute(
                text("""SELECT id, occured_at, event_type, rank, notes FROM military.service_events
                        WHERE service_record_id = :sr ORDER BY occured_at DESC, id DESC LIMIT :n"""),
                {"sr": row.sr_id, "n": limit},
            )
            return [dict(r._mapping) for r in res]
    except Exception as e:
        logger.exception(f"Error getting service events: {e}")
        return None


_MERGE_CODES = ("no_identity", "steam_linked_to_other_discord", "different_steam", "service_record_conflict",
                "record_not_found", "same_record", "different_organization")


def _merge_error(e: Exception) -> str:
    """The SQL function's error code (its RAISE message), else 'error'."""
    return next((c for c in _MERGE_CODES if c in str(e)), "error")


async def merge_identities(discord_id: str, steam_id: str, force: bool = False) -> str:
    """Link/merge the Discord identity and the Steam identity (public.fab_merge_player_identities):
    'merged', 'linked', 'already_linked', a SQL error code (see _MERGE_CODES) or 'error'."""
    try:
        discord, steam = int(discord_id), int(steam_id)
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            res = (await session.execute(
                text("SELECT public.fab_merge_player_identities(:s, :d, :f)"), {"s": steam, "d": discord, "f": force}
            )).scalar_one()
            await session.commit()
        if res["result"] == "merged":  # no undo, so keep what was deleted
            logger.info(f"Merged identities (discord {discord}, steam {steam}): {res}")
        return res["result"]
    except Exception as e:
        logger.exception(f"Error merging identities: {e}")
        return _merge_error(e)


async def _merge_side(session, col: str, value: int):
    """Identity found by steam_id/discord_id with its AFDF record, or None."""
    return (await session.execute(
        text(f"""SELECT p.id, p.alias, p.steam_id, p.discord_id, sr.id AS sr_id, sr.current_rank, sr.service_status
                 FROM public.identities_player p
                 LEFT JOIN military.service_records sr ON sr.player_identity_id = p.id AND sr.organization_id =
                      (SELECT id FROM public.identities_organizations WHERE name = :org)
                 WHERE p.{col} = :v"""),
        {"org": ORG, "v": value},
    )).first()


async def get_merge_preview(discord_id: str, steam_id: str) -> Optional[Dict[str, Any]]:
    """Read-only view of both sides for a confirmation prompt: {'steam': row|None, 'discord': row|None, 'survivor': ...}.
    A row has id, alias, steam_id, discord_id, sr_id, current_rank, service_status. survivor is
    'steam' or 'discord': the side with a service record survives, the Discord one if neither (same rule as the SQL).
    None on error."""
    try:
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            st = await _merge_side(session, "steam_id", int(steam_id))
            dc = await _merge_side(session, "discord_id", int(discord_id))
        return {"steam": st, "discord": dc, "survivor": "steam" if st and st.sr_id else "discord"}
    except Exception as e:
        logger.exception(f"Error getting merge preview: {e}")
        return None


async def merge_service_records(discord_id: str, steam_id: str) -> str:
    """Merge the Steam identity's service record into the Discord identity's (public.fab_merge_service_records):
    'merged', 'no_identity', 'no_record' (either side has none), a SQL error code or 'error'.
    On success returns 'merged' and the SQL result is printed (it includes the previous rank/status)."""
    try:
        prev = await get_merge_preview(discord_id, steam_id)
        if prev is None:
            return "error"
        if not prev["steam"] or not prev["discord"]:
            return "no_identity"
        if not prev["steam"].sr_id or not prev["discord"].sr_id:
            return "no_record"
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            res = (await session.execute(
                text("SELECT public.fab_merge_service_records(:f, :t)"),
                {"f": prev["steam"].sr_id, "t": prev["discord"].sr_id},
            )).scalar_one()
            await session.commit()
        logger.info(f"Merged service records (discord {discord_id}, steam {steam_id}): {res}")
        return "merged"
    except Exception as e:
        logger.exception(f"Error merging service records: {e}")
        return _merge_error(e)


async def _service_state(session, discord: int):
    """(identity id or None, service record row or None); the row has id, current_rank, service_status, event_type (newest enlisted/reenlisted/discharged)."""
    pid = (await session.execute(
        text("SELECT id FROM public.identities_player WHERE discord_id = :d"), {"d": discord}
    )).scalar_one_or_none()
    if pid is None:
        return None, None
    sr = (await session.execute(
        text("""SELECT sr.id, sr.current_rank, sr.service_status, ev.event_type
                FROM military.service_records sr
                JOIN public.identities_organizations o ON o.id = sr.organization_id AND o.name = :org
                LEFT JOIN LATERAL (
                    SELECT e.event_type FROM military.service_events e
                    """ + _LATEST_EVENT_FILTER + """) ev ON true
                WHERE sr.player_identity_id = :pid"""),
        {"org": ORG, "pid": pid},
    )).first()
    return pid, sr


async def enlist_member(discord_id: str, rank: str = "EN0") -> str:
    """Enlist an existing identity: 'enlisted' (new record or first enlisted event), 'reinstated'
    (inactive record set active again at its previous rank), 'already_enlisted', 'no_identity' or 'error'."""
    try:
        discord = int(discord_id)
        if not is_valid_rank(rank):
            return "error"
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            pid, sr = await _service_state(session, discord)
            if pid is None:
                return "no_identity"

            result = "enlisted"
            if sr is None:
                sr_id = (await session.execute(
                    text(_INSERT_RECORD),
                    {"pid": pid, "code": rank, "org": ORG},
                )).scalar_one()
                etype, ev_rank = "enlisted", rank
            elif sr.service_status != "active" or sr.event_type == "discharged":
                sr_id, etype, ev_rank, result = sr.id, "reenlisted", sr.current_rank, "reinstated"
                await session.execute(
                    text("UPDATE military.service_records SET service_status = 'active', updated_at = now() WHERE id = :sr"),
                    {"sr": sr_id},
                )
            elif sr.event_type in ("enlisted", "reenlisted"):
                return "already_enlisted"
            else:  # record made by /create_service_record: active but never enlisted
                sr_id, etype, ev_rank = sr.id, "enlisted", sr.current_rank

            await session.execute(
                text("""INSERT INTO military.service_events (service_record_id, event_type, rank, occured_at)
                        VALUES (:sr, :etype, :code, now())"""),
                {"sr": sr_id, "etype": etype, "code": ev_rank},
            )
            await session.commit()
            return result
    except Exception as e:
        logger.exception(f"Error enlisting member: {e}")
        return "error"


async def discharge_member(discord_id: str, reason: Optional[str] = None, kind: str = "discharged") -> str:
    """End a member's service (kind 'discharged' or 'retired'): set the record to that status and log the event
    (rank is kept for reinstatement). Returns kind on success, otherwise 'no_record' (no identity or service record), 'not_enlisted' (already inactive) or 'error'."""
    if kind not in ("discharged", "retired"):
        return "error"
    try:
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            pid, sr = await _service_state(session, int(discord_id))
            if sr is None:
                return "no_record"
            if sr.service_status != "active" or sr.event_type == "discharged":
                return "not_enlisted"
            await session.execute(
                text("UPDATE military.service_records SET service_status = :kind, updated_at = now() WHERE id = :sr"),
                {"sr": sr.id, "kind": kind},
            )
            await session.execute(
                text("""INSERT INTO military.service_events (service_record_id, event_type, rank, notes, occured_at)
                        VALUES (:sr, :kind, :rank, :reason, now())"""),
                {"sr": sr.id, "kind": kind, "rank": sr.current_rank, "reason": reason},
            )
            await session.commit()
            return kind
    except Exception as e:
        logger.exception(f"Error discharging member: {e}")
        return "error"
