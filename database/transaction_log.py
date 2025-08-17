"""
Transaction Log Functions for AFDFBorderBot

Simple transaction logging and querying using SQLAlchemy.
"""

import logging
from typing import Optional, List, Dict, Any, Union
from decimal import Decimal

from sqlalchemy.future import select

from .db_manager import get_db_manager
from .models import TransactionLog

logger = logging.getLogger(__name__)


async def add_transaction(
    amount: Union[Decimal, float, int],
    transaction_type: str,
    from_user_id: Optional[str] = None,
    to_user_id: Optional[str] = None,
    description: Optional[str] = None,
    processed: bool = False
) -> bool:
    """Add a new transaction to the log."""
    try:
        db = await get_db_manager()
        
        if isinstance(amount, (int, float)):
            amount = Decimal(str(amount))
        
        async with db.get_session() as session:
            transaction = TransactionLog(
                from_user_id=from_user_id,
                to_user_id=to_user_id,
                amount=amount,
                transaction_type=transaction_type,
                description=description,
                processed=processed
            )
            session.add(transaction)
            await session.commit()
            return True
            
    except Exception as e:
        logger.error(f"Failed to add transaction: {e}")
        return False


async def get_unprocessed_transactions() -> List[Dict[str, Any]]:
    """Get all unprocessed transactions."""
    try:
        db = await get_db_manager()
        
        async with db.get_session() as session:
            result = await session.execute(
                select(TransactionLog).where(TransactionLog.processed == False).order_by(TransactionLog.timestamp.asc())
            )
            transactions = result.scalars().all()
            
            return [
                {
                    "id": t.id,
                    "timestamp": t.timestamp,
                    "from_user_id": t.from_user_id,
                    "to_user_id": t.to_user_id,
                    "amount": t.amount,
                    "transaction_type": t.transaction_type,
                    "description": t.description,
                    "processed": t.processed
                }
                for t in transactions
            ]
            
    except Exception as e:
        logger.error(f"Failed to get unprocessed transactions: {e}")
        return []


async def get_transactions_by_sender(user_id: str) -> List[Dict[str, Any]]:
    """Get transactions by sender."""
    try:
        db = await get_db_manager()
        
        async with db.get_session() as session:
            result = await session.execute(
                select(TransactionLog).where(TransactionLog.from_user_id == user_id).order_by(TransactionLog.timestamp.desc())
            )
            transactions = result.scalars().all()
            
            return [
                {
                    "id": t.id,
                    "timestamp": t.timestamp,
                    "from_user_id": t.from_user_id,
                    "to_user_id": t.to_user_id,
                    "amount": t.amount,
                    "transaction_type": t.transaction_type,
                    "description": t.description,
                    "processed": t.processed
                }
                for t in transactions
            ]
            
    except Exception as e:
        logger.error(f"Failed to get transactions by sender: {e}")
        return []


async def get_transactions_by_recipient(user_id: str) -> List[Dict[str, Any]]:
    """Get transactions by recipient."""
    try:
        db = await get_db_manager()
        
        async with db.get_session() as session:
            result = await session.execute(
                select(TransactionLog).where(TransactionLog.to_user_id == user_id).order_by(TransactionLog.timestamp.desc())
            )
            transactions = result.scalars().all()
            
            return [
                {
                    "id": t.id,
                    "timestamp": t.timestamp,
                    "from_user_id": t.from_user_id,
                    "to_user_id": t.to_user_id,
                    "amount": t.amount,
                    "transaction_type": t.transaction_type,
                    "description": t.description,
                    "processed": t.processed
                }
                for t in transactions
            ]
            
    except Exception as e:
        logger.error(f"Failed to get transactions by recipient: {e}")
        return []


async def mark_transaction_processed(transaction_id: int) -> bool:
    """Mark a transaction as processed."""
    try:
        db = await get_db_manager()
        
        async with db.get_session() as session:
            result = await session.execute(
                select(TransactionLog).where(TransactionLog.id == transaction_id)
            )
            transaction = result.scalar_one_or_none()
            
            if transaction:
                transaction.processed = True
                await session.commit()
                return True
            return False
            
    except Exception as e:
        logger.error(f"Failed to mark transaction as processed: {e}")
        return False
