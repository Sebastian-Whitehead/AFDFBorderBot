# Step 03: Second database connection for the shared (Supabase) DB

**Goal:** the bot holds two connections:
- **local** (existing): `get_db_manager()`, used only for `bot_settings`;
- **shared** (new): `get_shared_db_manager()`, used for users and LOA.

No behaviour changes yet. Nothing calls the shared manager until step 04.

**Preconditions:** step 02 committed. The shadow DB is running (`docker start afdf-shadow`).

## Changes

### `database/db_manager.py`
1. Move the `postgres://` → `postgresql+asyncpg://` rewrite out of `_build_database_url` into a module function `_to_asyncpg_url(url: str) -> str`. It also handles `postgresql://` (Supabase hands out that form) and leaves `postgresql+asyncpg://` unchanged. `_build_database_url` calls it, so local behaviour stays identical.
2. Add, mirroring `_db_manager` and `get_db_manager`:
   ```python
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
   ```
3. `close_database()` also closes and resets `_shared_db_manager`.
4. Do **not** change pool settings, `initialize()` or the query helpers.

### `database/__init__.py`
Export `get_shared_db_manager`.

### `.env.example`
Add, with a comment:
```
# Shared Supabase DB: use the SESSION pooler string (port 5432), add ?ssl=require
SUPABASE_DATABASE_URL=postgresql://postgres.<project-ref>:<password>@<pooler-host>:5432/postgres?ssl=require
```

### `tests/conftest.py`
- Add a fixture `shared_db`: skip if `TEST_SHARED_DATABASE_URL` is unset, and `monkeypatch.setenv("SUPABASE_DATABASE_URL", <it>)`.
- The autouse teardown already calls `close_database()`, which now closes both.

## Tests: `tests/test_db_manager.py`

| ID | Test |
|---|---|
| C1 (unit) | `_to_asyncpg_url("postgres://u:p@h:5432/d")` and `_to_asyncpg_url("postgresql://u:p@h:5432/d")` both give `"postgresql+asyncpg://u:p@h:5432/d"`. An asyncpg URL is unchanged. A query string (`?ssl=require`) is kept. |
| C2 (unit) | With `SUPABASE_DATABASE_URL` unset (`monkeypatch.delenv(..., raising=False)`), `await get_shared_db_manager()` raises `RuntimeError` with `SUPABASE_DATABASE_URL` in the message. |
| C3 (`local_db`) | `DatabaseManager()` with only `DATABASE_URL` set builds the same URL as before the change (assert `.database_url`). |
| C4 (`shared_db`) | `(await get_shared_db_manager()).health_check()` is True. `SELECT to_regclass('military.leave_requests')` is not null, so we are on the shadow DB. |
| C5 (`local_db` + `shared_db`) | The two managers are different objects with different `database_url`s. After `close_database()`, both module globals are `None`. |

All step 01 tests must still pass unchanged, in particular **S1**: settings still go to the local DB.

## Done when

- C1–C5 and the full suite pass.
- `python -c "import discord.bot"` still imports without error (run from the repo root with the venv).
- Committed as `migration step 03: shared db connection`.
