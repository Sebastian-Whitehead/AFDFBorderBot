"""
Core User Database Functions for AFDFBorderBot

Simple functions for creating, modifying, and retrieving user data using SQLAlchemy.
"""

from typing import Optional, Dict, Any, Union, List
from datetime import datetime
from decimal import Decimal

from sqlalchemy.future import select
from sqlalchemy import or_, func

from .db_manager import get_db_manager
from .models import User


async def create_user(
    name: str,
    steam_id: str,
    discord_id: Optional[str] = None,
    rank: int = 0,
    money: Union[float, Decimal] = 0,
    notes: Optional[str] = None,
    enlisted: bool = False
) -> Optional[Dict[str, Any]]:
    """Create a new user in the database."""
    try:
        db = await get_db_manager()
        
        if isinstance(money, float):
            money = Decimal(str(money))
        
        async with db.get_session() as session:
            # Check if user exists
            result = await session.execute(
                select(User).where(or_(User.steam_id == steam_id, User.discord_id == discord_id))
            )
            if result.scalar_one_or_none():
                return None
            
            user = User(
                name=name,
                steam_id=steam_id,
                discord_id=discord_id,
                rank=rank,
                money=money,
                notes=notes,
                enlisted_at=datetime.utcnow() if enlisted else None
            )
            session.add(user)
            await session.commit()
            
            return {
                "id": user.id,
                "name": user.name,
                "steam_id": user.steam_id,
                "discord_id": user.discord_id,
                "rank": user.rank,
                "money": user.money,
                "enlisted": user.enlisted_at is not None
            }
            
    except Exception as e:
        print(f"Error creating user: {e}")
        return None


async def get_user_info(identifier: str) -> Optional[Dict[str, Any]]:
    """Get user information by Discord ID or Steam ID."""
    try:
        db = await get_db_manager()
        
        async with db.get_session() as session:
            result = await session.execute(
                select(User).where(or_(User.discord_id == identifier, User.steam_id == identifier))
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return None
                
            return {
                "id": user.id,
                "name": user.name,
                "steam_id": user.steam_id,
                "discord_id": user.discord_id,
                "joined_at": user.joined_at,
                "enlisted_at": user.enlisted_at,
                "money": user.money,
                "rank": user.rank,
                "notes": user.notes,
                "achievements": user.achievements,
                "last_death": user.last_death,
                "deaths": user.deaths,
                "reprimands": user.reprimands,
                "extra_data": user.extra_data,
                "enlisted": user.enlisted_at is not None
            }
            
    except Exception as e:
        print(f"Error getting user info: {e}")
        return None


async def modify_user(
    identifier: str,
    name: Optional[str] = None,
    rank: Optional[int] = None,
    money: Optional[Union[float, Decimal]] = None,
    notes: Optional[str] = None,
    enlisted: Optional[bool] = None
) -> bool:
    """Modify user information."""
    try:
        db = await get_db_manager()
        
        async with db.get_session() as session:
            result = await session.execute(
                select(User).where(or_(User.discord_id == identifier, User.steam_id == identifier))
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return False
            
            if name is not None:
                user.name = name
            if rank is not None:
                user.rank = rank
            if money is not None:
                user.money = Decimal(str(money)) if isinstance(money, float) else money
            if notes is not None:
                user.notes = notes
            if enlisted is not None:
                user.enlisted_at = datetime.utcnow() if enlisted else None
                
            await session.commit()
            return True
            
    except Exception as e:
        print(f"Error modifying user: {e}")
        return False


async def search_users(query: str) -> List[Dict[str, Any]]:
    """Search users by name."""
    try:
        db = await get_db_manager()
        
        async with db.get_session() as session:
            result = await session.execute(
                select(User).where(User.name.ilike(f'%{query}%')).limit(20)
            )
            users = result.scalars().all()
            
            return [
                {
                    "id": user.id,
                    "name": user.name,
                    "steam_id": user.steam_id,
                    "discord_id": user.discord_id,
                    "rank": user.rank,
                    "money": user.money,
                    "enlisted": user.enlisted_at is not None
                }
                for user in users
            ]
            
    except Exception as e:
        print(f"Error searching users: {e}")
        return []


async def get_user_stats() -> Dict[str, Any]:
    """Get user statistics."""
    try:
        db = await get_db_manager()
        
        async with db.get_session() as session:
            total_users = await session.execute(select(func.count(User.id)))
            enlisted_users = await session.execute(
                select(func.count(User.id)).where(User.enlisted_at.is_not(None))
            )
            
            return {
                "total_users": total_users.scalar(),
                "enlisted_users": enlisted_users.scalar()
            }
            
    except Exception as e:
        print(f"Error getting user stats: {e}")
        return {"total_users": 0, "enlisted_users": 0}
