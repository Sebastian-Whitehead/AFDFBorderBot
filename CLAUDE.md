# AFDFBorderBot

Discord bot (nextcord) for the AFDF server: border approval, enlistment, events, LOA, border-officer monitoring. PostgreSQL via async SQLAlchemy.

## Run
- `python main.py` (entry point; calls `discord.run_bot`). Needs `.env` (see `.env.example`, `DISCORD_TOKEN`).
- Docker: see README.md (`docker-compose` profiles: database, bot, full). Dev flow = DB in Docker, bot local.
- Tests: `venv/Scripts/python.exe -m pytest`.

## Layout
- `discord/` is a LOCAL package, not the pip `discord` lib (the bot uses `nextcord`). Don't rename it or add a pip `discord.py`.
  - `bot.py` create_bot/load_extensions; `config.py` settings cache (load_settings/get_setting/update_setting).
  - `commands/` cogs (Attendance, Checkpoint, Enlistment, GuildEvent, Info, LOA, Session, SettingsManagement, UserManagement); `listeners/` cogs (BorderOfficerMonitor, GuildEventListener, JoinLeaveHandler); `utils/` (EmbedProcessor, RankManager, steam.py: Steam ID/URL resolution, confirm.py: shared Approve/Decline prompt, `confirm(interaction, embed_file, ...)`, needs a deferred interaction).
- `database/`: `db_manager.py` (global manager via `get_db_manager()`, local + shared engines), `models.py`, `user_functions.py`, `session_functions.py` (sessions), `attendance_functions.py` (attendance rows), `loa_functions.py`, `rank_codes.py` (ordered rank codes from ids.yml), `settings_manager.py`. Settings live in the local DB (`BotSetting`), loaded async at startup.
- Data split: shared Supabase holds users (`public.identities_player`, `military.service_records`/`service_events`) LOA (`military.leave_requests`), sessions and attendance (`military.sessions`, `military.attendance`); local DB holds `bot_settings` only. The bot never reads/writes `economy.*` and never handles money.
- `embeds/`, `Settings.json`, `ids.yml`: static config/data. `init.sql`: DB schema.

## Gotchas
- `requirements.txt` is UTF-16 encoded; rewrite it as UTF-16 or convert deliberately, don't append with a UTF-8 tool.
- Settings manager init is async; recent fixes touched this, so await it before reading settings.
- `SUPABASE_DATABASE_URL` (session pooler, `?ssl=require`) is required for users/LOA; `STEAM_API_KEY` optional.
- `shared_db` tests need the shadow DB (`bash migration/build_shadow.sh`, `TEST_SHARED_DATABASE_URL` in `.env.test`); `db_local` tests need `TEST_LOCAL_DATABASE_URL`.
- `.env`, `pgadmin-data/`, `venv/` are local-only; never read or commit secrets.
- Slash commands that touch the DB call `interaction.response.defer()` first and reply with `followup` (Supabase can exceed Discord's 3s limit).
- The active attendance list is in memory in the Attendance cog (lost on restart).
- LOA commands are `/loa`, `/loa_list`, `/loa_cancel` (underscores, not hyphens).

## Knowledge graph
`graphify-out/` (gitignored) holds `graph.json`, `GRAPH_REPORT.md`, `graph.html`. For architecture questions use `/graphify query "<question>"` before grepping. Rebuild with `/graphify . --update` after big changes.

## Conventions
- Branch: work on `dev`, PRs target `main`.
- Ponytail mode: smallest complete change, no unrequested features.
