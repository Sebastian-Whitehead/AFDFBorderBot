# Step 09: Production cutover

**Goal:** apply the schema to production Supabase, migrate the real local data, switch the bot over, and clean up.

**This step writes to the shared production DB. Every write below needs explicit user approval at the moment it happens.** Do not batch approvals.

**Preconditions:**
- Steps 00–08 are committed and the full suite is green.
- The user is available for the whole step.

## 1. Pre-flight (read-only)

1. `git status` is clean, and you are on `supabase`.
2. Run the duplicate checks from step 02 §3 against production. **STOP if** there are rows.
3. Re-dump the production schema (step 02 §2) and diff it against `migration/shadow/schema.sql`. **STOP if** `public`, `economy` or `military` changed in a way that affects the tables or functions the bot uses, and ask the user.
4. Back up the local bot DB:
   ```bash
   docker compose exec -T postgres pg_dump -U postgres -d AFdb > migration/backup/AFdb-<date>.sql
   ```
   Confirm the file is non-empty.

## 2. Schema to production

Show the user `migration/sql/001_bot_tables.sql`. After approval, apply it with the Supabase MCP `apply_migration` tool on project `rjakbhfokyjoujqlijqn`, name `afdf_bot_tables`.

Then run read-only checks:
- `to_regclass('military.leave_requests')` is not null.
- There is exactly one `AFDF - Para Raiders` org.
- `get_advisors` (security) shows no new errors for `leave_requests`.

## 3. Stop the bot

Stop the running bot (`docker compose --profile bot stop bot`, or stop the local process) so no writes happen during migration.

## 4. Migrate data

1. Dry run against production:
   ```bash
   python migration/migrate_to_supabase.py --source-url <AFdb url> --target-url <session pooler url, asyncpg form, ?ssl=require> --allow-remote --dry-run
   ```
2. Show the user the full report. **STOP if** there are unexpected skips or conflicts; the user decides each one.
3. After approval, run the same command **without** `--dry-run`. Keep the report in `migration/backup/`.

## 5. Switch the bot

1. Add `SUPABASE_DATABASE_URL` (session pooler, `?ssl=require`) to `.env`, and to the bot service's `environment` in `docker-compose.yml` if the bot runs in Docker. Do not print the secret in chat or logs.
2. Start the bot.

## 6. Smoke test (manual, in Discord, with the user)

Use a test Discord account the user nominates. Record pass or fail for each:

| # | Action | Expected |
|---|---|---|
| 1 | `/profile` on a migrated user | Rank and enlisted date match the local data. There is no Money field. |
| 2 | `/add_member` for the test account | Success embed. A row appears in `identities_player` and `service_records`. |
| 3 | `/promote` for the test account by 1 | Success. There is a `rank_changed` event. |
| 4 | `/give_money` | The command no longer exists |
| 5 | Submit, list and cancel an LOA | Each works, and the rows are in `military.leave_requests` |
| 6 | A settings command | It still works, so settings are still on the local DB |
| 7 | Join and leave the server | Existing listener behaviour is unchanged |

If any check fails, roll back (section 8).

## 7. Clean up (only after the smoke test passes and the user confirms)

- `init.sql`: remove the `users`, `loa_requests` and `transaction_log` tables, their indexes and the sample user inserts. Keep `bot_settings`.
- `models.py` should now contain only `Base` and `BotSetting`.
- `tests/conftest.py`: the local baseline fixtures for users and LOA are no longer used. Leave `local_db` for S1.
- Update `CLAUDE.md` (Layout and Gotchas): the shared Supabase DB holds users and LOA, the bot never touches `economy.*`, the local DB holds settings, and add the `SUPABASE_DATABASE_URL` variable.
- **Do not drop** the local tables from the running `AFdb` database yet. Leave them as a fallback for a week, then ask the user.
- Commit as `migration step 09: cutover`. Push only if the user asks.

## 8. Rollback

- **Bot:** remove `SUPABASE_DATABASE_URL` from the environment, check out the last commit before step 03 (`git checkout <sha> -- database discord`), and restart. The local tables are untouched, so the bot works as before (with the `/user` cog still broken, as it was).
- **Supabase data:** migrated rows can be found by the report's identity ids. Do not delete shared data without the user. Adopted identities belong to the game.
- **Schema:** `001_bot_tables.sql` is additive. Removing it is a separate decision for the user.

## Done when

The smoke test passes, the cleanup is committed, and the user has confirmed.
