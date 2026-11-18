# Task: identity and service-record merging (plan + prompt for a new session)

You are continuing work on AFDFBorderBot. Read `CLAUDE.md` first, then this file. Everything here has been agreed with the user.
Work on the `supabase` branch. Keep code as simple as possible (ponytail mode: smallest complete change, no unrequested features).

## Hard rules

- **Do not touch the production Supabase DB** (no `apply_migration`, no writes through `execute_sql`). Read-only queries through the Supabase MCP are fine (e.g. to read a function definition). All SQL is developed and tested on the **shadow DB** (docker container `afdf-shadow`, port 54329). When it all passes there, stop and wait for the user's explicit go-ahead before anything goes to production.
- Never read or commit `.env` / `.env.test`.
- Do not commit or push unless the user asks.
- Start Docker Desktop if `docker info` fails. The shadow DB is rebuilt with `bash migration/build_shadow.sh` (it applies every `migration/sql/*.sql` in order, so new migrations are picked up). `TEST_SHARED_DATABASE_URL` is already in `.env.test`.
- Tests: `venv/Scripts/python.exe -m pytest -q` (whole suite takes about 7s with the DBs up).

## Current repo state (uncommitted when this was written)

- `migration/sql/003_ensure_player_account_steam_or_discord.sql`: new version of `public.fab_ensure_player_account(p_alias, p_steam_id, p_discord_id)` that accepts a Steam ID, a Discord ID, or both. Applied to the shadow DB only, **not production**. Production still has the old function (it rejects a NULL Steam ID).
- `database/user_functions.py`: `ensure_player_identity` now always calls that function (the direct-insert branch for a missing Steam ID was removed). It needs 003 to be live to work against production, so 003 must be applied before the bot is deployed.
- Plan for production later: apply 003, then 004, then 005 (below), then deploy the bot.

## Background facts (verified on the shadow DB and the live definition)

- `public.identities_player(id, created_at, alias, steam_id, discord_id, details jsonb)`. Partial unique indexes: one row per non-null `steam_id`, one per non-null `discord_id`.
- Only two tables reference `identities_player(id)`, both `ON DELETE RESTRICT`: `economy.accounts.player_identity_id` and `military.service_records.player_identity_id`.
- Tables referencing `military.service_records(id)`: `service_events`, `attendance`, `leave_requests`.
- Trigger `create_default_account_for_player` (after insert on `identities_player`) creates the "Main" bank account (0 money). The functions never insert accounts themselves.
- Unique indexes that a merge must respect:
  - `economy.accounts`: one `Main` per player (`economy_accounts_one_main_per_player`), unique `(player_identity_id, lower(account_name))` for non-archived rows (`accounts_player_name_unique`).
  - `military.service_records`: unique `(player_identity_id, organization_id)`.
  - `military.attendance`: unique `(service_record_id, session_id)`.
  - `military.leave_requests`: one `active` request per record (`leave_requests_one_active`).
- The bot's single organization is `ORG` (see `user_functions.py`, `AFDF-Para Raiders`).
- Existing function names use the `fab_` prefix. Keep it.
- `set_steam_id` in `database/user_functions.py` and `/add_steam` in `discord/commands/UserManagement.py` are what is being replaced. `confirm(interaction, embed_file, ...)` in `discord/utils/confirm.py` is the shared Approve/Decline prompt (needs a deferred interaction). Embeds live in `embeds/*.json` (see `delete_session_warning.json` for a warning-embed example). Slash commands that touch the DB call `interaction.response.defer()` first. Command names use underscores.
- Look up Steam input with `resolve_steam_id` (`discord/utils/steam.py`), as `/add_steam` does today.

## Feature summary

Three Discord commands, all Leadership-only (`@commands.has_role(LEADERSHIP_ROLE_ID)`):

| Command | Behaviour |
|---|---|
| `/add_steam user steam_url` | Attach a Steam ID to the member. If an identity with that Steam ID already exists with **no** Discord ID, merge it into the member's identity (bank accounts follow). If that Steam identity already has a Discord ID, return an error. No confirmation prompt. |
| `/force_merge user steam_url` | **Confirmation prompt first** (shows what will happen). Forces the identity linked to the Discord user to merge with the Steam identity, ignoring existing IDs even if each side already has other IDs. |
| `/merge_service_records user steam_url` | Merges the service record on the Steam identity into the member's record. **Also has the confirmation prompt** (it deletes the Steam identity's record and overwrites the member's rank and status with the Steam record's). |

Order dependency to put in the error text: if both identities have a service record, `/force_merge` fails with `service_record_conflict`. Tell the user to run `/merge_service_records` **first**, then `/force_merge`.

