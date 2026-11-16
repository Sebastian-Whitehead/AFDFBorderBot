"""Leadership record corrections: service events, direct rank set, identity name/notes."""

from typing import Optional

from sqlalchemy import text

from .db_manager import get_shared_db_manager
from .rank_codes import is_valid_rank
from .user_functions import _service_state

# editable service_events columns; event_type is deliberately absent
_EVENT_COLUMNS = {"notes": "notes = :notes", "status": "status = :status", "rank": "rank = :rank",
                  "occured_at": "occured_at = :occured_at", "details": "details = CAST(:details AS jsonb)"}


async def get_service_event(event_id: int):
    """('ok', row dict with event_type/occured_at/rank), ('not_found', None) or ('error', None)."""
    try:
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            row = (await session.execute(
                text("SELECT id, event_type, occured_at, rank FROM military.service_events WHERE id = :id"), {"id": event_id}
            )).first()
            return ("ok", dict(row._mapping)) if row else ("not_found", None)
    except Exception as e:
        print(f"Error getting service event: {e}")
        return "error", None


async def update_service_event(event_id: int, **fields) -> str:
    """Change the given columns (notes, status, rank, occured_at, details as JSON string; None = leave alone):
    'updated', 'no_changes', 'not_found' or 'error'."""
    changes = {k: v for k, v in fields.items() if v is not None}
    if not changes or not set(changes) <= set(_EVENT_COLUMNS):
        return "no_changes" if not changes else "error"
    try:
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            updated = (await session.execute(
                text(f"UPDATE military.service_events SET {', '.join(_EVENT_COLUMNS[k] for k in changes)} WHERE id = :id RETURNING id"),
                {**changes, "id": event_id},
            )).first()
            if updated is None:
                return "not_found"
            await session.commit()
            return "updated"
    except Exception as e:
        print(f"Error updating service event: {e}")
        return "error"


async def delete_service_event(event_id: int) -> str:
    """'deleted', 'not_found' or 'error'."""
    try:
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            gone = (await session.execute(
                text("DELETE FROM military.service_events WHERE id = :id RETURNING id"), {"id": event_id}
            )).first()
            if gone is None:
                return "not_found"
            await session.commit()
            return "deleted"
    except Exception as e:
        print(f"Error deleting service event: {e}")
        return "error"


async def set_member_rank(discord_id: str, rank: str, notes: Optional[str] = None):
    """Set current_rank directly (no promotion rules) and log a rank_changed event.
    Returns (status, old_rank): 'ok', 'no_record', 'same_rank' or 'error'."""
    if not is_valid_rank(rank):
        return "error", None
    try:
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            _, sr = await _service_state(session, int(discord_id))
            if sr is None:
                return "no_record", None
            if sr.current_rank == rank:
                return "same_rank", sr.current_rank
            await session.execute(
                text("UPDATE military.service_records SET current_rank = :rank, updated_at = now() WHERE id = :sr"),
                {"rank": rank, "sr": sr.id},
            )
            await session.execute(
                text("""INSERT INTO military.service_events (service_record_id, event_type, rank, notes, occured_at)
                        VALUES (:sr, 'rank_changed', :rank, :notes, now())"""),
                {"sr": sr.id, "rank": rank, "notes": notes},
            )
            await session.commit()
            return "ok", sr.current_rank
    except Exception as e:
        print(f"Error setting rank: {e}")
        return "error", None


async def update_member(discord_id: str, name: Optional[str] = None, notes: Optional[str] = None) -> str:
    """Edit the player's alias and/or details notes: 'updated', 'no_changes', 'no_identity' or 'error'."""
    if name is None and notes is None:
        return "no_changes"
    try:
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            pid = (await session.execute(
                text("SELECT id FROM public.identities_player WHERE discord_id = :d"), {"d": int(discord_id)}
            )).scalar_one_or_none()
            if pid is None:
                return "no_identity"
            if name is not None:
                await session.execute(
                    text("UPDATE public.identities_player SET alias = :name WHERE id = :id"), {"name": name, "id": pid})
            if notes is not None:
                await session.execute(
                    text("""UPDATE public.identities_player
                            SET details = coalesce(details, '{}'::jsonb) || jsonb_build_object('notes', CAST(:notes AS text))
                            WHERE id = :id"""),
                    {"notes": notes, "id": pid},
                )
            await session.commit()
            return "updated"
    except Exception as e:
        print(f"Error updating member: {e}")
        return "error"
