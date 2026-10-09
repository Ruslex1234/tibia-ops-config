# bastex_online Lambda

Runs every minute (EventBridge rule `per_minute`), fetches online players for
each world from TibiaData, renders the Online Tracker HTML to S3, and sends
Telegram login/logoff alerts.

Nothing configurable is hardcoded in the code. There are two sources:

| What | Where | How it ships |
|---|---|---|
| Player lists (alerts, trolls, block, bastex) | `.configs/*.json` | config publish on merge, live next run |
| Everything else configurable | `.configs/settings.json` | same |
| Private values | Lambda environment variables | set in the AWS console, never in git |
| Code | `lambda/bastex_online/*.py` | `deploy-lambda` on merge |

Every run loads `configs/combined.json` from S3 and validates its `settings`
block. If it is missing or invalid, the run uses the last good copy held by
the warm container, or aborts and leaves the current page untouched. The
tests run the same validator on `settings.json` in every PR, so a bad edit
fails CI before it can ship.

## settings.json

| Key | Effect |
|---|---|
| `worlds` | Worlds to fetch and show, in display order. Also used by `scripts/` |
| `premium_vocations` | Vocations that put a player from `alerts.json` in Alerts and trigger Telegram |
| `guilds.enemies` | Enemy guilds. `color` (orange) at `low_level_below` and up, `low_level_color` below it. `unguilded_label` is the category for players in `bastex.json` and non-premium players in `alerts.json` |
| `guilds.friends` | Friendly guilds, shown in `color` (green) |
| `guilds.dan` | Dan's guilds, shown in `color` (pink) |
| `lists` | Label and color for the categories built from the list files, plus `others` for everyone unmatched |
| `show_first` | Which `lists` categories appear at the top of each world, in order. Then enemies, friends, dan, other guilds, Others |
| `min_level` | Players at or below this level are hidden |
| `online_too_long` | Enemies and tracked players online longer than `after_hours` turn `color` (gray) |
| `abort` | Skip the run (page keeps its last state) when more than `max_failed_worlds_percent` of worlds fail, or on any TibiaData 5xx if `on_server_error` |
| `telegram.alert_recipients` | Who receives alerts. `mykera` reads the chat ID from the `CHAT_ID_MYKERA` env var |
| `telegram.login_message` / `logoff_message` | Alert text. `{name}` and `{duration}` are filled in |
| `api` | TibiaData URL (`{world_name}` is filled in), timeouts, retries, parallel requests (0 = one per world) |
| `storage` | S3 object keys for the online-status tracker and the last-known-data cache |
| `page` | Title, auto-refresh, freshness colors (`fresh_minutes`, `stale_minutes`), profile and extra character links (`{name}` is filled in), server-type filter chips |
| `death_watch` | Guild to world map whose members' death lists `scripts/check_online_enemies.py` checks |

## Environment variables (AWS console)

Private values stay in the Lambda's environment. Deploys only replace code
and never touch these.

| Variable | Purpose |
|---|---|
| `BUCKET_NAME` | Bucket for the HTML page and state files (required) |
| `OUTPUT_FILE_NAME` | Public HTML file name (required) |
| `CONFIG_S3_KEY` | Location of combined.json (required) |
| `CONFIG_S3_BUCKET` | Bucket holding combined.json, if not `BUCKET_NAME` |
| `TELEGRAM_BOT_TOKEN` | Bot token |
| `CHAT_ID_<NAME>` | One per alert recipient, e.g. `CHAT_ID_MYKERA` |

`WORLDS`, `PREMIUM_VOCATIONS`, `BASE_API_URL` and `ONLINE_STATUS_KEY` are no
longer read (they live in settings.json now) and can be deleted.

## Adding a guild

Edit `.configs/settings.json` on GitHub, add the name to
`guilds.enemies.names` (orange) or `guilds.friends.names` (green), commit.
It is live on the next one-minute run after the config publish finishes.
