"""
Core User Database Functions for AFDFBorderBot

Simple functions for creating, modifying, and retrieving user data.
Works with either Discord ID or Steam ID as the identifying information.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional, Dict, Any, Union, List
from datetime import datetime, date
from decimal import Decimal

# Import from same directory
try:
    from .db_manager import get_db_manager
except ImportError:
    # Fallback for direct execution
    from db_manager import get_db_manager


async def create_user(
    name: str,
    steam_id: str,
    discord_id: Optional[str] = None,
    rank: int = 0,
    money: Union[float, Decimal] = 0,
    notes: Optional[str] = None,
    enlisted: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Create a new user in the database.
    
    Args:
        name: User's display name
        steam_id: Steam ID (must be unique)
        discord_id: Discord ID (optional, must be unique if provided)
        rank: Starting rank (0-10, default: 0)
        money: Starting money (default: 0)
        notes: Additional notes (optional)
        enlisted: Whether user is enlisted (default: False)
    
    Returns:
        Dict with user data if successful, None if failed
    """
    try:
        db = await get_db_manager()
        
        # Check if user already exists
        existing_user = await get_user_info(steam_id=steam_id)
        if existing_user:
            print(f"❌ User with Steam ID {steam_id} already exists")
            return None
        
        if discord_id:
            existing_discord = await get_user_info(discord_id=discord_id)
            if existing_discord:
                print(f"❌ User with Discord ID {discord_id} already exists")
                return None
        
        # Validate rank
        if not (0 <= rank <= 10):
            print(f"❌ Invalid rank: {rank}. Must be between 0-10")
            return None
        
        # Convert money to Decimal
        if isinstance(money, float):
            money = Decimal(str(money))
        
        # Create user
        enlisted_at = datetime.utcnow() if enlisted else None
        
        result = await db.execute_raw_query("""
            INSERT INTO users (name, steam_id, discord_id, rank, money, notes, enlisted_at, joined_at)
            VALUES (:name, :steam_id, :discord_id, :rank, :money, :notes, :enlisted_at, :joined_at)
            RETURNING *
        """, {
            "name": name,
            "steam_id": steam_id,
            "discord_id": discord_id,
            "rank": rank,
            "money": money,
            "notes": notes,
            "enlisted_at": enlisted_at,
            "joined_at": datetime.utcnow()
        })
        
        if result:
            user_data = dict(result[0])
            print(f"✅ Created user: {user_data['name']} (ID: {user_data['id']})")
            return user_data
        
        return None
        
    except Exception as e:
        print(f"❌ Failed to create user: {e}")
        return None