## SQL function 1: `public.fab_merge_player_identities(p_steam_id bigint, p_discord_id bigint, p_force boolean default false) returns jsonb`

File: `migration/sql/004_merge_player_identities.sql`. `LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public','pg_temp'` like `fab_ensure_player_account`. Copy that function's `EXECUTE` grants (check them on the shadow DB; the live ones can be read via the Supabase MCP, read-only). Take advisory locks (steam first, then discord, same key formats as 003) so concurrent calls cannot deadlock.

A = identity with `steam_id = p_steam_id`. B = identity with `discord_id = p_discord_id`.

| Situation | Result |
|---|---|
| A and B both missing | error `no_identity` |
| A == B (same row) | return `already_linked` |
| A missing, B exists | B has no Steam ID or `p_force`: set B.steam_id → `linked`. Else error `different_steam` |
| A exists, B missing | A has no Discord ID or `p_force`: set A.discord_id → `linked`. Else error `steam_linked_to_other_discord` |
| A and B both exist, different rows | see merge steps below |

Merge steps (A and B different rows):
1. If A has a Discord ID and not `p_force`: error `steam_linked_to_other_discord`.
2. If B has a (different) Steam ID and not `p_force`: error `different_steam`.
3. If both A and B have a service record for the same organization: error `service_record_conflict` (always, even with force). Run the service record merge (function 2) first.
4. **Pick the survivor (S) and the loser (L) by content, not by which ID is the Discord one:** the identity that has a service record for the organization survives. If neither has one, B (the Discord identity) survives. Why: the survivor keeps its real "Main" bank account under that name, and the member's original identity, id and history. Example: a member loses their Discord account. Old identity X (Steam ID, old Discord ID, record, money) and a new empty identity Y (new Discord ID, from `/approve`): X survives and takes the new Discord ID, Y is the loser.
5. Rename any of L's bank accounts whose `lower(account_name)` collides with one of S's (including `Main`) by appending ` (merged from <L.id>)`, so the unique indexes hold. **Balances are not combined.** Both accounts live on under S. (An empty, unused account from L is just clutter; deleting zero-balance, no-history accounts is optional and not required.)
6. Repoint all of L's `economy.accounts` and L's service record (if any) to S.
7. Remember L's alias, details, steam_id, discord_id, then delete L (clears the unique indexes).
8. Set S.steam_id = `p_steam_id` and S.discord_id = `p_discord_id` (whichever differs). Steam is truth here too: if the Steam identity (A) is the loser, its alias (when not null) and details (merged over S's, A's keys winning) overwrite S's. If A is the survivor, its own values simply stay (B's alias/details only fill in where A's are null). (With force, S's old Steam or Discord ID is overwritten and is no longer attached to anyone.)
9. Return `{result: 'merged', identity_id: S.id, accounts_moved: n, removed: {id, alias, steam_id, discord_id, details}}`. The `removed` values give the user and the bot log something to rebuild from, since there is no undo.

Return shape for the other results: `{result: 'linked'|'already_linked', identity_id: n}`.
Errors are `RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='<code>'`. Codes: `no_identity`, `steam_linked_to_other_discord`, `different_steam`, `service_record_conflict`, `invalid_player_identifier` (both IDs NULL).

## SQL function 2: `public.fab_merge_service_records(p_from_record_id bigint, p_to_record_id bigint) returns jsonb`

File: `migration/sql/005_merge_service_records.sql`. Same function settings and grants as function 1. No force flag: it always behaves like this.

**Rule: the Steam identity's record is the source of truth.** On any conflict between the two records, the "from" (Steam) side wins and the Discord side's conflicting value is ignored. Nothing is reconciled by hand afterwards unless the user fixes it (e.g. with `/set_rank`). The "to" (Discord) record row survives, so it keeps its id, its attendance and its LOA history.

1. Errors: `record_not_found` (either id missing), `same_record`, `different_organization`.
2. Copy the "from" record's `current_rank` and `service_status` onto the "to" record (even if that lowers the rank: Steam is truth, e.g. Steam EN1 and Discord EN2 gives EN1). Do not recompute from events.
3. Repoint all of the "from" record's `service_events` to the "to" record.
4. `attendance`: for sessions both records have, the "from" (Steam) row wins: delete the "to" row, then repoint all of the "from" rows to the "to" record.
5. `leave_requests`: if both records have an active request, keep the "from" (Steam) one and cancel the "to" one (set its status the way the existing code cancels; check `database/loa_functions.py`). Repoint all the "from" requests to the "to" record.
6. Delete the "from" record.
7. Return `{result: 'merged', events_moved, attendance_moved, attendance_replaced, leave_moved, leave_cancelled, removed: {id, current_rank, service_status}, previous: {current_rank, service_status}}`. `previous` is the "to" record's own rank/status before it was overwritten, for the bot log and the Discord reply.

