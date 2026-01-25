"""
Centralized configuration for Tibia Ops Config.
All hardcoded values are maintained here for easy updates.
"""

# =============================================================================
# API Configuration
# =============================================================================
TIBIADATA_BASE_URL = "https://api.tibiadata.com/v4"

# Retry configuration for API calls
MAX_RETRIES = 4
INITIAL_BACKOFF = 2  # seconds
TRANSIENT_ERROR_CODES = [429, 502, 503, 504]  # Rate limit, Bad Gateway, Service Unavailable, Gateway Timeout
REQUEST_TIMEOUT = 30  # seconds

# =============================================================================
# World Configuration
# =============================================================================
# All Tibia worlds we monitor for guild data
WORLDS = [
    'Quidera', 'Firmera', 'Aethera', 'Monstera', 'Talera',
    'Lobera', 'Quintera', 'Wintera', 'Eclipta', 'Epoca',
    'Zunera', 'Mystera', 'Xymera', 'Tempestera'
]

# =============================================================================
# Enemy Guild Configuration
# =============================================================================
# Guild name -> World mapping for enemy tracking
# These guilds' online members will have their death lists checked
ENEMY_GUILDS = {
    "Bastex": "Firmera",
    "Bastex Ruzh": "Tempestera"
}

# =============================================================================
# File Paths (relative to repository root)
# =============================================================================
CONFIGS_DIR = '.configs'
TROLLS_FILE = f'{CONFIGS_DIR}/trolls.json'
BASTEX_FILE = f'{CONFIGS_DIR}/bastex.json'
BLOCK_FILE = f'{CONFIGS_DIR}/block.json'
ALERTS_FILE = f'{CONFIGS_DIR}/alerts.json'
WORLD_GUILDS_FILE = f'{CONFIGS_DIR}/world_guilds_data.json'
