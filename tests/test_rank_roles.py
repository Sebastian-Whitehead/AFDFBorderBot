from unittest.mock import AsyncMock, MagicMock

from discord.utils.rank_roles import rank_role_id, sync_rank_roles


async def test_swaps_old_for_new():
    guild, member = MagicMock(), MagicMock(remove_roles=AsyncMock(), add_roles=AsyncMock())
    guild.get_role.side_effect = lambda rid: f"role{rid}"
    await sync_rank_roles(guild, member, "EN3", "EN4")
    member.remove_roles.assert_awaited_once_with(f"role{rank_role_id('EN3')}")
    member.add_roles.assert_awaited_once_with(f"role{rank_role_id('EN4')}")


async def test_rank_without_role_is_skipped():
    guild, member = MagicMock(), MagicMock(remove_roles=AsyncMock(), add_roles=AsyncMock())
    guild.get_role.side_effect = lambda rid: f"role{rid}"
    assert rank_role_id("OF6") is None
    await sync_rank_roles(guild, member, "OF4", "OF6")  # new rank has no role: only the old one goes
    member.remove_roles.assert_awaited_once()
    member.add_roles.assert_not_awaited()
