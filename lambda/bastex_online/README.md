# bastex_online Lambda

Runs every minute (EventBridge rule `per_minute`), fetches online players for
each world from TibiaData, renders the Online Tracker HTML to S3, and sends
Telegram login/logoff alerts.

Nothing configurable is hardcoded in the code. There are two sources:

| What | Where | How it ships |
|---|---|---|
| Player lists (alerts, trolls, block, bastex) | `.configs/*.json` | config publish on merge, live next run |
| Everything else configurable | `.configs/settings.json` | same |
| Private values | GitHub secrets | `deploy-lambda` copies them into the Lambda env |
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
| `telegram.alert_recipients` | Names from the `TELEGRAM_CHAT_IDS` secret that receive alerts |
| `telegram.login_message` / `logoff_message` | Alert text. `{name}` and `{duration}` are filled in |
| `api` | TibiaData URL (`{world_name}` is filled in), timeouts, retries, parallel requests (0 = one per world) |
| `storage` | S3 object keys for the online-status tracker and the last-known-data cache |
| `page` | Title, auto-refresh, freshness colors (`fresh_minutes`, `stale_minutes`), profile and extra character links (`{name}` is filled in), server-type filter chips |
| `death_watch` | Guild to world map whose members' death lists `scripts/check_online_enemies.py` checks |

## GitHub secrets

`deploy-lambda` replaces the function's whole environment with these on every
deploy. To change one, update the secret and run the workflow by hand.

| Secret | Lambda env var |
|---|---|
| `LAMBDA_FUNCTION_NAME` | (which function to deploy) |
| `LAMBDA_BUCKET_NAME` | `BUCKET_NAME` |
| `LAMBDA_OUTPUT_FILE_NAME` | `OUTPUT_FILE_NAME` |
| `S3_BUCKET` | `CONFIG_S3_BUCKET` |
| `TELEGRAM_BOT_TOKEN` | `TELEGRAM_BOT_TOKEN` |
| `TELEGRAM_CHAT_IDS` | `TELEGRAM_CHAT_IDS`, JSON like `{"mykera": "-100123", "rod": "456"}` |
