# Commands

All commands are slash commands. `?` marks an optional option. Commands that touch the database reply to the sender in the channel unless noted; attendance and session commands reply ephemerally (only the sender sees them).

**Access** is the role the command checks. "Anyone" means the bot does not check a role (server permissions on the command in Discord still apply).

- **Leadership**, **Border Officer**, **Civil Servant**: roles from `ids.json`.
- Names use underscores (`/loa_list`), except the `/settings` subcommands.

## Border and enlistment

| Command | Access | What it does |
|---|---|---|
| `/approve user steam_id?` | Border Officer | Lets someone through the border. Creates their player identity (with an optional SteamID64 or Steam profile URL), gives the citizen roles, removes the join role, and posts the new-citizen welcome in the main channel. The welcome can be turned off with the `new-citizen-welcome` setting. Does not create a service record. |
| `/enlist user msg?` | Leadership | Enlists a member. No service record: creates one at EN0, logs `enlisted`, gives the enlisted roles. Already active and enlisted: does nothing. Inactive record: sets it active again at their previous rank, logs `reenlisted`, gives the roles for that rank. The member must already have a player identity. `msg` true/false forces the welcome tour on or off for this enlistment; leave it out to follow the `enlist-welcome` setting. |
| `/discharge user reason?` | Leadership | Marks the member's service record `discharged`, logs a `discharged` event (with the reason as notes), and removes the enlisted and rank roles. Their rank is kept so `/enlist` can reinstate them. |
| `/retire user reason?` | Leadership | Retires a member: marks the service record `retired`, logs a `retired` event (reason as notes), removes their rank role and the military personnel role, and gives the Distinguished Citizen role. Their rank is kept. `/enlist` can reinstate them later. |

## Members and service records

| Command | Access | What it does |
|---|---|---|
| `/add_member user steam_id? service_record? rank? notes?` | Leadership | Adds a player identity (Discord, optional Steam ID, notes). `service_record: True` also creates the military service record at `rank` (default EN0). `rank` only applies with `service_record`. |
| `/add_steam user steam_url` | Leadership | Attaches a Steam ID (SteamID64 or profile URL) to the member. If an identity with that Steam ID already exists with no Discord ID, it is merged into the member's identity (bank accounts follow). Errors if that Steam ID belongs to another Discord user or the member has a different Steam ID. |
| `/force_merge user steam_url` | Leadership | Asks for confirmation, then merges the member's identity with the Steam identity even if either already has other IDs. The identity with a service record survives (the Discord one if neither has one); the other is deleted. Bank accounts move over with separate balances. If both have service records, run `/merge_service_records` first. |
| `/merge_service_records user steam_url` | Leadership | Asks for confirmation, then merges the service record on the Steam identity into the member's. The Steam record wins: rank and status are copied from it, and it is deleted. Events, attendance and LOA move over. Discord rank roles are not changed; use `/set_rank`. |
| `/create_service_record user rank` | Leadership | Creates the service record for an existing identity, with a `rank_changed` event ("Service record created") at that rank. No role changes. |
| `/create_service_event user type date rank? status? notes? details?` | Leadership | Adds an event to a member's service record. `type` is one of `enlisted`, `rank_changed`, `discharged`, `reenlisted`, `retired`, `reprimand`. `date` is UTC, `YYYY-MM-DD` or `YYYY-MM-DD HH:MM`. `details` is a JSON object. Only inserts the event; it does not change the record's rank or status. |
| `/promote user new_rank reason?` | Leadership | Promotes a member by one or two ranks, logs it on their service record, and swaps their Discord rank role. If the role swap fails, the rank change is kept and the reply says so. |
| `/demote user new_rank reason` | Leadership | Demotes a member to a lower rank, logs it on their service record, and swaps their Discord rank role (same failure handling as `/promote`). |
| `/reprimand user reason` | Leadership | Logs a `reprimand` event on a member's service record. |
| `/set_rank user rank reason?` | Leadership | Sets a member's rank directly, skipping the promotion rules (for corrections). Logs a `rank_changed` event and swaps their Discord rank role. Does nothing if the rank is unchanged. |
| `/edit_service_event event_id notes? status? rank? date? details?` | Leadership | Edits an existing service event; only the fields you give change. The event type can't be changed (delete and recreate it). Find event ids with `/service_record`. `details` replaces the old details. |
| `/delete_service_event event_id` | Leadership | Deletes a service event, after a confirmation prompt. |
| `/edit_member user name? notes?` | Leadership | Edits a member's name and/or notes. |

