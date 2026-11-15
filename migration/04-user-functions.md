# Step 04: Move `database/user_functions.py` to Supabase

**Goal:** reimplement `create_user`, `get_user_info`, `modify_user`, `search_users` and `get_user_stats` on the shared DB, with the same signatures and return shapes **minus money**, so contract tests U1–U7 pass unchanged against the shadow DB. Also add the one function the `/user` cog needs (step 06).

**The bot does not touch money.**
- Remove the `money` parameter from `create_user` and `modify_user`, and the `money` key from every returned dict.
- Never query or modify `economy.*`. Never call economy functions.

**Preconditions:** step 03 committed, shadow DB running.

## Data model (decisions D2–D3)

A **bot user** is a `public.identities_player` row that has a `military.service_records` row in organization `AFDF-Para Raiders`.

| Old `users` field | New source |
|---|---|
| `id` | `identities_player.id` |
| `name` | `identities_player.alias` |
| `steam_id`, `discord_id` | `identities_player.steam_id` / `discord_id` (bigint). **Return them as `str`** (callers compare strings) and accept `str` input (`int(identifier)`). |
| `joined_at` | `identities_player.created_at` |
| `rank` (int level) | `service_records.current_rank` (code), converted with `database/rank_codes.py` |
| `enlisted`, `enlisted_at` | D3: take the newest `service_events` row of type enlisted, reenlisted or discharged for the record. `enlisted` = that row's type is enlisted or reenlisted. `enlisted_at` = its `occured_at` when enlisted, else `None`. |
| `notes`, `achievements`, `deaths`, `last_death`, `reprimands`, `extra_data` | keys of `identities_player.details` (D2). `deaths` defaults to `0` and the others to `None` when missing. `last_death` is stored as an ISO date string and returned as `datetime.date`. |
| `money` | **dropped** |

Look up the AFDF-Para Raiders org id once per call: `SELECT id FROM public.identities_organizations WHERE name = 'AFDF-Para Raiders'`.

## New file: `database/rank_codes.py`

```python
"""Rank level (int, used by the bot) <-> rank code (text, stored in Supabase), from ids.json."""
import json
from pathlib import Path

_RANKS = {int(k): v["code"].strip() for k, v in
          json.loads((Path(__file__).parent.parent / "ids.json").read_text(encoding="utf-8"))["roles"]["ranks"].items()}

def level_to_code(level: int) -> str:
    return _RANKS[level]          # KeyError -> caller treats as invalid rank

def code_to_level(code: str) -> int:
    for level, c in _RANKS.items():
        if c == code:
            return level
    raise KeyError(code)
```

## Rewrite `database/user_functions.py`

- Use `get_shared_db_manager()` and raw SQL through `sqlalchemy.text` with **named parameters** (never f-strings with values). Qualify every table with its schema.
- **One session per function, one commit.** All writes of a call either all happen or none do.
- Keep the existing error contract: on any exception, log and return `None`, `False`, `[]` or the zero-stats dict exactly as today.

### Behaviour per function

**`create_user(name, steam_id, discord_id=None, rank=0, notes=None, enlisted=False)`**
1. Validate that `steam_id` (and `discord_id` if given) are numeric and that `rank` is a known level. Otherwise return `None`.
2. If an identity with this steam_id **already has an AFDF-Para Raiders service record**, return `None`. If another identity holds this discord_id, return `None`.
3. `SELECT public.fab_ensure_player_account(:name, :steam, :discord)`. It creates the identity or returns the existing one; ignore its JSON result.
   - If the identity existed without a discord_id and one was given, set it.
   - If it existed with a different, non-null discord_id, return `None` and roll back.
4. Insert into `military.service_records` (`player_identity_id`, `organization_id=AFDF-Para Raiders`, `current_rank=level_to_code(rank)`, `service_status='active'`). If `enlisted`, add a `service_events` row (`event_type='enlisted'`, `rank=code`, `occured_at=now()`).
5. If `notes`, merge `{"notes": notes}` into `details` (`coalesce(details,'{}'::jsonb) || jsonb_build_object(...)`).
6. Return the same dict shape as today, without `money`.

