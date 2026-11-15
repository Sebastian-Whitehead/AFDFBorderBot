# Supabase migration: step index

Moves users and LOA requests from the bot's local Postgres to the shared Supabase project. `bot_settings` stays local.

**The bot does not touch money.** It never reads or writes `economy.*` and never calls economy functions. Money fields, money commands and the local transaction log are removed, not migrated.

Execute steps strictly in order, one per session, on the `supabase` git branch. Each step file is self-contained.

| Step | File | Touches |
|---|---|---|
| 00 | [00-decisions.md](00-decisions.md) | Nothing. Confirms choices with the user |
| 01 | [01-test-harness-and-baseline.md](01-test-harness-and-baseline.md) | `tests/`, `requirements-dev.txt` |
| 02 | [02-supabase-schema-and-shadow-db.md](02-supabase-schema-and-shadow-db.md) | `migration/sql/`, shadow DB |
| 03 | [03-shared-db-connection.md](03-shared-db-connection.md) | `database/db_manager.py`, `.env.example` |
| 04 | [04-user-functions.md](04-user-functions.md) | `database/user_functions.py`, `database/rank_codes.py` |
| 05 | [05-loa.md](05-loa.md) | `database/loa_functions.py` |
| 06 | [06-user-management-cog.md](06-user-management-cog.md) | `discord/commands/UserManagement.py` |
| 07 | [07-remove-transaction-log.md](07-remove-transaction-log.md) | `database/transaction_log.py` (deleted) |
| 08 | [08-data-migration-script.md](08-data-migration-script.md) | `migration/migrate_to_supabase.py` |
| 09 | [09-cutover.md](09-cutover.md) | Production Supabase, `.env`, `init.sql` |

## Rules for whoever executes these steps

1. **Never write to the production Supabase project (`rjakbhfokyjoujqlijqn`) before step 09.** It is the shared source of truth for the game. All tests run against the local Postgres (step 01) or the shadow DB (step 02). Read-only queries against production are fine.
2. A step is done only when every test in its "Tests" section passes **and** the full suite (`python -m pytest`) still passes. Paste the pytest summary line into the commit message.
3. Commit at the end of each step: `git commit -m "migration step NN: <title>"`. Do not push unless the user asks.
4. If a "STOP" condition in a step is hit, stop and ask the user. Do not improvise around it.
5. Do not change behaviour that the step does not mention. Do not add features.
6. Run Python with the repo venv from the repo root: `venv/Scripts/python.exe -m pytest` (Git Bash) or `.\venv\Scripts\python.exe -m pytest` (PowerShell).

## Facts verified when this plan was written (2026-11-14)

- Supabase schemas: `public.identities_player|npc|organizations`, `economy.accounts|transactions|transactions_entries|stocks`, `military.service_records|service_events|sessions|attendance`. All have RLS enabled.
- `public.fab_ensure_player_account(p_alias text, p_steam_id bigint, p_discord_id bigint) → jsonb` (`SECURITY DEFINER`) creates the identity if no row has that steam_id. It is the canonical way to create or find a player identity, and the bot calls it and ignores the JSON it returns. A trigger on `identities_player` creates a bank account for every new identity. That is Supabase's rule, not the bot's: the bot never reads or changes accounts. The only exception is test cleanup on the shadow DB, which must delete those accounts because of the foreign key.
- Constraints: `service_records.current_rank` and `service_events.rank` allow only `EN0–EN8`, `OF0–OF11`. `ids.json` ranks are levels 0–8 = `EN0–EN8`, 9 = `UO`, 10 = `PRES`. `service_events.event_type` ∈ {enlisted, rank_changed, discharged, reenlisted, retired}. `service_records.service_status` ∈ {active, discharged, retired}. `service_records.organization_id` is required.
- Bot bugs today: `discord/commands/UserManagement.py` imports `get_db_manager` from `..utils` (not exported). It calls `db.get_user_by_discord_id`, `db.create_user`, `db.update_user_rank`, `db.update_user_money`, `db.get_top_users_by_money` and `db.get_user_count_by_rank`, none of which exist. Money is dropped from `user_functions` in step 04, and the money commands are removed from the cog in step 06. It also calls `RankManager.is_valid_rank`, `get_rank_info` and `can_promote_to`, which don't exist either. The cog cannot work today.
- `database/transaction_log.py` has no callers outside `database/__init__.py`.
