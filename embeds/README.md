# Embeds

Each `*.json` here is a Discord message (Discord's embed JSON). Edit the text, colours, fields and images freely. The bot reads the file every time it sends, so no code change is needed (restart only if `embeds/` is baked into a Docker image).

Write `{name}` where a value should be filled in. Preview the welcome messages with `/test-msg`.

## Placeholders that work in every embed

| Write | Becomes |
|---|---|
| `{channel:loa_txt}` | a clickable channel mention. The name is any key under `channels` in `ids.yml`. |
| `{role:leadership}` | a role mention. Any single-id key under `roles` in `ids.yml` (not `citizen` or `ranks`: those hold several ids). |
| `{setting:modpack-url}` | the value of a bot setting (see `/settings list`). Falls back to `SETTING_DEFAULTS` in `afdfbot/config.py`. |

To use a new channel, add it to `ids.yml` and write `{channel:<its key>}`. No Python needed.

## Placeholders a command fills in

Listed per file in [placeholders.yml](placeholders.yml).

- `"member"` embeds (join, leave, approve, enlist) get `{user}` (mention), `{username}`, `{User}`, `{Username}`, `{userid}`, `{usertag}`.
- Other embeds list the exact names their command passes.

A new per-event value (for example a new field on the LOA embed) needs one line in the command that sends it, plus the name added to `placeholders.yml`.

`tests/test_embeds.py` fails if an embed uses a placeholder that isn't generic or listed, so typos get caught.