**`get_user_info(identifier)`** matches `discord_id = :n OR steam_id = :n` among bot users. It returns the full dict (keys as today minus `money`) or `None`. A non-numeric identifier returns `None`.

**`modify_user(identifier, name=None, rank=None, notes=None, enlisted=None, reason=None)`**. The new optional `reason` goes to the rank event's notes.
- `name` updates `alias`.
- `rank` updates `current_rank`, `updated_at=now()` and inserts a `rank_changed` event (`rank=code`, `notes=reason`).
- `notes` merges into `details`.
- `enlisted=True` inserts an `enlisted` event, or `reenlisted` if any `discharged` event exists. `enlisted=False` inserts a `discharged` event. `service_status` stays `'active'`, per D3.
- An unknown identifier returns `False`.

**`search_users(query)`**: `alias ILIKE '%' || :q || '%'` among bot users, `LIMIT 20`, with the same keys as today minus `money`.

**`get_user_stats()`**: `total_users` = number of AFDF-Para Raiders service records. `enlisted_users` = how many of those are enlisted per D3.

### New function (needed by step 06; export it from `database/__init__.py`)
- `get_user_count_by_rank() -> dict[int, int]` maps rank level to the count of bot users.

### Remove the old model
Delete the `User` class from `database/models.py` and its import in `user_functions.py`. **STOP if** anything else imports `User` (`grep -rn "models import" .`).

## Tests

1. **Switch** `tests/test_user_functions_contract.py` from the `local_db` fixture to `shared_db`. **Do not change any assertion** in U1–U7. If one fails, the implementation is wrong, not the test. The only allowed test change is the fixture name.
2. Extend `cleanup()` in `tests/helpers.py` for the shared DB. Delete in this order, matching test players by `steam_id BETWEEN 76561190000000000 AND 76561190000999999 OR discord_id BETWEEN 900000000000000000 AND 900000000000999999 OR alias LIKE 'zz_test_%'`:
   1. `service_events` of their service records
   2. `service_records`
   3. the `economy.accounts` rows the identity trigger created for them (`player_identity_id IN (...)`). This is test cleanup on the shadow DB only, and the FK requires it. The bot code never does this.
   4. the identities

   Add an assert at the top of `cleanup()` that the URL host is `localhost`, so it can never run against production.
3. New `tests/test_user_functions_shared.py` (`shared_db`):

| ID | Test |
|---|---|
| U8 | **Adopt an existing game player:** call `fab_ensure_player_account('zz_test_game', s, NULL)` directly, then `create_user("zz_test_game", s, d)`. It returns a dict (not `None`), `get_user_info(d)` finds it, and only **one** identity has that steam_id. |
| U9 | `modify_user(d, rank=9, reason="r")` sets `rank == 9`, `current_rank == 'UO'`, and a `rank_changed` event with `notes == "r"`. |
| U10 | `get_user_count_by_rank` counts two test users under their levels (compare deltas). |
| U11 | `create_user` with `steam_id="abc"` returns None and nothing is inserted. |
| U12 | **No money access:** searching `database/user_functions.py` for any of `economy.`, `money`, `post_economy` or `fab_transfer` finds nothing. The returned dicts have no `money` key. |
| R1 (unit, `tests/test_rank_codes.py`) | `level_to_code(0) == "EN0"`, `level_to_code(7) == "EN7"` (the name in ids.json has a leading space, the code must not), `level_to_code(9) == "UO"`, `level_to_code(10) == "PRES"`. `code_to_level(level_to_code(n)) == n` for all levels. `level_to_code(99)` raises KeyError. |

## Done when

- U1–U7 pass on the shared DB with only the fixture changed, and U8–U12 and R1 pass.
- The LOA (L*) and settings (S1) tests still pass on the local DB.
- `grep -rn "get_db_manager" database/user_functions.py` returns nothing.
- Committed as `migration step 04: user functions on supabase`.
