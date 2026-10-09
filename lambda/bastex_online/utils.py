"""
Utility functions for S3, Telegram, HTTP operations, and time formatting
utils.py
"""
import json
import gzip
import hashlib
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError
import urllib3
from urllib3.util.retry import Retry

import config
from config import BUCKET_NAME, CONFIG_S3_BUCKET, CONFIG_S3_KEY, TELEGRAM_BOT_TOKEN

# Compact JSON: no whitespace, smaller S3 payloads
_JSON_COMPACT = {"separators": (",", ":")}


def utcnow_ts() -> int:
    """Current UTC epoch seconds (timezone-aware; utcnow() is deprecated)."""
    return int(datetime.now(timezone.utc).timestamp())


# ========== Custom Exceptions ==========
class APIError(Exception):
    """Raised when API returns an error status code"""
    def __init__(self, status_code, url, message="API request failed"):
        self.status_code = status_code
        self.url = url
        self.message = f"{message}: {status_code} for {url}"
        super().__init__(self.message)


# ========== HTTP Client ==========
_http = None


def http_pool(size):
    """Shared PoolManager with at least `size` connections per host.
    Rebuilt only when the worker count grows (e.g. worlds added in settings)."""
    global _http
    if _http is None or _http.connection_pool_kw.get("maxsize", 0) < size:
        _http = urllib3.PoolManager(num_pools=4, maxsize=size, headers={"Accept-Encoding": "gzip"})
    return _http


def _timeout():
    s = config.settings
    return urllib3.Timeout(connect=s.connect_timeout, read=s.read_timeout)


def _retry():
    """Retry transient failures (connection resets, 502/503/504) so a single
    blip doesn't mark a world as failed and trip the abort thresholds."""
    s = config.settings
    return Retry(
        total=s.retries,
        connect=s.retries,
        read=s.retries,
        backoff_factor=s.retry_backoff,
        status_forcelist=(502, 503, 504),
        raise_on_status=False,
        respect_retry_after_header=True,
    )

# ========== AWS Clients (initialized once) ==========
S3_CLIENT = boto3.client("s3")
S3_RESOURCE = boto3.resource("s3")


# ========== HTTP Functions ==========
def http_get_json(url: str):
    """Fetch JSON data from URL with gzip support and transient-error retries"""
    r = http_pool(1).request(
        "GET",
        url,
        timeout=_timeout(),
        retries=_retry(),
        preload_content=True,
        decode_content=True,
    )

    # Check for error status codes
    if r.status >= 500:
        raise APIError(r.status, url, "Server error")
    elif r.status >= 400:
        raise APIError(r.status, url, "Client error")
    elif r.status != 200:
        raise APIError(r.status, url, "Unexpected status")

    return json.loads(r.data.decode("utf-8"))


# ========== S3 Functions ==========
def load_combined_config():
    """Load combined.json from S3 (settings, alerts, bastex, block, trolls,
    world_guilds_data). Raises on failure: running without config would
    render a page with every list empty."""
    obj = S3_CLIENT.get_object(Bucket=CONFIG_S3_BUCKET, Key=CONFIG_S3_KEY)
    cfg = json.loads(obj["Body"].read())
    if not isinstance(cfg, dict):
        raise ValueError("combined config is not a JSON object")
    print("Loaded combined config")
    return cfg


# Reserved key inside the online-status file. Maps world -> {name: True}
# for players who qualified for a login alert, so logoff alerts can fire
# even though vocation is unknowable once the player is offline.
ALERTED_REGISTRY_KEY = "_alerted"


def load_online_status():
    """Load online status tracking data from S3"""
    try:
        response = S3_CLIENT.get_object(Bucket=BUCKET_NAME, Key=config.settings.online_status_key)
        online_status = json.loads(response['Body'].read())
        # Pull the alert registry aside so epoch normalization skips it
        alerted = online_status.pop(ALERTED_REGISTRY_KEY, {})
        # Normalize to epoch ints
        for w, m in list(online_status.items()):
            if isinstance(m, dict):
                online_status[w] = {n: _to_epoch(t) for n, t in m.items()}
        online_status[ALERTED_REGISTRY_KEY] = alerted if isinstance(alerted, dict) else {}
        return online_status
    except ClientError as e:
        if e.response.get('Error', {}).get('Code') in ('NoSuchKey', '404'):
            return {}
        else:
            raise
    except Exception:
        return {}


def save_online_status(online_status):
    """Save online status tracking data to S3"""
    S3_CLIENT.put_object(
        Bucket=BUCKET_NAME,
        Key=config.settings.online_status_key,
        Body=json.dumps(online_status, **_JSON_COMPACT),
        ContentType='application/json'
    )


