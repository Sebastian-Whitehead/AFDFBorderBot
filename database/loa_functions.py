"""
LOA (Leave of Absence) database functions for AFDFBorderBot.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date

from sqlalchemy.future import select
from sqlalchemy import and_, text, update

from .db_manager import get_db_manager
from .models import LOARequest

logger = logging.getLogger(__name__)


class LOAManager:
    """LOA database operations manager."""
    
    @staticmethod
    async def create_or_update_loa(discord_id: str, username: str, end_date: str, reason: Optional[str] = None) -> tuple[bool, str]:
        """Create a new LOA or update an existing active one."""
        try:
            db = await get_db_manager()
            
            async with db.get_session() as session:
                # Check if user has an active LOA
                result = await session.execute(
                    select(LOARequest).where(
                        and_(LOARequest.discord_id == discord_id, LOARequest.status == 'active')
                    )
                )
                existing_loa = result.scalar_one_or_none()
                
                if existing_loa:
                    # Update existing LOA
                    existing_loa.end_date = end_date
                    if reason is not None:
                        existing_loa.reason = reason
                    existing_loa.last_modified = datetime.utcnow()
                    await session.commit()
                    return True, "updated"
                else:
                    # Create new LOA
                    loa = LOARequest(
                        discord_id=discord_id,
                        username=username,
                        start_date=datetime.utcnow().date(),
                        end_date=end_date,
                        reason=reason
                    )
                    session.add(loa)
                    await session.commit()
                    return False, "submitted"
                    
        except Exception as e:
            logger.error(f"Error creating/updating LOA: {e}")
            return False, "failed"

    @staticmethod
    async def get_active_loa_by_discord_id(discord_id: str) -> Optional[Dict[str, Any]]:
        """Get active LOA by Discord ID."""
        try:
            db = await get_db_manager()
            
            async with db.get_session() as session:
                result = await session.execute(
                    select(LOARequest).where(
                        and_(LOARequest.discord_id == discord_id, LOARequest.status == 'active')
                    )
                )
                loa = result.scalar_one_or_none()
                
                if not loa:
                    return None
                    
                return {
                    "id": loa.id,
                    "discord_id": loa.discord_id,
                    "username": loa.username,
                    "start_date": loa.start_date,
                    "end_date": loa.end_date,
                    "reason": loa.reason,
                    "status": loa.status,
                    "submitted_at": loa.submitted_at,
                    "last_modified": loa.last_modified
                }
                
        except Exception as e:
            logger.error(f"Error getting active LOA: {e}")
            return None

    @staticmethod
    async def get_all_active_loas() -> List[Dict[str, Any]]:
        """Get all active LOAs."""
        try:
            db = await get_db_manager()
            
            async with db.get_session() as session:
                result = await session.execute(
                    select(LOARequest).where(LOARequest.status == 'active').order_by(LOARequest.submitted_at.desc())
                )
                loas = result.scalars().all()
                
                return [
                    {
                        "id": loa.id,
                        "discord_id": loa.discord_id,
                        "username": loa.username,
                        "start_date": loa.start_date,
                        "end_date": loa.end_date,
                        "reason": loa.reason,
                        "status": loa.status,
                        "submitted_at": loa.submitted_at,
                        "last_modified": loa.last_modified
                    }
                    for loa in loas
                ]
                
        except Exception as e:
            logger.error(f"Error getting all active LOAs: {e}")
            return []

    @staticmethod
    async def cancel_loa(discord_id: str) -> bool:
        """Cancel active LOA for a user."""
        try:
            db = await get_db_manager()
            
            async with db.get_session() as session:
                result = await session.execute(
                    select(LOARequest).where(
                        and_(LOARequest.discord_id == discord_id, LOARequest.status == 'active')
                    )
                )
                loa = result.scalar_one_or_none()
                
                if loa:
                    loa.status = 'cancelled'
                    loa.last_modified = datetime.utcnow()
                    await session.commit()
                    return True
                return False
                
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
            
            # Try MM/DD/YYYY format
            try:
                return datetime.strptime(end_date_str, "%m/%d/%Y").date()
            except ValueError:
                pass
                
            return None
            
        except Exception as e:
            logger.error(f"Error parsing end date: {e}")
            return None

    @staticmethod
    async def cleanup_expired_loas():
        """Mark expired LOAs as expired using pure SQLAlchemy ORM approach."""
        try:
            db = await get_db_manager()
            
            async with db.get_session() as session:
                # Get all active LOAs
                result = await session.execute(
                    select(LOARequest).where(LOARequest.status == 'active')
                )
                active_loas = result.scalars().all()
                
                current_date = date.today()
                expired_count = 0
                
                # Process each LOA using our existing date parsing logic
                for loa in active_loas:
                    end_date = await LOAManager.parse_end_date(loa.end_date)
                    if end_date and end_date < current_date:
                        loa.status = 'expired'
                        loa.last_modified = datetime.utcnow()
                        expired_count += 1
                
                if expired_count > 0:
                    await session.commit()
                    logger.info(f"Marked {expired_count} LOAs as expired")
                
                # Alternative: Raw SQL for bulk operations (more efficient for large datasets)
                # This is the original approach - commented out but kept for reference
                # await session.execute(
                #     text("""
                #         UPDATE loa_requests 
                #         SET status = 'expired', last_modified = CURRENT_TIMESTAMP
                #         WHERE status = 'active' 
                #         AND (
                #             (end_date ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' AND end_date::date < CURRENT_DATE)
                #             OR
                #             (end_date ~ '^[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}$' AND 
                #              TO_DATE(end_date, 'MM/DD/YYYY') < CURRENT_DATE)
                #         )
                #     """)
                # )
                
        except Exception as e:
            logger.error(f"Error cleaning up expired LOAs: {e}")
