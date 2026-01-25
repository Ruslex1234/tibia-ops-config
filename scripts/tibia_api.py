"""
Shared TibiaData API client with retry logic.
Used by all scripts that interact with the TibiaData API.
"""

import json
import urllib.request
import urllib.parse
import urllib.error
import gzip
import time
from io import BytesIO

from config import (
    TIBIADATA_BASE_URL,
    MAX_RETRIES,
    INITIAL_BACKOFF,
    TRANSIENT_ERROR_CODES,
    REQUEST_TIMEOUT
)


def fetch_with_retry(url, max_retries=MAX_RETRIES):
    """
    Fetch URL with exponential backoff retry logic for transient errors.

    Args:
        url: The URL to fetch
        max_retries: Maximum number of retry attempts

    Returns:
        tuple: (data, success) where data is the parsed JSON or None
    """
    request = urllib.request.Request(url)
    request.add_header('Accept-Encoding', 'gzip')
    request.add_header('User-Agent', 'TibiaOpsConfig/1.0')

    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                if response.info().get('Content-Encoding') == 'gzip':
                    buffer = BytesIO(response.read())
                    with gzip.open(buffer, 'rb') as f:
                        data = json.loads(f.read().decode('utf-8'))
                else:
                    data = json.loads(response.read().decode('utf-8'))
                return data, True

        except urllib.error.HTTPError as e:
            if e.code in TRANSIENT_ERROR_CODES:
                if attempt < max_retries - 1:
                    backoff = INITIAL_BACKOFF * (2 ** attempt)
                    print(f"  Warning: HTTP {e.code} error (attempt {attempt + 1}/{max_retries}). Retrying in {backoff}s...")
                    time.sleep(backoff)
                    continue
                else:
                    print(f"  Error: HTTP {e.code} error persisted after {max_retries} attempts. Skipping.")
                    return None, False
            else:
                print(f"  Error: HTTP {e.code} error (non-retryable). Skipping.")
                return None, False

        except urllib.error.URLError as e:
            if attempt < max_retries - 1:
                backoff = INITIAL_BACKOFF * (2 ** attempt)
                print(f"  Warning: Network error: {e.reason} (attempt {attempt + 1}/{max_retries}). Retrying in {backoff}s...")
                time.sleep(backoff)
                continue
            else:
                print(f"  Error: Network error persisted after {max_retries} attempts: {e.reason}")
                return None, False

        except Exception as e:
            print(f"  Error: Unexpected error: {e}")
            return None, False

    return None, False


def fetch_character(character_name):
    """
    Fetch character data from TibiaData API.

    Args:
        character_name: The character name to look up

    Returns:
        dict or None: Character data dict, or None if fetch failed
    """
    encoded_name = urllib.parse.quote(character_name)
    url = f"{TIBIADATA_BASE_URL}/character/{encoded_name}"
    data, success = fetch_with_retry(url)

    if success and data:
        return data.get('character', {})
    return None


def fetch_guild(guild_name):
    """
    Fetch guild data from TibiaData API.

    Args:
        guild_name: The guild name to look up

    Returns:
        dict or None: Guild data dict, or None if fetch failed
    """
    encoded_name = urllib.parse.quote(guild_name)
    url = f"{TIBIADATA_BASE_URL}/guild/{encoded_name}"
    data, success = fetch_with_retry(url)

    if success and data:
        return data.get('guild', {})
    return None


def fetch_world_guilds(world):
    """
    Fetch list of active guilds for a world.

    Args:
        world: The world name to look up

    Returns:
        list or None: List of guild dicts, or None if fetch failed
    """
    url = f"{TIBIADATA_BASE_URL}/guilds/{world}"
    data, success = fetch_with_retry(url)

    if success and data:
        return data.get('guilds', {}).get('active', [])
    return None


def get_online_guild_members(guild_name):
    """
    Get list of online member names from a guild.

    Args:
        guild_name: The guild name to check

    Returns:
        list: List of online member names (empty if none or fetch failed)
    """
    guild_data = fetch_guild(guild_name)
    if guild_data is None:
        return []

    members = guild_data.get('members', [])
    return [m.get('name') for m in members if m.get('status') == 'online']


def get_character_deaths(character_name):
    """
    Get death list for a character.

    Args:
        character_name: The character name to look up

    Returns:
        list: List of death records (empty if none or fetch failed)
    """
    char_data = fetch_character(character_name)
    if char_data is None:
        return []
    return char_data.get('deaths', [])


def get_character_info(character_name):
    """
    Get basic character info (name, world, guild).

    Args:
        character_name: The character name to look up

    Returns:
        tuple: (correct_name, world, guild_name) or (None, None, None) if failed
    """
    char_data = fetch_character(character_name)
    if char_data is None:
        return None, None, None

    char_info = char_data.get('character', {})
    correct_name = char_info.get('name')
    world = char_info.get('world', '')
    guild = char_info.get('guild', {})
    guild_name = guild.get('name', '') if guild else ''

    return correct_name, world, guild_name
