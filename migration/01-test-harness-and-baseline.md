# Step 01: Test harness and baseline contract tests

**Goal:** write tests that pin down what `database/user_functions.py`, `database/loa_functions.py` (`LOAManager`) and the settings functions do **today**, and see them pass against the current code. Steps 04 and 05 rerun the same tests against Supabase, and that is how we know function is preserved.

**Preconditions:** step 00 answered. Docker is running. You are on the `supabase` branch.

## 1. Tooling

1. Create `requirements-dev.txt`:
   ```
   -r requirements.txt
   pytest>=8.0
   pytest-asyncio>=0.23
   ```
   Note: `requirements.txt` is **UTF-16** encoded. Do not edit it. If pip fails to read it through `-r`, drop the `-r` line and install `requirements.txt` separately.
2. `venv/Scripts/python.exe -m pip install -r requirements-dev.txt`
3. Create `pytest.ini` in the repo root:
   ```ini
   [pytest]
   testpaths = tests
   asyncio_mode = auto
   markers =
       db_local: needs TEST_LOCAL_DATABASE_URL
       db_shared: needs TEST_SHARED_DATABASE_URL
   ```
4. Append to `.gitignore`: `.env.test`, `migration/shadow/` and `migration/backup/`.

## 2. Local test database (never the dev `AFdb` database)

```bash
docker compose --profile database up -d postgres
docker compose exec postgres psql -U postgres -c 'CREATE DATABASE "AFdb_test"'
docker compose exec -T postgres psql -U postgres -d AFdb_test < init.sql
```
Create `.env.test` (gitignored):
```
TEST_LOCAL_DATABASE_URL=postgresql+asyncpg://postgres:admin@localhost:5432/AFdb_test
```

## 3. `tests/conftest.py`

Requirements:
- Load `.env.test` with `python-dotenv` (already a dependency).
- Put the repo root on `sys.path` so `import database` and `import discord` resolve to the **local** packages. `discord/` here is the bot's own package, not discord.py.
- **Autouse async fixture** that, after each test, calls `database.db_manager.close_database()`. From step 03 it also closes the shared manager. Engines are bound to an event loop, and pytest-asyncio gives each test a new loop, so a cached engine would break the next test.
- Fixture `local_db`: skip the test if `TEST_LOCAL_DATABASE_URL` is unset. Otherwise set `os.environ["DATABASE_URL"]` to it (with `monkeypatch.setenv`), run `cleanup()` before and after the test, and yield.
- Constants for test data, so cleanup can never touch real rows:
  ```python
  STEAM_BASE = 76561190000000000      # not a real Steam64 range
  DISCORD_BASE = 900000000000000000
  NAME_PREFIX = "zz_test_"
  ```
  Helper `def ids(n): return str(STEAM_BASE + n), str(DISCORD_BASE + n)`.
- `async def cleanup()` (in `tests/helpers.py`), which for now uses the local DB:
  ```sql
  DELETE FROM users WHERE name LIKE 'zz_test_%' OR steam_id LIKE '765611900000%';
  DELETE FROM loa_requests WHERE discord_id LIKE '9000000000000%';
  ```
  Run it through `get_db_manager().execute_dml_query(...)`.

## 4. Contract tests (write exactly these)

**Money is out of scope.** Do not pass `money` to any function and do not assert on a `money` key. Step 04 removes money from the API.

### `tests/test_user_functions_contract.py` (all use `local_db`)