async def get_user_info(
    discord_id: Optional[str] = None,
    steam_id: Optional[str] = None,
    user_id: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    Get user information by Discord ID, Steam ID, or database ID.
    
    Args:
        discord_id: Discord ID to search for
        steam_id: Steam ID to search for
        user_id: Database ID to search for
    
    Returns:
        Dict with user data if found, None if not found
    """
    if not any([discord_id, steam_id, user_id]):
        print("❌ Must provide at least one identifier (discord_id, steam_id, or user_id)")
        return None
    
    try:
        db = await get_db_manager()
        
        if user_id:
            query = "SELECT * FROM users WHERE id = :id"
            params = {"id": user_id}
        elif discord_id:
            query = "SELECT * FROM users WHERE discord_id = :discord_id"
            params = {"discord_id": discord_id}
        elif steam_id:
            query = "SELECT * FROM users WHERE steam_id = :steam_id"
            params = {"steam_id": steam_id}
        
        result = await db.execute_raw_query(query, params)
        
        if result:
            user_data = dict(result[0])
            # Convert datetime objects to strings for easier handling
            if user_data.get('joined_at'):
                user_data['joined_at'] = user_data['joined_at'].isoformat()
            if user_data.get('enlisted_at'):
                user_data['enlisted_at'] = user_data['enlisted_at'].isoformat()
            if user_data.get('last_death'):
                user_data['last_death'] = user_data['last_death'].isoformat()
            
            return user_data
        
        return None
        
    except Exception as e:
        print(f"❌ Failed to get user info: {e}")
        return None


async def modify_user(
    identifier: str,
    identifier_type: str = "discord_id",
    name: Optional[str] = None,
    steam_id: Optional[str] = None,
    discord_id: Optional[str] = None,
    rank: Optional[int] = None,
    money: Optional[Union[float, Decimal]] = None,
    money_operation: str = "set",  # "set", "add", "subtract"
    notes: Optional[str] = None,
    enlisted: Optional[bool] = None,
    achievements: Optional[List[str]] = None,
    achievement_operation: str = "add",  # "add", "remove", "set"
    deaths: Optional[int] = None,
    death_operation: str = "set",  # "set", "add"
    reprimands: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Modify an existing user's data.
    
    Args:
        identifier: The identifying value (Discord ID, Steam ID, or database ID)
        identifier_type: Type of identifier ("discord_id", "steam_id", or "user_id")
        name: New name (optional)
        steam_id: New Steam ID (optional)
        discord_id: New Discord ID (optional)
        rank: New rank (0-10, optional)
        money: Money amount (optional)
        money_operation: How to apply money ("set", "add", "subtract")
        notes: New notes (optional)
        enlisted: Enlistment status (optional)
        achievements: Achievements list (optional)
        achievement_operation: How to apply achievements ("add", "remove", "set")
        deaths: Death count (optional)
        death_operation: How to apply deaths ("set", "add")
        reprimands: Reprimand data to add (optional)
    
    Returns:
        True if successful, False if failed
    """
    try:
        # First, get the user to ensure they exist
        if identifier_type == "discord_id":
            user = await get_user_info(discord_id=identifier)
        elif identifier_type == "steam_id":
            user = await get_user_info(steam_id=identifier)
        elif identifier_type == "user_id":
            user = await get_user_info(user_id=int(identifier))
        else:
            print(f"❌ Invalid identifier_type: {identifier_type}")
            return False
        
        if not user:
            print(f"❌ User not found with {identifier_type}: {identifier}")
            return False
        
        db = await get_db_manager()
        update_parts = []
        params = {"user_id": user["id"]}
        
        # Build update query dynamically based on provided parameters
        
        if name is not None:
            update_parts.append("name = :name")
            params["name"] = name
        
        if steam_id is not None:
            # Check if Steam ID is already in use by another user
            existing = await get_user_info(steam_id=steam_id)
            if existing and existing["id"] != user["id"]:
                print(f"❌ Steam ID {steam_id} is already in use")
                return False
            update_parts.append("steam_id = :steam_id")
            params["steam_id"] = steam_id
        
        if discord_id is not None:
            # Check if Discord ID is already in use by another user
            existing = await get_user_info(discord_id=discord_id)
            if existing and existing["id"] != user["id"]:
                print(f"❌ Discord ID {discord_id} is already in use")
                return False
            update_parts.append("discord_id = :discord_id")
            params["discord_id"] = discord_id
        
        if rank is not None:
            if not (0 <= rank <= 10):
                print(f"❌ Invalid rank: {rank}. Must be between 0-10")
                return False
            update_parts.append("rank = :rank")
            params["rank"] = rank
        
        if money is not None:
            if isinstance(money, float):
                money = Decimal(str(money))
            
            if money_operation == "set":
                update_parts.append("money = :money")
                params["money"] = money
            elif money_operation == "add":
                update_parts.append("money = money + :money")
                params["money"] = money
            elif money_operation == "subtract":
                update_parts.append("money = money - :money")
                params["money"] = money
            else:
                print(f"❌ Invalid money_operation: {money_operation}")
                return False
        
        if notes is not None:
            update_parts.append("notes = :notes")
            params["notes"] = notes
        
        if enlisted is not None:
            if enlisted and not user.get("enlisted_at"):
                # User is being enlisted for the first time
                update_parts.append("enlisted_at = :enlisted_at")
                params["enlisted_at"] = datetime.utcnow()
            elif not enlisted:
                # User is being un-enlisted
                update_parts.append("enlisted_at = NULL")
        
        if achievements is not None:
            if achievement_operation == "set":
                update_parts.append("achievements = :achievements")
                params["achievements"] = achievements
            elif achievement_operation == "add":
                # Add new achievements to existing ones
                update_parts.append("achievements = COALESCE(achievements, '{}') || :achievements::text[]")
                params["achievements"] = achievements
            elif achievement_operation == "remove":
                # Remove specific achievements
                for achievement in achievements:
                    update_parts.append("achievements = array_remove(achievements, :achievement)")
                    params["achievement"] = achievement
        
        if deaths is not None:
            if death_operation == "set":
                update_parts.append("deaths = :deaths")
                params["deaths"] = deaths
                # Also update last_death if we're setting deaths
                update_parts.append("last_death = :last_death")
                params["last_death"] = date.today()
            elif death_operation == "add":
                update_parts.append("deaths = deaths + :deaths")
                params["deaths"] = deaths
                update_parts.append("last_death = :last_death")
                params["last_death"] = date.today()
        
        if reprimands is not None:
            # Add timestamp to reprimand data
            reprimands["timestamp"] = datetime.utcnow().isoformat()
            update_parts.append("reprimands = COALESCE(reprimands, '{}') || :reprimands::jsonb")
            params["reprimands"] = reprimands
        
        if not update_parts:
            print("❌ No valid updates provided")
            return False
        
        # Execute the update
        query = f"UPDATE users SET {', '.join(update_parts)} WHERE id = :user_id"
        result = await db.execute_raw_query(query, params)
        
        print(f"✅ Updated user: {user['name']} (ID: {user['id']})")
        return True
        
    except Exception as e:
        print(f"❌ Failed to modify user: {e}")
        return False


async def search_users(
    search_term: str,
    search_fields: List[str] = ["name", "discord_id", "steam_id"],
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Search for users by various fields.
    
    Args:
        search_term: Term to search for
        search_fields: Fields to search in ("name", "discord_id", "steam_id", "notes")
        limit: Maximum number of results
    
    Returns:
        List of user data dictionaries
    """
    try:
        db = await get_db_manager()
        
        # Build search conditions
        conditions = []
        params = {"search": f"%{search_term}%", "limit": limit}
        
        for field in search_fields:
            if field in ["name", "discord_id", "steam_id", "notes"]:
                conditions.append(f"{field} ILIKE :search")
        
        if not conditions:
            print("❌ No valid search fields provided")
            return []
        
        query = f"""
            SELECT * FROM users 
            WHERE {' OR '.join(conditions)}
            ORDER BY name 
            LIMIT :limit
        """
        
        result = await db.execute_raw_query(query, params)
        
        users = []
        for row in result:
            user_data = dict(row)
            # Convert datetime objects to strings
            if user_data.get('joined_at'):
                user_data['joined_at'] = user_data['joined_at'].isoformat()
            if user_data.get('enlisted_at'):
                user_data['enlisted_at'] = user_data['enlisted_at'].isoformat()
            if user_data.get('last_death'):
                user_data['last_death'] = user_data['last_death'].isoformat()
            users.append(user_data)
        
        return users
        
    except Exception as e:
        print(f"❌ Failed to search users: {e}")
        return []


async def get_user_stats() -> Dict[str, Any]:
    """
    Get general statistics about users in the database.
    
    Returns:
        Dictionary with various statistics
    """
    try:
        db = await get_db_manager()
        
        stats = await db.execute_raw_query("""
            SELECT 
                COUNT(*) as total_users,
                COUNT(CASE WHEN enlisted_at IS NOT NULL THEN 1 END) as enlisted_users,
                COUNT(CASE WHEN discord_id IS NOT NULL THEN 1 END) as users_with_discord,
                AVG(money) as avg_money,
                MAX(money) as max_money,
                SUM(deaths) as total_deaths,
                AVG(rank) as avg_rank,
                MAX(rank) as max_rank,
                COUNT(CASE WHEN rank = 0 THEN 1 END) as civilians,
                COUNT(CASE WHEN rank >= 8 THEN 1 END) as high_ranking
            FROM users
        """)
        
        if stats:
            return dict(stats[0])
        return {}
        
    except Exception as e:
        print(f"❌ Failed to get user stats: {e}")
        return {}


# Convenience functions for testing
async def test_user_functions():
    """Test the user functions with sample data."""
    print("🧪 Testing user database functions...\n")
    
    # Test creating a user
    print("1. Creating test user...")
    user_data = await create_user(
        name="Test User",
        steam_id="76561198000000999",
        discord_id="999999999999999999",
        rank=2,
        money=500.50,
        notes="Test user for function testing",
        enlisted=True
    )
    
    if not user_data:
        print("❌ Failed to create user, stopping tests")
        return
    
    # Test getting user info
    print("\n2. Getting user info by Discord ID...")
    retrieved_user = await get_user_info(discord_id="999999999999999999")
    if retrieved_user:
        print(f"   ✅ Found user: {retrieved_user['name']}")
    
    print("\n3. Getting user info by Steam ID...")
    retrieved_user2 = await get_user_info(steam_id="76561198000000999")
    if retrieved_user2:
        print(f"   ✅ Found user: {retrieved_user2['name']}")
    
    # Test modifying user
    print("\n4. Modifying user (promoting and giving money)...")
    success = await modify_user(
        identifier="999999999999999999",
        identifier_type="discord_id",
        rank=4,
        money=1000,
        money_operation="add",
        achievements=["Test Achievement", "Database Tester"],
        achievement_operation="add",
        notes="Updated during testing"
    )
    print(f"   {'✅' if success else '❌'} Modify result: {success}")
    
    # Test search
    print("\n5. Searching for users...")
    search_results = await search_users("Test", limit=5)
    print(f"   ✅ Found {len(search_results)} users matching 'Test'")
    
    # Test stats
    print("\n6. Getting user statistics...")
    stats = await get_user_stats()
    print(f"   ✅ Total users: {stats.get('total_users', 0)}")
    print(f"   ✅ Enlisted users: {stats.get('enlisted_users', 0)}")
    
    # Clean up test user
    print("\n7. Cleaning up test user...")
    db = await get_db_manager()
    await db.execute_raw_query(
        "DELETE FROM users WHERE steam_id = :steam_id",
        {"steam_id": "76561198000000999"}
    )
    print("   ✅ Test user removed")
    
    print("\n🎉 All tests completed!")


if __name__ == "__main__":
    # Run tests if script is executed directly
    asyncio.run(test_user_functions())
