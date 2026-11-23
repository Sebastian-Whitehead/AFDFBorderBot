"""
LOA (Leave of Absence) database functions for AFDFBorderBot.
Backed by military.leave_requests, keyed by service record.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date

from sqlalchemy import text

from .db_manager import get_shared_db_manager
from .user_functions import ORG as ORG_NAME

logger = logging.getLogger(__name__)


_SR_ID = """
    SELECT sr.id FROM military.service_records sr
    JOIN public.identities_player p ON p.id = sr.player_identity_id
    JOIN public.identities_organizations o ON o.id = sr.organization_id
    WHERE p.discord_id = :d AND o.name = :org
"""

_SELECT = """
    SELECT l.id, p.discord_id, l.submitted_by, l.start_date, l.end_date, l.reason,
           l.status, l.created_at, l.updated_at
    FROM military.leave_requests l
    JOIN military.service_records sr ON sr.id = l.service_record_id
    JOIN public.identities_player p ON p.id = sr.player_identity_id
    JOIN public.identities_organizations o ON o.id = sr.organization_id
    WHERE l.status = 'active' AND o.name = :org
"""


def _row(r) -> Dict[str, Any]:
    return {
        "id": r.id,
        "discord_id": str(r.discord_id),
        "username": r.submitted_by,
        "start_date": r.start_date,
        "end_date": r.end_date.isoformat(),
        "reason": r.reason,
        "status": r.status,
        "submitted_at": r.created_at,
        "last_modified": r.updated_at,
    }


class LOAManager:
    """LOA database operations manager."""

    @staticmethod
    async def create_or_update_loa(discord_id: str, username: str, end_date: str, reason: Optional[str] = None,
                                   start_date: Optional[str] = None) -> tuple[bool, str]:
        """Create a new LOA or update an existing active one. start_date defaults to today (or the end date if that is earlier)."""
        try:
            parsed = await LOAManager.parse_end_date(end_date)
            if parsed is None:
                return False, "failed"
            start = await LOAManager.parse_end_date(start_date) if start_date else None
            if start_date and (start is None or start > parsed):
                return False, "failed"
            db = await get_shared_db_manager()

            async with db.get_session() as session:
                sr_id = (await session.execute(
                    text(_SR_ID), {"d": int(discord_id), "org": ORG_NAME}
                )).scalar_one_or_none()
                if sr_id is None:
                    logger.warning(f"LOA failed: {discord_id} has no service record (not enlisted)")
                    return False, "failed"

                res = await session.execute(text("""
                    UPDATE military.leave_requests
                       SET end_date = :e, start_date = COALESCE(:s, LEAST(start_date, :e)),
                           reason = COALESCE(:r, reason), submitted_by = :u, updated_at = now()
                     WHERE service_record_id = :sr AND status = 'active'
                """), {"e": parsed, "s": start, "r": reason, "u": username, "sr": sr_id})
                if res.rowcount:
                    await session.commit()
                    return True, "updated"

                await session.execute(text("""
                    INSERT INTO military.leave_requests (service_record_id, start_date, end_date, reason, submitted_by)
                    VALUES (:sr, COALESCE(:s, LEAST(current_date, CAST(:e AS date))), :e, :r, :u)
                """), {"sr": sr_id, "s": start, "e": parsed, "r": reason, "u": username})
                await session.commit()
                return False, "submitted"

        except Exception as e:
            logger.error(f"Error creating/updating LOA: {e}")
            return False, "failed"

    @staticmethod
    async def get_active_loa_by_discord_id(discord_id: str) -> Optional[Dict[str, Any]]:
        """Get active LOA by Discord ID."""
        try:
            db = await get_shared_db_manager()

            async with db.get_session() as session:
                r = (await session.execute(
                    text(_SELECT + " AND p.discord_id = :d"),
                    {"d": int(discord_id), "org": ORG_NAME},
                )).first()
                return _row(r) if r else None

        except Exception as e:
            logger.error(f"Error getting active LOA: {e}")
            return None

    @staticmethod
    async def get_all_active_loas() -> List[Dict[str, Any]]:
        """Get all active LOAs."""
        try:
            db = await get_shared_db_manager()

            async with db.get_session() as session:
                result = await session.execute(
                    text(_SELECT + " ORDER BY l.created_at DESC"),
                    {"org": ORG_NAME},
                )
                return [_row(r) for r in result]

        except Exception as e:
            logger.error(f"Error getting all active LOAs: {e}")
            return []

    @staticmethod
    async def cancel_loa(discord_id: str) -> bool:
        """Cancel active LOA for a user."""
        try:
            db = await get_shared_db_manager()

            async with db.get_session() as session:
                res = await session.execute(text("""
                    UPDATE military.leave_requests
                       SET status = 'cancelled', updated_at = now()
                     WHERE status = 'active' AND service_record_id IN (""" + _SR_ID + ")"),
                    {"d": int(discord_id), "org": ORG_NAME})
                await session.commit()
                return res.rowcount > 0

        except Exception as e:
            logger.error(f"Error canceling LOA: {e}")
            return False

    @staticmethod
    async def parse_end_date(end_date_str: str) -> Optional[date]:
        """Parse end date string to date object."""
        try:
            # Try YYYY-MM-DD format
            try:
                return datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass
            
            # DD/MM/YYYY
            try:
                return datetime.strptime(end_date_str, "%d/%m/%Y").date()
            except ValueError:
                pass

            # DD/MM: next occurrence, today included (range covers 29/02 leap years)
            today = date.today()
            for year in range(today.year, today.year + 5):
                try:
                    d = datetime.strptime(f"{end_date_str}/{year}", "%d/%m/%Y").date()
                except ValueError:
                    continue
                if d >= today:
                    return d

            return None
            
        except Exception as e:
            logger.error(f"Error parsing end date: {e}")
            return None

    @staticmethod
    async def cleanup_expired_loas():
        """Mark expired LOAs as expired."""
        try:
            db = await get_shared_db_manager()

            async with db.get_session() as session:
                res = await session.execute(text("""
                    UPDATE military.leave_requests
                       SET status = 'expired', updated_at = now()
                     WHERE status = 'active' AND end_date < current_date
                """))
                await session.commit()
                if res.rowcount:
                    logger.info(f"Marked {res.rowcount} LOAs as expired")

        except Exception as e:
            logger.error(f"Error cleaning up expired LOAs: {e}")
