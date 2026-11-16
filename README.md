# AFDF Border Bot

Discord bot (nextcord) for the AFDF server: border approval, enlistment, service records, LOA, events and border-officer monitoring.

## Setup

Requirements: Python 3.10+, Docker (for the local settings DB), a Discord bot token, a Supabase connection string.

```bash
cp .env.example .env            # then fill it in
pip install -r requirements.txt # UTF-16 encoded file
docker-compose --profile database up -d   # local Postgres (+ pgAdmin on :5050)
python main.py
```

Docker profiles: `database` (Postgres + pgAdmin), `bot` (bot + DB), `full` (everything). Production: `docker-compose --profile full up -d`; rebuild after code changes with `docker-compose build bot`. The local DB is `AFdb` on `localhost:5432` (user `postgres`, password `admin`), schema loaded from `init.sql`.

The bot role must sit above every role it manages. Needed permissions: Manage Roles, Manage Events, Manage Messages, Send Messages, View Channels, Connect, Embed Links, Use Slash Commands.

## Environment variables

| Var | Purpose |
|---|---|
| `DISCORD_TOKEN` | Bot token (required) |
| `DATABASE_URL` | Local Postgres, holds `bot_settings` only |
| `SUPABASE_DATABASE_URL` | Shared Supabase DB, session pooler (port 5432), add `?ssl=require` |
| `STEAM_API_KEY` | Optional. Resolves custom `steamcommunity.com/id/<name>` links; without it the bot uses the keyless profile XML (stricter rate limits) |

Tests read `.env.test`: `TEST_LOCAL_DATABASE_URL`, `TEST_SHARED_DATABASE_URL`, `SUPABASE_DUMP_URL` (used only to dump the production schema).

## Architecture

- `discord/` is a local package (not pip `discord`): `bot.py`, `config.py` (settings cache), `commands/` (Attendance, Checkpoint, Enlistment, GuildEvent, Info, LOA, Session, SettingsManagement, UserManagement), `listeners/` (BorderOfficerMonitor, GuildEventListener, JoinLeaveHandler), `utils/` (EmbedProcessor, RankManager, steam, `confirm.py`: shared Approve/Decline prompt that shows an embed from `embeds/`).
- `database/`: `db_manager.py` (local + shared engines), `user_functions.py`, `session_functions.py` (sessions), `attendance_functions.py` (attendance rows), `loa_functions.py`, `settings_manager.py`, `rank_codes.py`, `models.py`.
- `embeds/`, `Settings.json`, `ids.json`: static config and data.

Data split:

- **Supabase (shared with the game)**: `public.identities_player`, `military.service_records`, `military.service_events`, `military.leave_requests`, `military.sessions`, `military.attendance`, organization `AFDF-Para Raiders`. The bot never reads or writes `economy.*` and never handles money.
- **Local Postgres**: `bot_settings` only.
- Ranks are identified by code everywhere (`EN0`-`EN8`, `OF0`-`OF11`, `PRES`), defined in order in `ids.json` (`roles.ranks`: abbr, name, Discord role id) and read via `database/rank_codes.py`. Commands offer them as a dropdown.

Design decisions:

1. The rank CHECK constraints in Supabase allow exactly those 22 codes (`UO` is not a rank).
2. Extra identity data (notes, achievements, deaths, last_death, reprimands) lives in `identities_player.details` JSON.
3. `enlisted` is derived from the newest enlisted/reenlisted/discharged service event.
4. Tests use a local "shadow" Postgres 17 built from a schema-only dump of production.

## Commands

| Command | Who | What |
|---|---|---|
| `/approve user [steam_id]` | Border Officers | Steam ID as SteamID64 or profile URL (custom `/id/` links work). Creates the player identity in Supabase before changing roles; no service record |
| `/enlist user` | Leadership | Creates service record (rank `EN0`) + `enlisted` event before adding roles; needs an identity |
| `/add_member user [steam_id] [rank] [notes]` | | Identity + service record, no roles |
| `/add_steam user steam_url` | | Attach a Steam ID to an existing identity; never overwrites a different one |
| `/create_service_record user rank` | | Record plus a "Service record created" event, no roles |
| `/promote user new_rank [reason]`, `/demote user new_rank reason` | | Update record rank + `rank_changed` event; no Discord role swap |
| `/reprimand user reason` | | Logs a `reprimand` service event |
| `/profile user`, `/service_record user [rows]`, `/ranks`, `/ping` | | Read only |
| `/loa start_date [end_date] [reason]`, `/loa_list`, `/loa_cancel` | LOA channel only | Writes `military.leave_requests`; needs a service record |
| `/settings list\|set\|set-interval` | | Local DB settings |
| `/create_session name [operation] [description] [start] [external_event_id] [timeline]` | Civil servants | New `military.sessions` row. `start` is UTC `YYYY-MM-DD HH:MM` (default now); `timeline` defaults to `A` |
| `/end_session [end]` | Civil servants | Asks for confirmation (embed `end_session_warning.json`), then ends the open session with the latest start |
| `/edit_session session_id [name] [operation] [description] [timeline] [start] [end]` | Civil servants | Changes only the fields given; refuses an end before the start |
| `/session_list [timeline] [page]` | | 10 sessions per page, newest first, as a table embed (`session_list.json`) |
| `/start_attendance` | Civil servants | Needs an open session. Lists everyone in your voice channel; people on an active LOA are noted (on LOA but not in VC = `on_leave`) |
| `/add_attendance user [status]`, `/remove_attendance user`, `/view_attendance`, `/discard_attendance` | Civil servants | Edit, show or throw away the active list (`present`, `absent`, `on_leave`, `excused`) |
| `/submit_attendance` | Civil servants | Saves the list to `military.attendance` for the latest open session. Active service records not on the list are shown (`attendance_absent_warning.json`) and saved as `absent` after Approve; Decline returns to the list |
| `/modify_attendance session_id` | Civil servants | Loads a session's saved attendance as the active list; submitting saves back to that session. Removing someone does not delete their row, they become `absent` |

The active attendance list is in bot memory (one list for the whole bot): a restart loses it. Replies are private to the sender.

`/create_weekend_events` and the old voice-channel `/attendance` are commented out in `GuildEvent.py` (the Attendance cog replaces `/attendance`). `/leaderboard` was removed.

## Testing

```bash
venv/Scripts/python.exe -m pytest
```

- `db_local` tests need `TEST_LOCAL_DATABASE_URL`: a local `AFdb_test` database loaded from `init.sql`.
- `db_shared` tests need `TEST_SHARED_DATABASE_URL`: the shadow DB. Build it with `bash migration/build_shadow.sh`, which dumps the production schema via `SUPABASE_DUMP_URL`, starts container `afdf-shadow` on port 54329, loads `migration/shadow_stubs.sql`, the dump, then `migration/sql/*.sql`. Use `TEST_SHARED_DATABASE_URL=postgresql+asyncpg://postgres:shadow@localhost:54329/postgres`.

## History

The old local `users` / `loa_requests` tables were migrated to Supabase. The one-off migration script and the step-by-step plan docs were removed in the cleanup commit; see git history.