def load_last_known_worlds_data():
    """Load last known good worlds data from S3 (for partial failure recovery).
    Handles both gzipped (new) and plain JSON (legacy) payloads."""
    try:
        response = S3_CLIENT.get_object(Bucket=BUCKET_NAME, Key=config.settings.last_known_data_key)
        raw = response['Body'].read()
        if raw[:2] == b'\x1f\x8b':  # gzip magic bytes
            raw = gzip.decompress(raw)
        worlds_data = json.loads(raw)
        print("Loaded last known worlds data")
        return worlds_data
    except ClientError as e:
        if e.response.get('Error', {}).get('Code') in ('NoSuchKey', '404'):
            print("No previous worlds data found - first run or cache missing")
            return {}
        else:
            raise
    except Exception as e:
        print(f"Failed to load last known worlds data: {e}")
        return {}


def save_last_known_worlds_data(worlds_data):
    """Save worlds data to S3 as gzipped backup for partial failure recovery.
    Gzipping cuts the PUT payload ~85-90% on every run."""
    try:
        body = gzip.compress(
            json.dumps(worlds_data, **_JSON_COMPACT).encode("utf-8"),
            mtime=0
        )
        S3_CLIENT.put_object(
            Bucket=BUCKET_NAME,
            Key=config.settings.last_known_data_key,
            Body=body,
            ContentType='application/json',
            ContentEncoding='gzip'
        )
        print(f"Saved last known worlds data ({len(body)} bytes gz)")
    except Exception as e:
        print(f"Warning: Failed to save last known worlds data: {e}")


def put_html_if_changed(bucket, key, html_str):
    """Upload HTML to S3 only if content has changed (using MD5 comparison).

    IMPORTANT: mtime=0 makes the gzip output deterministic. Without it, gzip
    embeds the current timestamp in the header, the MD5 changes every run even
    for identical HTML, and the skip-upload optimization never fires.
    """
    gz = gzip.compress(html_str.encode("utf-8"), mtime=0)
    md5hex = hashlib.md5(gz, usedforsecurity=False).hexdigest()

    try:
        head = S3_CLIENT.head_object(Bucket=bucket, Key=key)
        etag = head.get("ETag", "").strip('"')
        if "-" not in etag and etag == md5hex:
            print("HTML unchanged; skip upload.")
            return False
    except ClientError as e:
        if e.response.get('Error', {}).get('Code') not in ('404', 'NotFound', 'NoSuchKey'):
            raise

    obj = S3_RESOURCE.Object(bucket, key)
    obj.put(Body=gz, ACL="public-read", ContentType="text/html", ContentEncoding="gzip")
    print("HTML uploaded.")
    return True


# ========== Telegram Functions ==========
def _escape_markdown(text: str) -> str:
    """Escape characters that break Telegram Markdown formatting in names"""
    for ch in ('_', '*', '`', '['):
        text = text.replace(ch, '\\' + ch)
    return text


def send_alert(chat_id, message, bot_token=TELEGRAM_BOT_TOKEN):
    """Send a Telegram alert message via POST (message no longer in the URL,
    so it stays out of proxy/CloudWatch access logs and avoids URL length limits)."""
    if not bot_token or not chat_id:
        print("Skipped Telegram alert (no token or chat_id)")
        return {'statusCode': 200, 'body': json.dumps('Skipped (no token).')}

    send_url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    payload = json.dumps({
        'chat_id': chat_id,
        'parse_mode': 'Markdown',
        'text': message,
    }).encode('utf-8')

    try:
        r = http_pool(1).request(
            "POST", send_url,
            body=payload,
            headers={'Content-Type': 'application/json'},
            timeout=_timeout(),
            preload_content=True, decode_content=True
        )
        print(f"Telegram message sent: {r.status}")
        return {'statusCode': 200, 'body': json.dumps('Message sent!')}
    except Exception as e:
        print(f"Failed to send message: {e}")
        return {'statusCode': 400, 'body': json.dumps('Failed to send message')}


# ========== Time Utility Functions ==========
def _to_epoch(v):
    """Convert datetime string or int to epoch seconds"""
    if isinstance(v, int):
        return v
    try:
        return int(datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
                   .replace(tzinfo=timezone.utc).timestamp())
    except Exception:
        return utcnow_ts()


def format_timedelta_from_epoch(start_ts: int, now_ts: int):
    """Format time difference between two epoch timestamps as 'Xh Ym' or 'Ym'"""
    total = max(0, now_ts - start_ts)
    hours, rem = divmod(total, 3600)
    minutes = rem // 60
    return f"{hours}h{minutes}m" if hours else f"{minutes}m"


# ========== String Normalization ==========
def normalize_key(s: str) -> str:
    """Normalize string for comparison (lowercase, alphanumeric only, remove 'pvp' suffix)"""
    if not s:
        return ""
    s = s.lower()
    s = "".join(ch for ch in s if ch.isalnum())
    if s.endswith("pvp"):
        s = s[:-3]
    return s


def extract_world_meta(world_obj: dict):
    """Extract normalized PvP type and location from world data"""
    info = world_obj.get('world_information') or world_obj.get('information') or {}
    pvp_raw = info.get('pvp_type') or world_obj.get('pvp_type') or ""
    loc_raw = info.get('location') or info.get('server_location') or world_obj.get('location') or ""
    return normalize_key(pvp_raw), normalize_key(loc_raw)