# Step 06: Fix and rewire the `/user` cog (`discord/commands/UserManagement.py`)

**Goal:** the cog has never worked. It imports `get_db_manager` from `..utils`, which doesn't export it, and calls methods that don't exist on `DatabaseManager` and `RankManager`. Rewire it to the step 04 functions so every command does what its code clearly intends. **The bot does not touch money**, so remove `/give_money`, the money leaderboard, and the Money field on `/profile`. Everything else keeps the same command names, options, embed titles and fields.

**Preconditions:** step 05 committed.

## Changes (only in `UserManagement.py`)

1. **Imports:**
   ```python
   from database import create_user, get_user_info, modify_user, get_user_count_by_rank
   from ..utils import RankManager
   ```
   Remove `get_db_manager` and `Decimal`.
2. **RankManager calls.** Use the existing methods and do not add new ones to `RankManager`:
   - `self.rank_manager.is_valid_rank(r)` → `self.rank_manager.get_rank_by_level(r) is not None`
   - `self.rank_manager.get_rank_info(r)` → `self.rank_manager.get_rank_by_level(r)`
   - `self.rank_manager.can_promote_to(a, b)` → `self.rank_manager.is_valid_promotion(a, b)`
3. **Members are dicts now:** `member.name` → `member["name"]`, `member.rank` → `member["rank"]`, and the same for `steam_id`, `deaths`, `joined_at`, `enlisted_at`, `last_death`, `achievements` and `notes`.
4. **`add_member`:**
   - If `steam_id` is not all digits, reply ephemerally `❌ Steam ID must be numeric (SteamID64).` and return.
   - Existence check: `await get_user_info(discord_id) if discord_id else None`, then `or await get_user_info(steam_id)`.
   - Call `create_user(name=..., steam_id=..., discord_id=..., rank=..., notes=...)`. If it returns `None`, reply ephemerally `❌ Failed to add member (already exists or invalid data).` and return. Today the result is ignored.
5. **`promote` / `demote`:** replace `db.update_user_rank(member.id, new_rank, notes)` with `await modify_user(str(user.id), rank=new_rank, reason=notes)`.
6. **Remove money:**
   - Delete the whole `give_money` command.
   - In `leaderboard`, remove the `"money"` choice and its branch. Keep `choices=["rank"]` with `default="rank"`, so the command and its rank output stay unchanged.
   - In `profile`, delete the `Money` field.
7. **`leaderboard` rank branch:** use `get_user_count_by_rank()`.
8. **`profile`:** `member["deaths"]` may be 0. `joined_at`, `enlisted_at` and `last_death` may be `None`, and the existing `if` guards already handle that.

Change nothing else: no new commands, no permission changes, no embed redesign.

## Tests: `tests/test_user_management_cog.py` (unit, no DB)

Set up:
- `interaction = MagicMock()`, `interaction.id = 42`, `interaction.response.send_message = AsyncMock()`
- `discord_user = MagicMock(id=900000000000000001, mention="<@x>")`
- `cog = UserManagement(bot=MagicMock())`

Call commands as `await UserManagement.<command>.callback(cog, interaction, <every option passed explicitly>)`. Monkeypatch the database functions **on the cog module** (`monkeypatch.setattr(um_module, "create_user", AsyncMock(...))`).

| ID | Test |
|---|---|
| G0 | `import discord.commands.UserManagement` succeeds. This test fails on the code before this step, so run it first to confirm it reproduces the bug. |
| G1 | `add_member`, new user: `create_user` is awaited with `steam_id="76561190000000001"`, `discord_id="900000000000000001"` and `rank=0`. The reply embed title is `✅ Member Added Successfully`. |
| G2 | `add_member` with `steam_id="abc"` gives an ephemeral reply containing "numeric", and `create_user` is not awaited. |
| G3 | `add_member` where `get_user_info` returns a dict gives an ephemeral "already exists" reply, and `create_user` is not awaited. |
| G4 | `add_member` where `create_user` returns `None` gives an ephemeral "Failed to add member" reply. |
| G5 | `promote` from rank 2 to 3 calls `modify_user(..., rank=3, reason=<contains "Promoted">)`, and the embed title is `🎉 Promotion Successful`. |
| G6 | `promote` from 2 to 6 (more than 2 levels, `is_valid_promotion` False) gives an ephemeral "Invalid rank progression" reply, and `modify_user` is not awaited. |
| G7 | `demote` with `new_rank >= current` is rejected. A valid demote calls `modify_user` with `reason` containing the given reason. |
| G8 | **No money:** the cog has no `give_money` attribute. Searching `UserManagement.py` for `money` (case-insensitive) finds nothing. |
| G9 | `profile` with a full member dict (deaths 0, `None` dates, empty achievements) sends an embed without raising, and no embed field is named `Money`. |
| G10 | `leaderboard("rank", 10)` sends an embed whose description contains the rank names from `ids.json`. |
| G11 (`shared_db`, integration) | Run G1 → G5 → G9 against the shadow DB **without** mocks. Afterwards `get_user_info` shows rank 3. |

## Done when

- G0–G11 and the full suite pass.
- `python -c "import discord.bot"` works.
- Committed as `migration step 06: fix user management cog`.
