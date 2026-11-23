"""
Simple Database Manager for AFDFBorderBot

Provides basic database connection and raw query execution.
"""

import os
import logging
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

# Configure logging
logger = logging.getLogger(__name__)


def _to_asyncpg_url(url: str) -> str:
    """Rewrite postgres:// and postgresql:// to postgresql+asyncpg://."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+asyncpg://" + url[len(prefix):]
    return url


class DatabaseManager:
    """Simple database manager for raw SQL operations."""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize the database manager."""
        if database_url is None:
            database_url = self._build_database_url()
        
        self.database_url = database_url
        self._engine = None
        self._session_factory = None
        
    def _build_database_url(self) -> str:
        """Build database URL from environment variables or defaults."""
        # Check if DATABASE_URL is provided (for Docker)
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            return _to_asyncpg_url(database_url)
        
        # Fallback to building from individual environment variables
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        user = os.getenv("DB_USER", "postgres")
        password = os.getenv("DB_PASSWORD", "admin")
        database = os.getenv("DB_NAME", "AFdb")
        
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
    
    async def initialize(self):
        """Initialize database connections."""
        try:
            self._engine = create_async_engine(
                self.database_url,
                echo=False,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
            
            self._session_factory = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            logger.info("Database connections initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def close(self):
        """Close database connections."""
        if self._engine:
            await self._engine.dispose()
        logger.info("Database connections closed")
    
    def get_session(self) -> AsyncSession:
        """Get a new database session."""
        if not self._session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._session_factory()
    
    async def execute_raw_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a raw SQL query and return results."""
        async with self.get_session() as session:
            try:
                result = await session.execute(text(query), params or {})
                await session.commit()
                
                # Check if this is a SELECT query by looking at the query string
                query_lower = query.strip().lower()
                if query_lower.startswith('select') or query_lower.startswith('with'):
                    return [dict(row._mapping) for row in result.fetchall()]
                else:
                    # For INSERT, UPDATE, DELETE operations, return empty list
                    return []
            except Exception as e:
                await session.rollback()
                logger.error(f"Query failed: {e}")
                raise


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


async def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        await _db_manager.initialize()
    return _db_manager


_shared_db_manager: Optional[DatabaseManager] = None


async def get_shared_db_manager() -> DatabaseManager:
    """Shared Supabase DB (users, LOA). Settings stay on get_db_manager()."""
    global _shared_db_manager
    if _shared_db_manager is None:
        url = os.getenv("SUPABASE_DATABASE_URL")
        if not url:
            raise RuntimeError("SUPABASE_DATABASE_URL is not set")
        _shared_db_manager = DatabaseManager(_to_asyncpg_url(url))
        await _shared_db_manager.initialize()
    return _shared_db_manager


async def close_database():
    """Close the global database manager."""
    global _db_manager, _shared_db_manager
    if _db_manager:
        await _db_manager.close()
        _db_manager = None
    if _shared_db_manager:
        await _shared_db_manager.close()
        _shared_db_manager = None
