"""Attendance helpers: military.sessions (open session) and military.attendance."""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from .db_manager import get_shared_db_manager

logger = logging.getLogger(__name__)

ORG = "AFDF-Para Raiders"


async def load_session_attendance(session_id: int) -> Optional[tuple]:
    """(session or None, saved attendance rows [{discord_id, status, notes}]) for a session, or None on error.
    Rows for players without a Discord id are left out."""
    try:
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            sess = (await session.execute(text(
                "SELECT id, session_name FROM military.sessions WHERE id = :i"), {"i": session_id})).mappings().first()
            if sess is None:
                return None, []
            rows = (await session.execute(text("""
                SELECT p.discord_id, a.attendance_status::text AS status, a.notes
                FROM military.attendance a
                JOIN military.service_records sr ON sr.id = a.service_record_id
                JOIN public.identities_player p ON p.id = sr.player_identity_id
                WHERE a.session_id = :i AND p.discord_id IS NOT NULL ORDER BY a.id"""), {"i": session_id})).all()
            return dict(sess), [{"discord_id": str(r.discord_id), "status": r.status, "notes": r.notes} for r in rows]
    except Exception as e:
        logger.error(f"Error loading session attendance: {e}")
        return None


async def find_unaccounted(discord_ids: List[str]) -> Optional[List[str]]:
    """Discord ids of active service records that are not in discord_ids. None on error."""
    try:
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            rows = await session.execute(text("""
                SELECT p.discord_id FROM military.service_records sr
                JOIN public.identities_player p ON p.id = sr.player_identity_id
                JOIN public.identities_organizations o ON o.id = sr.organization_id
                WHERE o.name = :org AND sr.service_status = 'active' AND p.discord_id IS NOT NULL
                  AND NOT (p.discord_id = ANY(CAST(:ids AS bigint[])))
                ORDER BY p.discord_id"""), {"org": ORG, "ids": [int(d) for d in discord_ids]})
            return [str(r.discord_id) for r in rows]
    except Exception as e:
        logger.error(f"Error finding unaccounted members: {e}")
        return None


async def submit_attendance(session_id: int, rows: List[Dict[str, Any]], recorded_by: str) -> Optional[Dict[str, List[str]]]:
    """Upsert one military.attendance row per {discord_id, status, notes}, in one transaction.
    Returns {'saved': [...], 'skipped': [...]} (skipped = no service record), or None on error."""
    saved, skipped = [], []
    try:
        db = await get_shared_db_manager()
        async with db.get_session() as session:
            for r in rows:
                res = await session.execute(text("""
                    INSERT INTO military.attendance (service_record_id, session_id, attendance_status, notes, recorded_by)
                    SELECT sr.id, :sid, CAST(:st AS military.attendance_status), :n, :by
                    FROM military.service_records sr
                    JOIN public.identities_player p ON p.id = sr.player_identity_id
                    JOIN public.identities_organizations o ON o.id = sr.organization_id
                    WHERE p.discord_id = :d AND o.name = :org
                    ON CONFLICT (service_record_id, session_id) DO UPDATE
                      SET attendance_status = EXCLUDED.attendance_status, notes = EXCLUDED.notes,
                          recorded_at = now(), recorded_by = EXCLUDED.recorded_by"""),
                    {"sid": session_id, "st": r["status"], "n": r.get("notes"), "by": recorded_by,
                     "d": int(r["discord_id"]), "org": ORG})
                (saved if res.rowcount else skipped).append(r["discord_id"])
            await session.commit()
        return {"saved": saved, "skipped": skipped}
    except Exception as e:
        logger.error(f"Error submitting attendance: {e}")
        return None