## Info

| Command | Access | What it does |
|---|---|---|
| `/profile user` | Anyone | A member's profile: rank, enlistment, joined date and stats. |
| `/service_record user rows?` | Anyone | The member's latest service events, newest first, with each event's ID. |
| `/ranks` | Anyone | The rank hierarchy. |
| `/ping` | Anyone | Checks the bot is alive (ephemeral). |

## Leave of absence (LOA)

LOA commands only work in the LOA channel when one is configured.

| Command | Access | What it does |
|---|---|---|
| `/loa start_date end_date? reason?` | Anyone | Submits or updates your LOA and posts the LOA embed. |
| `/loa_list` | Anyone | Lists all current active LOAs. |
| `/loa_cancel` | Anyone | Cancels your active LOA. |

## Sessions

| Command | Access | What it does |
|---|---|---|
| `/create_session name operation? description? start? external_event_id? timeline?` | Civil Servant | Creates a session record. `start` is UTC `YYYY-MM-DD HH:MM` (default: now); `timeline` defaults to `A`. |
| `/end_session end?` | Civil Servant | Ends the most recently started open session, after a confirmation prompt. `end` is UTC (default: now). |
| `/edit_session session_id name? operation? description? timeline? start? end?` | Civil Servant | Edits a session; only the fields you give are changed. |
| `/delete_session session_id` | Civil Servant | Permanently deletes a session, after a confirmation prompt. Refused if the session has attendance recorded. |
| `/session_list timeline? page?` | Anyone | Lists sessions, 10 per page, newest first. |

## Attendance

The active attendance list lives in the bot's memory (lost on restart) until you submit it. All attendance commands need the Civil Servant role.

| Command | What it does |
|---|---|
| `/start_attendance` | Starts a list from your voice channel. Members in the channel are `present`; anyone with an active LOA who is not in the channel is `on_leave`. Needs an open session. |
| `/modify_attendance session_id` | Loads an existing session's saved attendance to edit it. |
| `/view_attendance` | Shows the current list. |
| `/add_attendance user attendance_status?` | Adds someone, or changes their status (default `present`). |
| `/remove_attendance user` | Removes someone from the list. |
| `/discard_attendance` | Throws the list away; nothing is saved. |
| `/submit_attendance` | Saves the list to the database. Asks for confirmation first if people are unaccounted for. |
| `/attendance_history user rows?` | A member's attendance history: counts by status, attendance rate (present out of all recorded sessions), and their latest sessions (default 10, max 25). |

## Settings (Leadership)

Stored in the bot's local database and cached at startup.

| Command | What it does |
|---|---|
| `/settings list` | Shows the current values. |
| `/settings set setting value` | Turns a setting on or off: `listen-for-join-leave`, `new-citizen-welcome`, `enlist-welcome`, `listen-for-border-officer`, `listen-for-event-start`. |
| `/settings set-interval minutes` | Sets how often the border-officer monitor checks (1-60 minutes). |
| `/toggle_joinleave action` | `Enable`, `Disable` or `Status` for the join/leave messages (same as the `listen-for-join-leave` setting). |

## Settings reference

| Setting | Default | Effect |
|---|---|---|
| `listen-for-join-leave` | on | Posts join and leave messages. |
| `new-citizen-welcome` | on | `/approve` posts the new-citizen welcome in the main channel. |
| `enlist-welcome` | on | `/enlist` posts the AFDF welcome tour in the main channel (new enlistments only, not reinstatements). |
| `listen-for-border-officer` | on | Runs the border-officer monitor. |
| `listen-for-event-start` | off | Event-start listener (currently disabled in the bot). |
| `border-officer-check-interval` | see `/settings list` | Seconds between monitor checks; set with `/settings set-interval`. |
