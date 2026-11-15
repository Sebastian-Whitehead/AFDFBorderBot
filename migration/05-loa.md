# Step 05: Move `LOAManager` to `military.leave_requests`

**Goal:** `database/loa_functions.py` reads and writes `military.leave_requests` on the shared DB. The method names, signatures and return shapes stay the same, so `discord/commands/LOA.py` needs **no changes**.

**Preconditions:** step 04 committed, shadow DB running.

## Changes in `database/loa_functions.py`

- Use `get_shared_db_manager()` and `sqlalchemy.text` with named parameters. Qualify the table as `military.leave_requests`.
- `parse_end_date` is **unchanged**. It stays an `async` staticmethod because `LOA.py` awaits it.
- **Table (decision 2026-11-15):** production already has `military.leave_requests(id, service_record_id NOT NULL, start_date, end_date, reason, status, submitted_by, details, created_at, updated_at)` with a one-active-per-`service_record_id` unique index. Use it unchanged. No DDL. Resolve a Discord ID to its service record with:
  ```sql
  SELECT sr.id FROM military.service_records sr
  JOIN public.identities_player p ON p.id = sr.player_identity_id
  JOIN public.identities_organizations o ON o.id = sr.organization_id
  WHERE p.discord_id = :d AND o.name = 'AFDF-Para Raiders'
  ```
  Store the Discord username in `submitted_by`.
- `create_or_update_loa(discord_id: str, username, end_date: str, reason=None)`:
  - Parse `end_date` with `parse_end_date`. If it is `None`, return `(False, "failed")`.
  - No service record for that Discord ID (not enlisted): return `(False, "failed")` and log why.
  - Active LOA exists for that service record: update `end_date`, `reason` (only if not `None`), `submitted_by`, `updated_at = now()`, then return `(True, "updated")`.
  - Otherwise insert `service_record_id`, `end_date`, `reason`, `submitted_by`. Return `(False, "submitted")`.
  - Keep the `(False, "failed")` return on exceptions.
- **Return dict shape**, same keys as today, built with the joins above: `{id, discord_id, username, start_date, end_date, reason, status, submitted_at, last_modified}`.
  - `discord_id` = `identities_player.discord_id` as `str`; `username` = `submitted_by`; `submitted_at` = `created_at`; `last_modified` = `updated_at`.
  - `end_date` is returned as the string `end_date.isoformat()` (`"YYYY-MM-DD"`), because `LOA.py` passes it back into `parse_end_date`. `start_date` stays a `date`.
- `get_all_active_loas()` keeps `ORDER BY submitted_at DESC`.
- `cancel_loa(discord_id)`: set `status='cancelled'` and `updated_at=now()`, matching through the service record, on the active row. Return whether a row changed.
- `cleanup_expired_loas()` becomes one statement, since `end_date` is a real date now:
  ```sql
  UPDATE military.leave_requests
     SET status = 'expired', updated_at = now()
   WHERE status = 'active' AND end_date < current_date
  ```
  Log the row count like today. Delete the commented-out legacy SQL block.
- Remove the `LOARequest` model from `database/models.py` and its import. **STOP if** anything else imports it.

## Tests

1. Switch `tests/test_loa_contract.py` from `local_db` to `shared_db`. **No assertion changes** to L1–L7.
2. Extend `cleanup()`: delete `military.leave_requests` rows whose service record belongs to a test identity (`discord_id BETWEEN 900000000000000000 AND 900000000000999999`). Run it before the service-record and identity deletes, because of the FKs.
3. L2–L7 now need an enlisted user first (the LOA needs a service record). Add that setup to the tests, with no assertion changes.
4. New `tests/test_loa_shared.py` (`shared_db`):

| ID | Test |
|---|---|
| L8 | After `create_user("zz_test_l", s, d)`, `create_or_update_loa(d, ...)` stores a `service_record_id` that belongs to that user's identity (query the table directly). Without a user it returns `(False, "failed")` and inserts nothing. |
| L9 | `create_or_update_loa(d, "u", "01/31/2030")` (US format input) leads `get_active_loa_by_discord_id(d)["end_date"]` to `"2030-01-31"`. |
| L10 | **LOA.py compatibility.** Call the `/loa-list` code path. Read `discord/commands/LOA.py` around lines 120–160 and reproduce its loop over `get_all_active_loas()` with `parse_end_date(loa_data['end_date'])`: every test LOA parses to a `date` (none fall into the "unparseable" branch). |
| L11 | Two LOAs, one ending yesterday and one tomorrow: `cleanup_expired_loas()` expires only yesterday's. |

## Done when

- L1–L7 pass on the shared DB with only the fixture changed, and L8–L11 pass.
- U* and S1 tests still pass.
- `git diff discord/commands/LOA.py` is empty.
- Committed as `migration step 05: loa on supabase`.
