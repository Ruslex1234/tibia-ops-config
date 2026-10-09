"""
Configuration for Bastex Online Lambda. Nothing configurable is hardcoded.

Two sources:
- Environment variables: private values only (bucket names, output file,
  Telegram token and chat IDs). Synced from GitHub secrets by the CD pipeline.
- settings: the "settings" block of combined.json, published from
  .configs/settings.json in GitHub. Parsed and validated on every run.
config.py
"""
import json
import os
import re
from dataclasses import dataclass

# ========== Private (environment) ==========
BUCKET_NAME = os.environ.get("BUCKET_NAME", "")
OUTPUT_FILE_NAME = os.environ.get("OUTPUT_FILE_NAME", "")
CONFIG_S3_BUCKET = os.environ.get("CONFIG_S3_BUCKET") or BUCKET_NAME
CONFIG_S3_KEY = os.environ.get("CONFIG_S3_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
REQUIRED_ENV = ("BUCKET_NAME", "OUTPUT_FILE_NAME", "CONFIG_S3_KEY")


def missing_env():
    """Names of required environment variables that are unset or empty."""
    return [k for k in REQUIRED_ENV if not os.environ.get(k)]


def telegram_chat_ids():
    """Recipient name -> chat ID, from the TELEGRAM_CHAT_IDS JSON env var."""
    try:
        ids = json.loads(os.environ.get("TELEGRAM_CHAT_IDS") or "{}")
    except ValueError:
        print("TELEGRAM_CHAT_IDS is not valid JSON; alerts disabled")
        return {}
    return {str(k): str(v) for k, v in ids.items()} if isinstance(ids, dict) else {}


# ========== Settings (from GitHub) ==========
LIST_KEYS = ("trolls", "alerts", "enemy_block", "others")
_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
_PVP_VALUE = re.compile(r"^[a-z0-9]*$")


class SettingsError(ValueError):
    """Raised with every problem found, so one run reports them all."""

    def __init__(self, errors):
        self.errors = errors
        super().__init__("; ".join(errors))


@dataclass(frozen=True)
class Settings:
    worlds: tuple
    premium_vocations: frozenset
    enemies: tuple
    enemies_set: frozenset
    enemy_color: str
    enemy_low_level_color: str
    enemy_low_level_below: int
    unguilded_enemy_label: str
    friends: tuple
    friends_set: frozenset
    friend_color: str
    dan: tuple
    dan_set: frozenset
    dan_color: str
    labels: dict           # list key -> category label
    label_colors: dict     # category label -> color
    show_first: tuple      # category labels
    min_level: int
    gray_after_hours: int
    gray_color: str
    max_failed_worlds_percent: int
    abort_on_server_error: bool
    alert_recipients: tuple
    login_message: str
    logoff_message: str
    world_url: str
    connect_timeout: float
    read_timeout: float
    retries: int
    retry_backoff: float
    max_parallel_requests: int
    online_status_key: str
    last_known_data_key: str
    page_title: str
    refresh_seconds: int
    fresh_minutes: int
    stale_minutes: int
    link_color: str
    profile_url: str
    character_links: tuple  # (label, url template)
    server_types: tuple     # (value, label)


# Set by the handler after a successful parse; read as config.settings.
settings = None


def _is_names(v):
    return (isinstance(v, list) and all(isinstance(x, str) and x.strip() for x in v)
            and len(set(v)) == len(v))


def _is_int(lo, hi=None):
    return lambda v: type(v) is int and v >= lo and (hi is None or v <= hi)


def _is_num(v):
    return type(v) in (int, float) and v >= 0


def _is_text(v):
    return isinstance(v, str) and v.strip() != ""


def _is_color(v):
    return isinstance(v, str) and bool(_COLOR.match(v))


def _is_url(placeholder):
    return lambda v: isinstance(v, str) and v.startswith("https://") and placeholder in v


def _formats(fields):
    def check(v):
        try:
            v.format(**{f: "x" for f in fields})
            return True
        except (AttributeError, KeyError, IndexError, ValueError):
            return False
    return check


def parse_settings(raw):
    """Validate the settings block and return Settings, or raise SettingsError."""
    errors = []
    if not isinstance(raw, dict):
        raise SettingsError(["settings: missing or not an object"])

    def get(path, check, expected):
        cur = raw
        for part in path.split("."):
            if not isinstance(cur, dict) or part not in cur:
                errors.append(f"{path}: missing")
                return None
            cur = cur[part]
        if not check(cur):
            errors.append(f"{path}: expected {expected}")
            return None
        return cur

    names = "a list of unique, non-empty names"
    color = "a color like #1A2B3C"
    worlds = get("worlds", lambda v: _is_names(v) and len(v) > 0, "a non-empty " + names)
    vocations = get("premium_vocations", _is_names, names)
    enemies = get("guilds.enemies.names", _is_names, names)
    friends = get("guilds.friends.names", _is_names, names)
    dan = get("guilds.dan.names", _is_names, names)

    labels, label_colors = {}, {}
    for key in LIST_KEYS:
        label = get(f"lists.{key}.label", _is_text, "text")
        c = get(f"lists.{key}.color", _is_color, color)
        if label is not None:
            labels[key] = label
            label_colors[label] = c
    if len(set(labels.values())) != len(labels):
        errors.append("lists: labels must be unique")

    show_first = get("show_first", lambda v: isinstance(v, list) and all(k in LIST_KEYS for k in v),
                     f"a list of keys from {', '.join(LIST_KEYS)}")

    links = get("page.character_links",
                lambda v: isinstance(v, list) and all(
                    isinstance(x, dict) and _is_text(x.get("label")) and _is_url("{name}")(x.get("url"))
                    for x in v),
                "a list of {label, url} with https:// urls containing {name}")
    server_types = get("page.server_types",
                       lambda v: isinstance(v, list) and len(v) > 0 and all(
                           isinstance(x, dict) and isinstance(x.get("value"), str)
                           and _PVP_VALUE.match(x["value"]) and _is_text(x.get("label"))
                           for x in v),
                       "a non-empty list of {value, label}; value lowercase letters/digits")

    death_watch = raw.get("death_watch")
    if not (isinstance(death_watch, dict) and all(isinstance(w, str) for w in death_watch.values())):
        errors.append("death_watch: expected an object of guild -> world")
    elif worlds:
        for guild, world in death_watch.items():
            if world not in worlds:
                errors.append(f"death_watch.{guild}: world '{world}' is not in worlds")

    s = dict(
        enemy_color=get("guilds.enemies.color", _is_color, color),
        enemy_low_level_color=get("guilds.enemies.low_level_color", _is_color, color),
        enemy_low_level_below=get("guilds.enemies.low_level_below", _is_int(0), "a whole number"),
        unguilded_enemy_label=get("guilds.enemies.unguilded_label", _is_text, "text"),
        friend_color=get("guilds.friends.color", _is_color, color),
        dan_color=get("guilds.dan.color", _is_color, color),
        min_level=get("min_level", _is_int(0), "a whole number"),
        gray_after_hours=get("online_too_long.after_hours", _is_int(0), "a whole number"),
        gray_color=get("online_too_long.color", _is_color, color),
        max_failed_worlds_percent=get("abort.max_failed_worlds_percent", _is_int(0, 100), "0 to 100"),
        abort_on_server_error=get("abort.on_server_error", lambda v: type(v) is bool, "true or false"),
        alert_recipients=get("telegram.alert_recipients", _is_names, names),
        login_message=get("telegram.login_message", _formats(["name"]), "text using only {name}"),
        logoff_message=get("telegram.logoff_message", _formats(["name", "duration"]),
                           "text using only {name} and {duration}"),
        world_url=get("api.world_url", _is_url("{world_name}"), "an https:// url containing {world_name}"),
        connect_timeout=get("api.connect_timeout_seconds", _is_num, "seconds"),
        read_timeout=get("api.read_timeout_seconds", _is_num, "seconds"),
        retries=get("api.retries", _is_int(0, 10), "0 to 10"),
        retry_backoff=get("api.retry_backoff_seconds", _is_num, "seconds"),
        max_parallel_requests=get("api.max_parallel_requests", _is_int(0), "a whole number (0 = one per world)"),
        online_status_key=get("storage.online_status_key", _is_text, "an S3 key"),
        last_known_data_key=get("storage.last_known_data_key", _is_text, "an S3 key"),
        page_title=get("page.title", _is_text, "text"),
        refresh_seconds=get("page.refresh_seconds", _is_int(5), "a whole number, 5 or more"),
        fresh_minutes=get("page.fresh_minutes", _is_int(1), "a whole number"),
        stale_minutes=get("page.stale_minutes", _is_int(1), "a whole number"),
        link_color=get("page.link_color", _is_color, color),
        profile_url=get("page.profile_url", _is_url("{name}"), "an https:// url containing {name}"),
    )

    if errors:
        raise SettingsError(errors)

    return Settings(
        worlds=tuple(worlds),
        premium_vocations=frozenset(vocations),
        enemies=tuple(enemies),
        enemies_set=frozenset(enemies),
        friends=tuple(friends),
        friends_set=frozenset(friends),
        dan=tuple(dan),
        dan_set=frozenset(dan),
        labels=labels,
        label_colors=label_colors,
        show_first=tuple(labels[k] for k in show_first),
        alert_recipients=tuple(s.pop("alert_recipients")),
        character_links=tuple((x["label"], x["url"]) for x in links),
        server_types=tuple((x["value"], x["label"]) for x in server_types),
        **s,
    )
