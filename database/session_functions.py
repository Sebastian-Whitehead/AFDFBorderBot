"""Sessions: military.sessions create / end / list / edit and the open-session lookup."""

import logging
from typing import Any, Dict, Optional

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from .db_manager import get_shared_db_manager

logger = logging.getLogger(__name__)


async def create_session(name: str, operation: Optional[str] = None, description: Optional[str] = None,
                         start_at=None, external_event_id: Optional[str] = None, timeline: str = "A") -> Optional[int]:
    """Insert a military.sessions row (start_at defaults to now). Returns the new id, or None on error."""
    try:
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            new_id = (await session.execute(
                text("""INSERT INTO military.sessions (session_name, operation, description, start_at, external_event_id, timeline)
                        VALUES (:n, :o, :d, COALESCE(:s, now()), :e, :t) RETURNING id"""),
                {"n": name, "o": operation, "d": description, "s": start_at, "e": external_event_id, "t": timeline},
            )).scalar_one()
            await session.commit()
            return new_id
    except Exception as e:
        logger.exception(f"Error creating session: {e}")
        return None


async def end_latest_session(end_at=None):
    """Set end_at (default now) on the open session with the latest start_at.
    Returns (status, row): 'ended', 'none_open', 'before_start' or 'error'; row has id, session_name, end_at."""
    try:
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            row = (await session.execute(text(
                """SELECT id, session_name, start_at, COALESCE(:e, now()) AS end_at FROM military.sessions
                   WHERE end_at IS NULL ORDER BY start_at DESC LIMIT 1 FOR UPDATE"""), {"e": end_at})).mappings().first()
            if row is None:
                return "none_open", None
            if row["end_at"] < row["start_at"]:
                return "before_start", dict(row)
            await session.execute(text("UPDATE military.sessions SET end_at = :e, updated_at = now() WHERE id = :i"),
                                  {"e": row["end_at"], "i": row["id"]})
            await session.commit()
            return "ended", dict(row)
    except Exception as e:
        logger.exception(f"Error ending session: {e}")
        return "error", None


async def get_open_session() -> Optional[Dict[str, Any]]:
    """Open session (end_at is null) with the latest start_at, or None (also on error)."""
    try:
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            row = (await session.execute(text(
                "SELECT id, session_name FROM military.sessions WHERE end_at IS NULL ORDER BY start_at DESC LIMIT 1"
            ))).mappings().first()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error getting open session: {e}")
        return None


PAGE_SIZE = 10


async def list_sessions(timeline: str, page: int) -> Optional[tuple]:
    """One page of sessions for a timeline (case-insensitive), newest start first.
    Returns (rows, total_count), or None on error."""
    try:
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            total = (await session.execute(text(
                "SELECT count(*) FROM military.sessions WHERE lower(timeline) = lower(:t)"), {"t": timeline})).scalar_one()
            rows = (await session.execute(text("""
                SELECT id, timeline, session_name, operation, start_at, end_at FROM military.sessions
                WHERE lower(timeline) = lower(:t) ORDER BY start_at DESC, id DESC LIMIT :n OFFSET :o"""),
                {"t": timeline, "n": PAGE_SIZE, "o": (page - 1) * PAGE_SIZE})).mappings().all()
            return [dict(r) for r in rows], total
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        return None


_EDITABLE = {"session_name", "operation", "description", "timeline", "start_at", "end_at"}


async def update_session(session_id: int, **changes) -> tuple:
    """Change the given columns (None values are ignored) and bump updated_at.
    Returns (status, row): 'updated', 'no_changes', 'not_found', 'bad_dates' (end before start) or 'error'."""
    changes = {k: v for k, v in changes.items() if v is not None}
    assert set(changes) <= _EDITABLE, "unknown session column"  # keys go into the SQL, so only whitelisted names
    try:
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            cur = (await session.execute(text(
                "SELECT id, session_name, operation, description, timeline, start_at, end_at "
                "FROM military.sessions WHERE id = :i FOR UPDATE"), {"i": session_id})).mappings().first()
            if cur is None:
                return "not_found", None
            new = {**cur, **changes}
            if new["end_at"] is not None and new["end_at"] < new["start_at"]:
                return "bad_dates", dict(cur)
            if not changes:
                return "no_changes", dict(cur)
            sets = ", ".join(f"{k} = :{k}" for k in changes)
            await session.execute(text(f"UPDATE military.sessions SET {sets}, updated_at = now() WHERE id = :i"),
                                  {**changes, "i": session_id})
            await session.commit()
            return "updated", new
    except Exception as e:
        logger.error(f"Error updating session: {e}")
        return "error", None


async def get_session_for_delete(session_id: int) -> tuple:
    """Returns (status, row): 'found' (row has id, session_name, start_at, attendance_count), 'not_found' or 'error'."""
    try:
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            row = (await session.execute(text(
                "SELECT s.id, s.session_name, s.start_at, "
                "(SELECT count(*) FROM military.attendance a WHERE a.session_id = s.id) AS attendance_count "
                "FROM military.sessions s WHERE s.id = :i"), {"i": session_id})).mappings().first()
            return ("found", dict(row)) if row else ("not_found", None)
    except Exception as e:
        logger.error(f"Error reading session for delete: {e}")
        return "error", None


async def delete_session(session_id: int) -> str:
    """Delete a session row. Returns 'deleted', 'not_found', 'blocked' (attendance rows reference it:
    the FK is ON DELETE RESTRICT, so they are never removed here) or 'error'."""
    try:
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            res = await session.execute(text("DELETE FROM military.sessions WHERE id = :i"), {"i": session_id})
            await session.commit()
            return "deleted" if res.rowcount else "not_found"
    except IntegrityError:
        return "blocked"
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        return "error"
