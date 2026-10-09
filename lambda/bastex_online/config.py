"""
Configuration module for Bastex Online Lambda
All environment variables and constants are defined here.
config.py
"""
import os

# ========== S3 Configuration ==========
BUCKET_NAME = os.environ.get("BUCKET_NAME", "")
OUTPUT_FILE_NAME = os.environ.get("OUTPUT_FILE_NAME", "")
CONFIG_S3_BUCKET = os.environ.get("CONFIG_S3_BUCKET", BUCKET_NAME)
CONFIG_S3_KEY = os.environ.get("CONFIG_S3_KEY", "configs/combined.json")
ONLINE_STATUS_KEY = os.environ.get("ONLINE_STATUS_KEY", "online_status_v2.txt")
LAST_KNOWN_DATA_KEY = os.environ.get("LAST_KNOWN_DATA_KEY", "last_known_worlds_data.json")

# ========== API Configuration ==========
BASE_API_URL = os.environ.get("BASE_API_URL", "https://api.tibiadata.com/v4/world/{world_name}")

# ========== World Configuration ==========
# Comma-separated list of worlds to monitor
WORLDS_RAW = os.environ.get("WORLDS",
    "Tempestera,Zunera,Eclipta,Epoca,Mystera,Firmera,Monstera,Quidera,Talera,Quintera,Wintera,Lobera,Aethera,Xymera,Havera")
WORLDS = [w.strip() for w in WORLDS_RAW.split(",") if w.strip()]

# ========== Guild Configuration ==========
SPECIAL_GUILDS_RAW = os.environ.get("SPECIAL_GUILDS",
    "Bastex,Los Dothraki,Unfallen,Bastex Rushback,Sun Tzu,Godslayers,Ragnarok,Bonstars,Acord Os,Namelesss,Reappers,No Mercy,Unlimited Bastex,Bastex Yellow,Bastex Green,Click Clack,Diamond Reappers,Mexicore,Daily Flips,Badstex,Gratitude,Bastex Inwazja")
SPECIAL_GUILDS = [g.strip() for g in SPECIAL_GUILDS_RAW.split(",") if g.strip()]

DAN_GUILDS_RAW = os.environ.get("DAN_GUILDS", "Watch The Throne,Sleeping Beauty,La Tampiquiza")
DAN_GUILDS = [g.strip() for g in DAN_GUILDS_RAW.split(",") if g.strip()]

# ========== Vocation Configuration ==========
PREMIUM_VOCATIONS_RAW = os.environ.get("PREMIUM_VOCATIONS",
    "Master Sorcerer,Elite Knight,Elder Druid,Royal Paladin,Exalted Monk")
PREMIUM_VOCATIONS = [v.strip() for v in PREMIUM_VOCATIONS_RAW.split(",") if v.strip()]

# ========== Telegram Configuration ==========
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID_ROD = os.environ.get("CHAT_ID_ROD", "")
CHAT_ID_MYKERA = os.environ.get("CHAT_ID_MYKERA", "")
CHAT_ID_CARLOS = os.environ.get("CHAT_ID_CARLOS", "")
CHAT_ID_DANNY = os.environ.get("CHAT_ID_DANNY", "")

# ========== Performance Configuration ==========
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", len(WORLDS)))
HTTP_POOL_NUM = int(os.environ.get("HTTP_POOL_NUM", "8"))
HTTP_POOL_MAXSIZE = int(os.environ.get("HTTP_POOL_MAXSIZE", "64"))
HTTP_CONNECT_TIMEOUT = float(os.environ.get("HTTP_CONNECT_TIMEOUT", "3.0"))
HTTP_READ_TIMEOUT = float(os.environ.get("HTTP_READ_TIMEOUT", "7.5"))
# Retries for transient failures (network hiccups, 502/503/504).
# Prevents a single blip from tripping the abort thresholds.
HTTP_RETRIES = int(os.environ.get("HTTP_RETRIES", "2"))
HTTP_RETRY_BACKOFF = float(os.environ.get("HTTP_RETRY_BACKOFF", "0.3"))

# ========== Filter Configuration ==========
MIN_LEVEL_FILTER = int(os.environ.get("MIN_LEVEL_FILTER", "8"))
ALERT_HOURS_THRESHOLD = int(os.environ.get("ALERT_HOURS_THRESHOLD", "3"))

# ========== Error Handling Configuration ==========
# Maximum percentage of worlds that can fail before aborting (0-100)
MAX_FAILURE_RATE = int(os.environ.get("MAX_FAILURE_RATE", "30"))
# Abort if ANY 5xx server errors occur (stricter for API downtime)
ABORT_ON_SERVER_ERROR = os.environ.get("ABORT_ON_SERVER_ERROR", "true").lower() == "true"

# ========== Color Configuration ==========
COLOR_MAP = {
    "No Freedoms": "#1D8102",
    "The Rebellion": "#1D8102",
    "Army Airdrop": "#1D8102",
    "Inferno": "#1D8102",
    "Loyalty": "#1D8102",
    "Tibashis": "#1D8102",
    "True Hope": "#1D8102",
    "Final Frontier": "#1D8102",
    "Death Line": "#1D8102",
    "Finale": "#1D8102",
    "Curse": "#1D8102",
    "Retaliation": "#1D8102",
    "Maskeikos Killers": "#1D8102",
    "Winter Brigade": "#1D8102",
    "Backlash": "#1D8102",
    "Ultimate Ice Strike": "#1D8102",
    "Juastara": "#1D8102",
    "Trolls": "#1D8102",
    "Alerts": "#FF0000",
    "Dan": "#AA336A",
    "Enemy Block": "#F3FF00",
    "Others": "#1DAAE5",
}

# ========== Category Priority Configuration ==========
PRIORITY_CATEGORIES = ["Trolls", "Dan", "Alerts"]
GREEN_CATEGORIES = [
    "No Freedoms", "Army Airdrop", "Juastara", "Ultimate Ice Strike", "Tibashis", "Inferno", "Loyalty", "Army Navy Seal", "True Hope", "The Rebellion",
    "Final Frontier", "Retaliation", "Maskeikos Killers", "Winter Brigade", "Watch Os"
]

# Pre-computed frozensets for O(1) membership checks in hot render paths
SPECIAL_GUILDS_SET = frozenset(SPECIAL_GUILDS)
DAN_GUILDS_SET = frozenset(DAN_GUILDS)
GREEN_CATEGORIES_SET = frozenset(GREEN_CATEGORIES)