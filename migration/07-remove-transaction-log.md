# Step 07: Remove the local transaction log

**Goal:** delete the unused `transaction_log` code. The bot does not handle money, so nothing replaces it.

**Preconditions:** step 06 committed.

## 1. Confirm it is unused

```bash
grep -rnE "transaction_log|add_transaction|get_unprocessed_transactions|get_transactions_by_(sender|recipient)|mark_transaction_processed|TransactionLog" \
  --include=*.py . | grep -v "^./venv/" | grep -v "^./tests/"
```
The only expected hits are in `database/transaction_log.py`, `database/__init__.py` and `database/models.py`. **STOP if** anything else shows up.

## 2. Export old rows (a backup only; they are not migrated anywhere)

From the **dev** database (`AFdb`), not the test one:
```bash
mkdir -p migration/backup
docker compose exec -T postgres psql -U postgres -d AFdb -c "\copy transaction_log TO STDOUT WITH CSV HEADER" > migration/backup/transaction_log.csv
```
Report the row count to the user (`wc -l` minus 1). `migration/backup/` is gitignored.

## 3. Delete

- Delete `database/transaction_log.py`.
- In `database/__init__.py`, remove its import line and the three names from `__all__`.
- In `database/models.py`, remove the `TransactionLog` class and any imports that become unused.

The `transaction_log` table is dropped from `init.sql` in step 09, not here. The test DB still has it, and that's harmless.

## Tests

| ID | Test |
|---|---|
| T1 | The grep from section 1 returns nothing. |
| T2 | `tests/test_imports.py` (new): importing `database`, `discord.bot` and every module in `discord/commands` and `discord/listeners` succeeds. Use `pkgutil.iter_modules` over the two folders and `importlib.import_module` on each. |
| T3 | The full suite passes. |

## Done when

T1–T3 pass. Committed as `migration step 07: remove transaction log`.
