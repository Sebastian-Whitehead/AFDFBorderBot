# Step 00: Confirm decisions with the user

**Goal:** lock the choices the later steps depend on. No code changes.

**Already decided by the user: the bot does not touch money.** Local `users.money`, `/give_money`, the money leaderboard and `transaction_log` are dropped, not migrated. The bot never reads or writes `economy.*`.

## Instructions

Ask the user each question below, showing the default. Record the answers in the "Answers" section of this file. Commit with `migration step 00: decisions`.

If the user picks a non-default answer, update the affected steps before moving on. The "Affects" column says which steps.

| # | Question | Default | Affects |
|---|---|---|---|
| D1 | Ranks `UO` (level 9) and `PRES` (level 10) are not allowed by Supabase's rank CHECK constraints. Add them to the constraints, or map them to existing codes (for example `OF1` / `OF11`)? | Add `UO` and `PRES` to both constraints | 02, 04 |
| D2 | Where do `notes`, `achievements`, `deaths`, `last_death` and `reprimands` go? | `identities_player.details` JSONB under top-level keys with those names. All 3 current players have `details = NULL`, so nothing collides. | 04, 08 |
| D3 | Meaning of "enlisted": every bot-created user gets a `military.service_records` row in org `AFDF-Para Raiders` with `service_status='active'`. `enlisted` is True when the newest event of type enlisted, reenlisted or discharged is enlisted or reenlisted. `enlisted_at` is that event's `occured_at`. OK? | Yes | 04, 08 |
| D4 | Test target for Supabase-shaped tests: a local "shadow" Postgres 17 built from a schema-only dump of production (free and isolated), or a paid Supabase branch? | Shadow DB | 02+ |

## Answers

All defaults accepted (no other steps changed).

| # | Answer |
|---|---|
| D1 | Add `UO` and `PRES` to both rank CHECK constraints |
| D2 | `identities_player.details` JSONB, top-level keys `notes`, `achievements`, `deaths`, `last_death`, `reprimands` |
| D3 | Yes: `AFDF-Para Raiders` service record, `enlisted` from newest enlisted/reenlisted/discharged event |
| D4 | Local shadow Postgres 17 from a schema-only dump |

## Tests

None. Done when every row above has an answer recorded.
