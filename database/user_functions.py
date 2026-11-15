"""
Core User Database Functions for AFDFBorderBot

Bot users live in the shared Supabase DB: a public.identities_player row with a
military.service_records row in the AFDF-Para Raiders org.
"""

from datetime import date
from typing import Optional, Dict, Any, List

from sqlalchemy import text

from .db_manager import get_shared_db_manager
from .rank_codes import level_to_code, code_to_level

ORG = "AFDF-Para Raiders"

# One row per bot user; ev = newest enlisted/reenlisted/discharged event (decision D3).
_BOT_USER = """
SELECT p.id, p.alias, p.steam_id, p.discord_id, p.created_at, p.details,
       sr.id AS sr_id, sr.current_rank, ev.event_type, ev.occured_at
FROM public.identities_player p
JOIN military.service_records sr ON sr.player_identity_id = p.id
JOIN public.identities_organizations o ON o.id = sr.organization_id AND o.name = :org
LEFT JOIN LATERAL (
    SELECT e.event_type, e.occured_at FROM military.service_events e
    WHERE e.service_record_id = sr.id
      AND e.event_type IN ('enlisted', 'reenlisted', 'discharged')
    ORDER BY e.occured_at DESC, e.id DESC LIMIT 1
) ev ON true
"""


def _is_enlisted(row) -> bool:
    return row.event_type in ("enlisted", "reenlisted")


def _brief(row) -> Dict[str, Any]:
    return {
        "id": row.id,
        "name": row.alias,
        "steam_id": str(row.steam_id) if row.steam_id is not None else None,
        "discord_id": str(row.discord_id) if row.discord_id is not None else None,
        "rank": code_to_level(row.current_rank),
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
    steam_id: str,
    discord_id: Optional[str] = None,
    rank: int = 0,
    notes: Optional[str] = None,
    enlisted: bool = False
) -> Optional[Dict[str, Any]]:
    """Create a new user in the database."""
    try:
        steam = int(steam_id)
        discord = int(discord_id) if discord_id else None
        code = level_to_code(rank)
    except (ValueError, TypeError, KeyError):
        return None

    try:
        db = await get_shared_db_manager()

        async with db.get_session() as session:
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

            sr_id = (await session.execute(
                text("""INSERT INTO military.service_records
                        (player_identity_id, organization_id, current_rank, service_status)
                        SELECT :pid, o.id, :code, 'active'
                        FROM public.identities_organizations o WHERE o.name = :org
                        RETURNING id"""),
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
                    text("""UPDATE public.identities_player
                            SET details = coalesce(details, '{}'::jsonb) || jsonb_build_object('notes', CAST(:notes AS text))
                            WHERE id = :id"""),
                    {"notes": notes, "id": ident.id},
                )
            await session.commit()

            return {
                "id": ident.id,
                "name": name,
                "steam_id": str(steam),
                "discord_id": str(discord) if discord is not None else None,
                "rank": rank,
                "enlisted": bool(enlisted),
            }

    except Exception as e:
        print(f"Error creating user: {e}")
        return None


async def get_user_info(identifier: str) -> Optional[Dict[str, Any]]:
    """Get user information by Discord ID or Steam ID."""
    try:
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            row = await _find(session, identifier)
            return _full(row) if row else None
    except Exception as e:
        print(f"Error getting user info: {e}")
        return None


async def modify_user(
    identifier: str,
    name: Optional[str] = None,
    rank: Optional[int] = None,
    notes: Optional[str] = None,
    enlisted: Optional[bool] = None,
    reason: Optional[str] = None
) -> bool:
    """Modify user information."""
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
                code = level_to_code(rank)
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
                    text("""UPDATE public.identities_player
                            SET details = coalesce(details, '{}'::jsonb) || jsonb_build_object('notes', CAST(:notes AS text))
                            WHERE id = :id"""),
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
                    {"sr": row.sr_id, "etype": etype, "code": row.current_rank if rank is None else level_to_code(rank)},
                )
            await session.commit()
            return True

    except Exception as e:
        print(f"Error modifying user: {e}")
        return False


async def search_users(query: str) -> List[Dict[str, Any]]:
    """Search users by name."""
    try:
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            res = await session.execute(
                text(_BOT_USER + " WHERE p.alias ILIKE '%' || :q || '%' LIMIT 20"), {"org": ORG, "q": query}
            )
            return [_brief(r) for r in res]
    except Exception as e:
        print(f"Error searching users: {e}")
        return []


async def get_user_stats() -> Dict[str, Any]:
    """Get user statistics."""
    try:
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            rows = (await session.execute(text(_BOT_USER), {"org": ORG})).all()
            return {
                "total_users": len(rows),
                "enlisted_users": sum(_is_enlisted(r) for r in rows),
            }
    except Exception as e:
        print(f"Error getting user stats: {e}")
        return {"total_users": 0, "enlisted_users": 0}


