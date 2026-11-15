# Step 08: Data migration script

**Goal:** write `migration/migrate_to_supabase.py`. It copies users and active LOAs from a local bot DB into a Supabase-shaped DB. It must be **idempotent** (safe to rerun) and have a dry run. In this step it runs only test DB → shadow DB. Production happens in step 09.

**Preconditions:** step 07 committed. The shadow DB and local test DB are running.

## CLI

```
python migration/migrate_to_supabase.py --source-url <local asyncpg url> --target-url <supabase asyncpg url> [--dry-run] [--allow-remote]
```
- `--dry-run`: does all the work inside one transaction per entity type, prints the report, then **ROLLBACK**. Constraint errors therefore surface in the dry run too.
- Refuse to run (exit 2) if the target host is not `localhost` or `127.0.0.1` unless `--allow-remote` is given.
- Read the source with plain SQL (`SELECT * FROM users`, `SELECT * FROM loa_requests`). Do **not** import the old models; they are deleted.
- Write the target with `sqlalchemy.text` and named parameters, through the same SQL patterns as `database/user_functions.py` (reuse `database/rank_codes.py`).

## Per user (in local `id` order; each user is its own savepoint, so one bad row doesn't abort the rest)

1. `steam_id` not numeric: **skip**, reason `non-numeric steam_id`.
2. Rank level not in `ids.json`: **skip**, reason `unknown rank <n>`.
3. `SELECT public.fab_ensure_player_account(:name, :steam, :discord)`. This creates the identity or adopts an existing one with the same steam_id.
   - Adopted, existing `discord_id` NULL, local has one: set it.
   - Adopted with a **different** non-null discord_id: keep Supabase's, and record a warning `discord conflict`.
   - Another identity already holds the local discord_id: **skip**, reason `discord_id used by identity <id>`.
4. `created_at = LEAST(created_at, :joined_at)`.
5. If there is no AFDF-FAS `service_records` row, insert one with `current_rank = level_to_code(rank)` and `service_status 'active'`. If one exists, leave it alone and count `record already existed`.
6. If `enlisted_at` is set and no enlisted or reenlisted event exists for the record, insert an `enlisted` event with `occured_at = enlisted_at` and `rank = code`.
7. Merge the non-null local `notes`, `achievements` (as a JSON array), `deaths`, `last_death` (ISO string), `reprimands` and `extra_data` into `details`, following D2. Existing keys in `details` win; never overwrite Supabase data.
8. Local `money` is **not migrated**. The bot does not touch money, and the script never touches `economy.*`.

## Per LOA (only `status = 'active'` rows)

1. `parse_end_date(end_date)` (import `LOAManager.parse_end_date`) returns None: **skip**, reason `unparseable end_date '<text>'`.
2. Resolve the user's service record. None: **skip**, reason `no service record`. If a row with the same `service_record_id` and `created_at` (= local `submitted_at`) exists in `military.leave_requests`, count it as `already migrated`. Insert the local username as `submitted_by`.
3. If the end date is in the past, insert with `status 'expired'`. Otherwise use `'active'`. If inserting `active` hits the one-active unique index, **skip** with reason `another active LOA exists`.
4. Copy `username`, `start_date`, `reason`, `submitted_at` and `last_modified`. Set `player_identity_id` by discord_id lookup.

## Report (stdout, also written to `migration/backup/migration-report-<timestamp>.txt`)

Counts: users created, adopted, skipped (with each reason and local id), warnings, LOAs migrated, expired and skipped (with reasons). Print `DRY RUN – rolled back` at the end of a dry run.

## Tests: `tests/test_migration_script.py` (`local_db` + `shared_db`)

Seed **AFdb_test** with these local rows. Use the zz_test / test ID ranges so cleanup covers them, and extend the local cleanup for LOAs if needed:

| Row | Data |
|---|---|
| A | Plain user: rank 0, not enlisted |
| B | Enlisted `2025-03-01 12:00`, rank 10, money `123.60` (must **not** be migrated), notes "n", achievements `{"x","y"}`, deaths 2, last_death 2025-06-01, reprimands `[{"r":1}]` |
| C | steam_id `"STEAM_0:1:1"` (non-numeric) |
| D | steam_id already present in the shadow DB. Pre-create it with `fab_ensure_player_account('zz_test_game', <steam>, NULL)`. |
| E | discord_id already used by a different shadow identity |
| LOA1 | Active, end `"2030-01-31"` |
| LOA2 | Active, end `"01/31/2030"` |
| LOA3 | Active, end `"next week"` |
| LOA4 | Cancelled |
| LOA5 | Active, end `"2000-01-01"` |

Run the script as a subprocess, or by calling its `main(argv)`, against `TEST_LOCAL_DATABASE_URL` → `TEST_SHARED_DATABASE_URL`.

| ID | Test |
|---|---|
| M1 | The report shows created 2 (A, B), adopted 1 (D), and skipped 2 (C non-numeric steam_id, E discord_id in use). Assert the exact skip reasons. |
| M2 | **Parity, which proves function is preserved.** For A, B and D, `get_user_info(<discord or steam>)` on the shared DB matches the local row: `name`, `steam_id`, `discord_id`, `rank`, `enlisted`, `notes`, `achievements` (as a list), `deaths` and `last_death`. B's `enlisted_at` equals the local one (compare in UTC). |
| M3 | D has exactly one identity with that steam_id, and its discord_id is now set. |
| M4 | **No money touched:** the row counts of `economy.transactions` and `economy.transactions_entries` are the same before and after the run, and the script's source contains no `economy.` or `post_economy`. |
| M5 | LOAs: LOA1 and LOA2 migrated as active with `end_date` 2030-01-31, LOA5 migrated as expired, LOA3 skipped (unparseable), LOA4 not migrated. |
| M6 | **Idempotent:** run the script again. Row counts in `identities_player`, `service_records`, `service_events` and `leave_requests` are unchanged. |
| M7 | **Dry run:** after cleanup and reseeding, `--dry-run` prints the same counts as M1, and afterwards the shadow DB has no test identities. |
| M8 | `--target-url` with host `db.example.com` and no `--allow-remote` exits with code 2 without connecting. |

## Done when

- M1–M8 and the full suite pass.
- Committed as `migration step 08: data migration script`.
