# Step prompts

One prompt per step. Paste into a fresh session, one step at a time, in order.

## Worker rules (every prompt refers to these)

- The session that gets the prompt is the **lead**. It spawns workers with the Agent tool (general-purpose). It starts all workers that don't wait on anything in one message, so they run in parallel.
- Each worker gets the step file path, its task, and the exact files it owns. Workers edit only those files, never run git, never commit, and never write to production Supabase.
- Workers share the working tree (no worktree isolation), because they share the Docker databases and their files don't overlap.
- **Only the lead runs pytest.** Parallel test runs would clash on the shared test databases and their cleanup.
- "Waits on" means the lead does not start that worker or task until the named workers have reported back.
- If a worker hits a STOP condition, the lead stops everything and asks me.
- The lead runs the step's tests and the full suite (`venv/Scripts/python.exe -m pytest`), fixes failures (by itself or by sending the failure to the owning worker), and commits.

## 00: Decisions - Complete
```
Do migration step 00. Read migration/README.md and migration/00-decisions.md. No workers: this step is a conversation with me. Ask me each question D1–D4 with its default, record my answers in the file, update affected steps if I pick a non-default. No test suite exists yet, so verify by re-reading the file: every row has an answer and every non-default answer is reflected in the affected steps. Then commit.
```

## 01: Test harness and baseline
```
Do migration step 01. Read migration/README.md, migration/PROMPTS.md (worker rules) and migration/01-test-harness-and-baseline.md. Do not touch product code.
Workers, all started in parallel (the step file fixes the fixture names, so test writers don't need to wait):
- W1 tooling: requirements-dev.txt, pytest.ini, .gitignore, pip install (§1).
- W2 local test DB: create AFdb_test, load init.sql, write .env.test (§2).
- W3 harness: tests/conftest.py, tests/helpers.py (§3).
- W4 tests/test_user_functions_contract.py (U1–U7).
- W5 tests/test_loa_contract.py (L1–L7).
- W6 tests/test_settings_contract.py (S1).
Lead waits on W1–W6, then runs the full suite against AFdb_test, applies the xfail rules from §5, checks git diff --stat, and commits.
```

## 02: Shadow DB and schema
```
Do migration step 02. Read migration/README.md, migration/PROMPTS.md (worker rules) and migration/02-supabase-schema-and-shadow-db.md. Production stays read-only. First ask me for the session pooler string and put it in .env.test yourself.
Workers:
- W1 shadow DB (waits on the pooler string): dump, stubs.sql, restore, check restore-errors.txt, add TEST_SHARED_DATABASE_URL (§1–2).
- W2 migration/sql/001_bot_tables.sql (§3). Starts immediately.
- W3 tests/test_shadow_schema.py (SH1–SH5). Starts immediately.
Lead waits on W1 and W2, applies the SQL to the shadow DB twice (§4), then waits on W3 and runs SH1–SH5 and the full suite, then commits.
```

## 03: Shared DB connection
```
Do migration step 03. Read migration/README.md, migration/PROMPTS.md (worker rules) and migration/03-shared-db-connection.md. Start the shadow DB first (docker start afdf-shadow).
Workers, both started in parallel:
- W1 code: database/db_manager.py, database/__init__.py, .env.example.
- W2 tests: shared_db fixture in tests/conftest.py, tests/test_db_manager.py (C1–C5).
Lead waits on W1 and W2, runs C1–C5, the full suite and the import check, then commits.
```

## 04: User functions on Supabase
```
Do migration step 04. Read migration/README.md, migration/PROMPTS.md (worker rules) and migration/04-user-functions.md. Shadow DB must be running.
Workers, all started in parallel (the step file fixes the rank_codes API, so W2 doesn't need to wait on W1):
- W1 database/rank_codes.py and tests/test_rank_codes.py (R1).
- W2 database/user_functions.py rewrite (no money), get_user_count_by_rank, export in database/__init__.py, remove User from database/models.py (STOP if anything else imports it).
- W3 tests: switch U1–U7 to shared_db (fixture only), extend cleanup() in tests/helpers.py with the localhost assert, write tests/test_user_functions_shared.py (U8–U12).
Lead waits on W1–W3, runs U1–U12, R1 and the full suite, does the grep check, then commits.
```

