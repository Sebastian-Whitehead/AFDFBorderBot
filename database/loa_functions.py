"""
LOA (Leave of Absence) database functions for AFDFBorderBot
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from sqlalchemy import text

from .db_manager import get_db_manager

logger = logging.getLogger(__name__)


class LOAManager:
    """Manager for LOA database operations."""
    
    @staticmethod
    async def create_or_update_loa(discord_id: str, username: str, end_date: str, reason: Optional[str] = None) -> tuple[bool, str]:
        """
        Create a new LOA or update an existing active one.
        
        Returns:
            tuple: (is_update, action_text)
        """
        try:
            db = await get_db_manager()
            
            # Check if user has an active LOA
            existing_loa = await LOAManager.get_active_loa_by_discord_id(discord_id)
            
            if existing_loa:
                # Update existing LOA
                # If no reason provided, keep the existing reason
                updated_reason = reason if reason is not None else existing_loa['reason']
                
                query = """
                UPDATE loa_requests 
                SET end_date = :end_date, 
                    reason = :reason, 
                    last_modified = CURRENT_TIMESTAMP
                WHERE discord_id = :discord_id AND status = 'active'
                """
                params = {
                    'discord_id': discord_id,
                    'end_date': end_date,
                    'reason': updated_reason
                }
                await db.execute_dml_query(query, params)
                return True, "updated"
            else:
                # Create new LOA
                query = """
                INSERT INTO loa_requests (discord_id, username, start_date, end_date, reason)
                VALUES (:discord_id, :username, CURRENT_DATE, :end_date, :reason)
                """
                params = {
                    'discord_id': discord_id,
                    'username': username,
                    'end_date': end_date,
                    'reason': reason
                }
                await db.execute_dml_query(query, params)
                return False, "submitted"
                
        except Exception as e:
            logger.error(f"Error creating/updating LOA: {e}")
            raise
    
    @staticmethod
    async def get_active_loa_by_discord_id(discord_id: str) -> Optional[Dict[str, Any]]:
        """Get active LOA for a specific Discord user."""
        try:
            db = await get_db_manager()
            query = """
            SELECT * FROM loa_requests 
            WHERE discord_id = :discord_id AND status = 'active'
            ORDER BY created_at DESC
            LIMIT 1
            """
            params = {'discord_id': discord_id}
            results = await db.execute_select_query(query, params)
            return results[0] if results else None
            
        except Exception as e:
            logger.error(f"Error fetching LOA for user {discord_id}: {e}")
            raise
    
    @staticmethod
    async def get_all_active_loas() -> List[Dict[str, Any]]:
        """Get all active LOA requests."""
        try:
            db = await get_db_manager()
            query = """
            SELECT * FROM loa_requests 
            WHERE status = 'active'
            ORDER BY created_at DESC
            """
            results = await db.execute_select_query(query)
            return results
            
        except Exception as e:
            logger.error(f"Error fetching all active LOAs: {e}")
            raise
    
    @staticmethod
    async def cancel_loa(discord_id: str) -> bool:
        """
        Cancel an active LOA for a user.
        
        Returns:
            bool: True if LOA was found and cancelled, False if no active LOA
        """
        try:
            db = await get_db_manager()
            
            # Check if user has an active LOA
            existing_loa = await LOAManager.get_active_loa_by_discord_id(discord_id)
            if not existing_loa:
                return False
            
            # Cancel the LOA
            query = """
            UPDATE loa_requests 
            SET status = 'cancelled', last_modified = CURRENT_TIMESTAMP
            WHERE discord_id = :discord_id AND status = 'active'
            """
            params = {'discord_id': discord_id}
            await db.execute_dml_query(query, params)
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling LOA for user {discord_id}: {e}")
            raise
    
    @staticmethod
    async def cleanup_expired_loas():
        """Mark LOAs as expired if their end date has passed."""
        try:
            db = await get_db_manager()
            
            # This is a bit tricky since end_date is stored as TEXT to support multiple formats
            # We'll need to parse dates and compare
            query = """
            UPDATE loa_requests 
            SET status = 'expired', last_modified = CURRENT_TIMESTAMP
            WHERE status = 'active' 
            AND (
                -- Handle YYYY-MM-DD format
                (end_date ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' AND end_date::date < CURRENT_DATE)
                OR
                -- Handle MM/DD/YYYY format (convert to date)
                (end_date ~ '^[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}$' AND 
                 TO_DATE(end_date, 'MM/DD/YYYY') < CURRENT_DATE)
            )
            """
            await db.execute_dml_query(query)
            logger.info("Cleaned up expired LOAs")
            
        except Exception as e:
            logger.error(f"Error cleaning up expired LOAs: {e}")
            # Don't raise here since this is cleanup - log and continue
    
    @staticmethod
    async def parse_end_date(end_date_str: str) -> Optional[date]:
        """Parse end date string to date object, supporting multiple formats."""
        try:
            if '/' in end_date_str:  # MM/DD/YYYY format
                return datetime.strptime(end_date_str, "%m/%d/%Y").date()
            else:  # YYYY-MM-DD format
                return datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            logger.warning(f"Could not parse end date: {end_date_str}")
            return None