async def get_user_count_by_rank() -> Dict[int, int]:
    """Map rank level to the number of bot users holding it."""
    try:
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            res = await session.execute(
                text("""SELECT sr.current_rank, count(*) AS n
                        FROM military.service_records sr
                        JOIN public.identities_organizations o ON o.id = sr.organization_id AND o.name = :org
                        WHERE sr.player_identity_id IS NOT NULL
                        GROUP BY sr.current_rank"""),
                {"org": ORG},
            )
            return {code_to_level(r.current_rank): r.n for r in res if r.current_rank}
    except Exception as e:
        print(f"Error getting rank counts: {e}")
        return {}


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
            if steam is None:
                # fab_ensure_player_account rejects a NULL steam_id, so insert the identity directly
                if not (await session.execute(
                    text("SELECT 1 FROM public.identities_player WHERE discord_id = :d"), {"d": discord}
                )).first():
                    await session.execute(
                        text("INSERT INTO public.identities_player (alias, discord_id) VALUES (nullif(:n, ''), :d)"),
                        {"n": name, "d": discord},
                    )
                await session.commit()
                return True
            await _claim_null_steam(session, discord, steam)
            if (await session.execute(
                text("SELECT 1 FROM public.identities_player WHERE discord_id = :d AND steam_id IS DISTINCT FROM :s"),
                {"d": discord, "s": steam},
            )).first():
                return False
            await session.execute(
                text("SELECT public.fab_ensure_player_account(:name, :steam, :discord)"),
                {"name": name, "steam": steam, "discord": discord},
            )
            ident = (await session.execute(
                text("SELECT id, discord_id FROM public.identities_player WHERE steam_id = :s"), {"s": steam}
            )).one()
            if ident.discord_id is None:
                await session.execute(
                    text("UPDATE public.identities_player SET discord_id = :d WHERE id = :id"),
                    {"d": discord, "id": ident.id},
                )
            elif ident.discord_id != discord:
                return False  # rolled back on session close
            await session.commit()
            return True
    except Exception as e:
        print(f"Error ensuring player identity: {e}")
        return False


async def create_service_record(discord_id: str, rank: int) -> str:
    """Create only the service record (no events) for an existing identity:
    'created', 'already_exists', 'no_identity' or 'error'."""
    try:
        discord = int(discord_id)
        code = level_to_code(rank)
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
            await session.execute(
                text("""INSERT INTO military.service_records (player_identity_id, organization_id, current_rank, service_status)
                        VALUES (:p, :o, :r, 'active')"""),
                {"p": pid, "o": org, "r": code},
            )
            await session.commit()
            return "created"
    except Exception as e:
        print(f"Error creating service record: {e}")
        return "error"


async def set_steam_id(discord_id: str, steam_id: str) -> str:
    """Attach a Steam ID to an existing identity: 'updated', 'already_set', 'no_identity',
    'different_steam' (identity already has another), 'steam_in_use' (another identity has it) or 'error'."""
    try:
        discord, steam = int(discord_id), int(steam_id)
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            row = (await session.execute(
                text("SELECT id, steam_id FROM public.identities_player WHERE discord_id = :d"), {"d": discord}
            )).first()
            if row is None:
                return "no_identity"
            if row.steam_id == steam:
                return "already_set"
            if row.steam_id is not None:
                return "different_steam"
            if (await session.execute(
                text("SELECT 1 FROM public.identities_player WHERE steam_id = :s"), {"s": steam}
            )).first():
                return "steam_in_use"
            await session.execute(
                text("UPDATE public.identities_player SET steam_id = :s WHERE id = :id"), {"s": steam, "id": row.id}
            )
            await session.commit()
            return "updated"
    except Exception as e:
        print(f"Error setting steam id: {e}")
        return "error"


async def enlist_member(discord_id: str, rank: int = 0) -> str:
    """Enlist an existing identity: 'enlisted', 'already_enlisted', 'no_identity' or 'error'."""
    try:
        discord = int(discord_id)
        code = level_to_code(rank)
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            pid = (await session.execute(
                text("SELECT id FROM public.identities_player WHERE discord_id = :d"), {"d": discord}
            )).scalar_one_or_none()
            if pid is None:
                return "no_identity"

            sr = (await session.execute(
                text("""SELECT sr.id, sr.current_rank, ev.event_type
                        FROM military.service_records sr
                        JOIN public.identities_organizations o ON o.id = sr.organization_id AND o.name = :org
                        LEFT JOIN LATERAL (
                            SELECT e.event_type FROM military.service_events e
                            WHERE e.service_record_id = sr.id
                              AND e.event_type IN ('enlisted', 'reenlisted', 'discharged')
                            ORDER BY e.occured_at DESC, e.id DESC LIMIT 1
                        ) ev ON true
                        WHERE sr.player_identity_id = :pid"""),
                {"org": ORG, "pid": pid},
            )).first()

            if sr is None:
                sr_id = (await session.execute(
                    text("""INSERT INTO military.service_records
                            (player_identity_id, organization_id, current_rank, service_status)
                            SELECT :pid, o.id, :code, 'active'
                            FROM public.identities_organizations o WHERE o.name = :org
                            RETURNING id"""),
                    {"pid": pid, "code": code, "org": ORG},
                )).scalar_one()
                etype, ev_rank = "enlisted", code
            elif sr.event_type in ("enlisted", "reenlisted"):
                return "already_enlisted"
            else:
                sr_id, ev_rank = sr.id, sr.current_rank
                had_discharge = (await session.execute(
                    text("SELECT 1 FROM military.service_events WHERE service_record_id = :sr AND event_type = 'discharged' LIMIT 1"),
                    {"sr": sr_id},
                )).first() is not None
                etype = "reenlisted" if had_discharge else "enlisted"

            await session.execute(
                text("""INSERT INTO military.service_events (service_record_id, event_type, rank, occured_at)
                        VALUES (:sr, :etype, :code, now())"""),
                {"sr": sr_id, "etype": etype, "code": ev_rank},
            )
            await session.commit()
            return "enlisted"
    except Exception as e:
        print(f"Error enlisting member: {e}")
        return "error"
