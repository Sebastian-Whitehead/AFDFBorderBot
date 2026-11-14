# AFDFBorderBot

Discord bot (nextcord) for the AFDF server: border approval, enlistment, events, LOA, border-officer monitoring. PostgreSQL via async SQLAlchemy.

## Run
- `python main.py` (entry point; calls `discord.run_bot`). Needs `.env` (see `.env.example`, `DISCORD_TOKEN`).
- Docker: see DOCKER.md (`docker-compose` profiles: database, bot, full). Dev flow = DB in Docker, bot local.
- No test suite exists.

## Layout
- `discord/` is a LOCAL package, not the pip `discord` lib (the bot uses `nextcord`). Don't rename it or add a pip `discord.py`.
  - `bot.py` create_bot/load_extensions; `config.py` settings cache (load_settings/get_setting/update_setting).
  - `commands/` cogs (Checkpoint, Enlistment, GuildEvent, LOA, SettingsManagement, UserManagement); `listeners/` cogs (BorderOfficerMonitor, GuildEventListener, JoinLeaveHandler); `utils/` (EmbedProcessor, RankManager).
- `database/`: `db_manager.py` (global manager via `get_db_manager()`, the most-connected node), `models.py`, `*_functions.py`, `settings_manager.py`, `transaction_log.py`. Settings live in the DB (`BotSetting`), loaded async at startup.
- `embeds/`, `Settings.json`, `ids.json`: static config/data. `init.sql`: DB schema.

## Gotchas
- `requirements.txt` is UTF-16 encoded; rewrite it as UTF-16 or convert deliberately, don't append with a UTF-8 tool.
- Settings manager init is async; recent fixes touched this, so await it before reading settings.
- `.env`, `pgadmin-data/`, `venv/` are local-only; never read or commit secrets.

## Knowledge graph
`graphify-out/` (gitignored) holds `graph.json`, `GRAPH_REPORT.md`, `graph.html`. For architecture questions use `/graphify query "<question>"` before grepping. Rebuild with `/graphify . --update` after big changes.

## Conventions
- Branch: work on `dev`, PRs target `main`.
- Ponytail mode: smallest complete change, no unrequested features.