## Python data layer (`database/user_functions.py`)

Contract (so work can run in parallel):
- `async def merge_identities(discord_id: str, steam_id: str, force: bool = False) -> str`: calls function 1 and returns `"merged"`, `"linked"`, `"already_linked"`, one of the SQL error codes, or `"error"`. Log the `removed` payload with `logger`/`print` the way the file already reports errors.
- `async def merge_service_records(discord_id: str, steam_id: str) -> str`: looks up the AFDF record on each identity (steam identity = from, discord identity = to), then calls function 2. Returns `"merged"`, `"no_identity"`, `"no_record"` (either side has none), `"record_not_found"`/`"same_record"`/`"different_organization"`, or `"error"`.
- `async def get_merge_preview(discord_id: str, steam_id: str) -> dict`: plain SELECTs returning, for the Steam identity and the Discord identity, alias, steam_id, discord_id, has-service-record (and its rank), number of bank accounts. Used to build the confirmation prompt. No writes.
- `set_steam_id` becomes a thin wrapper around `merge_identities(..., force=False)` (or is replaced by it). Keep a single code path.
- All DB access goes through the shared engine (`get_shared_db_manager`), inside one session/transaction per call.

## Discord layer (`discord/commands/UserManagement.py`)

- Update `/add_steam` to call `merge_identities` and map result codes to ephemeral messages. `service_record_conflict` -> "both have service records, run `/merge_service_records` first, then `/force_merge`". `steam_linked_to_other_discord` -> error that the Steam ID already belongs to another Discord user.
- Add `/force_merge` and `/merge_service_records` (same `user` + `steam_url` arguments, `defer` first, `resolve_steam_id` for the URL). Both build a warning embed from `get_merge_preview` (which also says which identity will survive, using the same rule as step 4), then `confirm(...)`, then act, then report. `/force_merge` must state: the member's old Steam ID will no longer be attached to anyone, any old Discord ID on the surviving identity is replaced, bank accounts keep separate balances under the surviving identity, and the identity without a service record (the Steam-only one if neither has one) is deleted. `/merge_service_records` must state that the Steam identity's record is deleted, that the member's rank and status become the Steam record's (show current vs resulting rank), and that Discord rank roles are **not** changed automatically (use `/set_rank` to fix roles). The reply after acting reports the resulting rank and the previous one.
- New embed JSON files under `embeds/` for the two warning prompts.

## Work breakdown (workers)

Define the contracts above first, then these can run in parallel:

1. **SQL worker A**: 004 (function 1) plus shadow DB tests covering every row of the table above, rollback-style. Include: bank account name collisions, A with a service record and B without (A survives), B with one and A without (B survives), neither has one (B survives), both with one (error), force overriding a different Steam ID and a different Discord ID, and the lost-Discord-account case (old identity with Steam ID + old Discord ID + record + balance, plus a new empty Discord-only identity: the old identity survives with the new Discord ID and keeps its 'Main' balance; also the variant where the new Discord user has no identity yet).
2. **SQL worker B**: 005 (function 2) plus shadow DB tests: events moved, same-session attendance in both (Steam row wins), two active leave requests (Steam one stays active, Discord one cancelled), Steam rank EN1 vs Discord rank EN2 gives EN1 and a Steam status of discharged vs active gives discharged, record on only one side (`no_record` is handled in Python), different organizations.
3. **Python worker**: the data layer above plus `shared_db` tests (see `tests/test_user_functions_shared.py` and `tests/helpers.py`). Update existing `set_steam_id` tests.
4. **Discord worker**: the three commands, embeds, cog tests with mocks (see `tests/test_user_management_cog.py`), and the `COMMANDS.md` rows for `/add_steam`, `/force_merge`, `/merge_service_records`.
5. **Integration (lead)**: rebuild the shadow DB with `build_shadow.sh`, run the full suite, review the whole diff for the points in "Hard rules", fix anything.
6. **Production (only after the user says go)**: apply 003, 004, 005 to the Supabase project (via `apply_migration`), then deploy the bot.

## Done when

- Shadow DB rebuilt from scratch with 003-005 applies cleanly.
- Full suite passes (`182 passed, 7 skipped` was the baseline before this work).
- Report to the user: what was added, what was tested, anything not verified, and the exact list of migrations waiting for production.
