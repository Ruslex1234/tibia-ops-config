# bastex_online Lambda

Runs every minute (EventBridge rule `per_minute`), fetches online players for
each world from TibiaData, renders the Online Tracker HTML to S3, and sends
Telegram login/logoff alerts.

## Where things live

| What | Where | How it ships |
|---|---|---|
| Player lists (alerts, trolls, block, bastex) | `.configs/*.json` | `publish-configs-to-s3` on merge, live next run |
| Worlds, guilds, colors, thresholds | `.configs/settings.json` | same as above |
| Code | `lambda/bastex_online/*.py` | `deploy-lambda` on merge |
| Secrets, bucket names, output file name | Lambda environment variables | AWS console only, never in git |

On each run the handler loads `configs/combined.json` from S3 and applies its
`settings` block over the env/default values in `config.py`. A missing or
invalid key is logged and skipped, so a bad commit falls back to the previous
behavior instead of breaking the tracker.

## settings.json keys

| Key | Type | Effect |
|---|---|---|
| `worlds` | list of names | Worlds to fetch and display, in display order. Also used by `scripts/` |
| `premium_vocations` | list | Vocations that trigger Alerts and Telegram pings |
| `special_guilds` | list | Highlighted yellow/orange (orange at level 300+) |
| `dan_guilds` | list | Highlighted pink |
| `priority_categories` | list | Categories shown first in each world |
| `green_categories` | list | Highlighted green |
| `color_map` | object | Category name to hex color fallback |
| `min_level_filter` | int | Players at or below this level are hidden |
| `alert_hours_threshold` | int | Tracked players online longer than this are grayed out |
| `max_failure_rate` | int (0 to 100) | Percent of worlds that may fail before the run aborts |
| `abort_on_server_error` | bool | Abort the run on any TibiaData 5xx |

## Environment variables (set in AWS, not here)

`TELEGRAM_BOT_TOKEN`, `CHAT_ID_*`, `BUCKET_NAME`, `OUTPUT_FILE_NAME`,
`CONFIG_S3_BUCKET`, `CONFIG_S3_KEY`, `ONLINE_STATUS_KEY`, `BASE_API_URL`.
`WORLDS` and `PREMIUM_VOCATIONS` still work as fallbacks but `settings.json`
wins when present.