## 05: LOA on Supabase
```
Do migration step 05. Read migration/README.md, migration/PROMPTS.md (worker rules) and migration/05-loa.md. Shadow DB must be running. discord/commands/LOA.py must not change.
Workers, both started in parallel:
- W1 database/loa_functions.py rewrite, remove LOARequest from database/models.py (STOP if anything else imports it).
- W2 tests: switch L1–L7 to shared_db (fixture only), extend cleanup() for leave_requests before the identity deletes, write tests/test_loa_shared.py (L8–L11).
Lead waits on W1 and W2, runs L1–L11 and the full suite, checks git diff discord/commands/LOA.py is empty, then commits.
```

## 06: Fix the /user cog
```
Do migration step 06. Read migration/README.md, migration/PROMPTS.md (worker rules) and migration/06-user-management-cog.md.
First, yourself: write G0 in tests/test_user_management_cog.py and run it against the unmodified cog to confirm it fails.
Then workers, both started in parallel after G0 is confirmed failing:
- W1 discord/commands/UserManagement.py changes (remove money).
- W2 the rest of tests/test_user_management_cog.py (G1–G11).
Lead waits on W1 and W2, runs G0–G11, the full suite and the import check, then commits.
```

## 07: Remove transaction log
```
Do migration step 07. Read migration/README.md, migration/PROMPTS.md (worker rules) and migration/07-remove-transaction-log.md.
Workers, both started in parallel:
- W1 backup: export transaction_log from the dev AFdb to migration/backup/transaction_log.csv and report the row count (§2).
- W2 code: run the §1 grep (STOP if there are unexpected hits), delete the code (§3), write tests/test_imports.py (T2).
Lead waits on W1 and W2, tells me the row count, runs T1–T3, then commits.
```

## 08: Data migration script
```
Do migration step 08. Read migration/README.md, migration/PROMPTS.md (worker rules) and migration/08-data-migration-script.md. Shadow DB and local test DB must be running.
Workers, both started in parallel (the step file fixes the CLI and the report format, so the tests don't need to wait):
- W1 migration/migrate_to_supabase.py (idempotent, dry run, refuses a remote target without --allow-remote).
- W2 tests/test_migration_script.py with seed rows A–E and LOA1–LOA5 (M1–M8), plus any local cleanup extension in tests/helpers.py.
Lead waits on W1 and W2, runs M1–M8 test DB → shadow DB and the full suite, then commits.
```

## 09: Cutover
```
Do migration step 09. Read migration/README.md, migration/PROMPTS.md (worker rules) and migration/09-cutover.md. This writes to production: ask my approval before every write. Workers never write to production; only you do, after my approval.
Phase 1, pre-flight. Workers, all started in parallel (all read-only):
- W1 runs the full suite and reports the result (the one exception to "only the lead runs pytest"; nothing else runs tests in this phase).
- W2 runs the production duplicate checks (§1.2).
- W3 re-dumps the production schema and diffs it against migration/shadow/schema.sql (§1.3).
- W4 backs up the local AFdb (§1.4) and confirms the file isn't empty.
Wait on W1–W4. STOP if the suite isn't green, there are duplicates, or the schema changed in a way that matters.
Phase 2, yourself, strictly in order, no workers: apply the schema (§2), stop the bot (§3), dry run, then the real migration (§4), switch the bot (§5), smoke test with me (§6).
Phase 3, cleanup, only after the smoke test passes and I confirm. Workers, both started in parallel:
- W5 init.sql, database/models.py, tests/conftest.py (§7).
- W6 CLAUDE.md (§7).
Wait on W5 and W6, run the full suite again (fix tests broken by the cleanup), then commit.
```