| ID | Test |
|---|---|
| U1 | `create_user(name="zz_test_a", steam_id=s, discord_id=d)` returns a dict whose keys include `{id, name, steam_id, discord_id, rank, enlisted}`. Expect `name="zz_test_a"`, `steam_id == s` (str), `discord_id == d` (str), `rank == 0`, `enlisted is False`. |
| U2 | `create_user(..., rank=3, enlisted=True)`, then `get_user_info(d)`: `rank == 3`, `enlisted is True`, `enlisted_at is not None`. |
| U3 | A second `create_user` with the same steam_id returns `None`. With a new steam_id but the same discord_id it also returns `None`. |
| U4 | `get_user_info(discord_id)` and `get_user_info(steam_id)` return the same `id`. The keys include `{id, name, steam_id, discord_id, joined_at, enlisted_at, rank, notes, achievements, last_death, deaths, reprimands, extra_data, enlisted}`. An unknown id (`str(DISCORD_BASE+999)`) returns `None`. |
| U5 | `modify_user(d, name="zz_test_b")`, `rank=4` and `notes="hello"` are each reflected in `get_user_info`. `modify_user(d, enlisted=False)` gives `enlisted False` and `enlisted_at None`, then `enlisted=True` gives `enlisted True`. `modify_user(unknown, name="x")` returns `False`. |
| U6 | Create `zz_test_alpha`. `search_users("ZZ_TEST_AL")` contains it (case-insensitive partial match). The result has at most 20 items, and each item has the keys `{id, name, steam_id, discord_id, rank, enlisted}`. |
| U7 | Read `get_user_stats()` (keys `total_users`, `enlisted_users`). Create one enlisted user and one not enlisted. `total_users` goes up by 2 and `enlisted_users` by 1. Compare deltas, never absolute numbers. |

### `tests/test_loa_contract.py`

| ID | Test |
|---|---|
| L1 (no DB) | `parse_end_date("2030-01-31")` and `parse_end_date("01/31/2030")` both return `date(2030,1,31)`. `"31-01-2030"` and `"garbage"` return `None`. |
| L2 | `create_or_update_loa(d, "zz_test_user", "2030-01-31", "trip")` returns `(False, "submitted")`. `get_active_loa_by_discord_id(d)` returns keys `{id, discord_id, username, start_date, end_date, reason, status, submitted_at, last_modified}`, with `discord_id == d` (str), `status == "active"`, `reason == "trip"` and `await parse_end_date(str(r["end_date"])) == date(2030,1,31)`. Do not assert the string format of `end_date`. |
| L3 | Calling again with `"2030-02-15", "longer"` returns `(True, "updated")`. The end date and reason are updated, and there is still exactly one active LOA for `d` in `get_all_active_loas()`. |
| L4 | With `reason=None` on update, the old reason is kept. |
| L5 | Two users' LOAs both appear in `get_all_active_loas()`, the newer one first (`submitted_at` descending). |
| L6 | `cancel_loa(d)` returns `True`, then `False`. `get_active_loa_by_discord_id(d)` is `None`. |
| L7 | `create_or_update_loa(d, ..., "2000-01-01", None)`, then `cleanup_expired_loas()`. `get_active_loa_by_discord_id(d)` is `None`. |

### `tests/test_settings_contract.py`
| ID | Test |
|---|---|
| S1 | Read `database/settings_manager.py` for the real API. Round-trip a setting with key `zz_test_setting`: update it, get it back equal, and delete it in teardown with `DELETE FROM bot_settings WHERE setting_key LIKE 'zz_test_%'`. Settings must stay on the **local** DB for the whole migration. |

## 5. Run the baseline

```bash
venv/Scripts/python.exe -m pytest -v
```

**Expected:** everything passes on the current, unmodified code.

If a test fails:
1. Re-read the function. If the test is wrong, fix the test.
2. If the current code has a real bug, mark that test `@pytest.mark.xfail(reason="baseline bug: <what>", strict=True)`, list it in the commit message, and tell the user. Do **not** fix product code in this step.

**STOP if** more than two tests are xfail. The baseline is then too weak to protect the migration, so ask the user.

## Done when

- `pytest` is green (xfails allowed as above) against `AFdb_test`.
- No product code was changed (`git diff --stat` shows only `tests/`, `pytest.ini`, `requirements-dev.txt`, `.gitignore`).
- Committed as `migration step 01: test harness and baseline`.
