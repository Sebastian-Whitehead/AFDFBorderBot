"""Keep a member's Discord rank role in step with their service-record rank."""

from typing import Optional

from .rank_manager import RankManager

_ranks = RankManager()


def rank_role_id(rank: Optional[str]) -> Optional[int]:
    """Discord role id for a rank code (None if the rank is unknown or has no role)."""
    info = _ranks.get_rank(rank) if rank else None
    return int(info["role_id"]) if info and info.get("role_id") else None


async def sync_rank_roles(guild, member, old_rank: Optional[str], new_rank: str) -> None:
    """Swap the old rank role for the new one. Ranks without a role are skipped.
    Raises whatever discord raises (e.g. Forbidden); callers decide how to report it."""
    old_id, new_id = rank_role_id(old_rank), rank_role_id(new_rank)
    if old_id and old_id != new_id and (role := guild.get_role(old_id)):
        await member.remove_roles(role)
    if new_id and (role := guild.get_role(new_id)):
        await member.add_roles(role)
