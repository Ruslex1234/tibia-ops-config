"""
Centralized configuration for Tibia Ops Config.
All hardcoded values are maintained here for easy updates.
"""

import json
import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
# Worlds and enemy guilds come from .configs/settings.json, the single source
# of truth shared with the bastex_online Lambda. Edit that file, not this one.
with open(os.path.join(_REPO_ROOT, '.configs', 'settings.json'), encoding='utf-8') as _f:
    _SETTINGS = json.load(_f)

# All Tibia worlds we monitor
WORLDS = _SETTINGS['worlds']

# =============================================================================
# Enemy Guild Configuration
# =============================================================================
# Guild name -> World mapping for enemy tracking
# These guilds' online members will have their death lists checked
ENEMY_GUILDS = _SETTINGS['death_watch']

# =============================================================================
# File Paths (relative to repository root)
# =============================================================================
CONFIGS_DIR = '.configs'
TROLLS_FILE = f'{CONFIGS_DIR}/trolls.json'
BASTEX_FILE = f'{CONFIGS_DIR}/bastex.json'
BLOCK_FILE = f'{CONFIGS_DIR}/block.json'
ALERTS_FILE = f'{CONFIGS_DIR}/alerts.json'
WORLD_GUILDS_FILE = f'{CONFIGS_DIR}/world_guilds_data.json'
