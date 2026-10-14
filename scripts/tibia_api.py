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

from config import (
    TIBIADATA_BASE_URL,
    MAX_RETRIES,
    INITIAL_BACKOFF,
    TRANSIENT_ERROR_CODES,
    REQUEST_TIMEOUT
)


def fetch_with_status(url, max_retries=MAX_RETRIES):
    """
    Fetch URL with exponential backoff retry logic for transient errors.

    Args:
        url: The URL to fetch
        max_retries: Maximum number of retry attempts

    Returns:
        tuple: (data, status) where data is the parsed JSON or None, and
        status is 200 on success, the HTTP code of a non-retryable error
        (e.g. 404), or None when the outcome is unknown (transient errors
        that persisted, network failures, unexpected exceptions).
    """
    request = urllib.request.Request(url, headers={
        'Accept-Encoding': 'gzip',
        'User-Agent': 'TibiaOpsConfig/1.0',
    })

    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                raw = response.read()
                if response.info().get('Content-Encoding') == 'gzip':
                    raw = gzip.decompress(raw)
                return json.loads(raw), 200

        except urllib.error.HTTPError as e:
            if e.code not in TRANSIENT_ERROR_CODES:
                print(f"  Error: HTTP {e.code} error (non-retryable). Skipping.")
                return None, e.code
            transient_reason = f"HTTP {e.code}"

        except urllib.error.URLError as e:
            transient_reason = f"Network error: {e.reason}"

        except Exception as e:
            print(f"  Error: Unexpected error: {e}")
            return None, None

        if attempt < max_retries - 1:
            backoff = INITIAL_BACKOFF * (2 ** attempt)
            print(f"  Warning: {transient_reason} (attempt "
                  f"{attempt + 1}/{max_retries}). "
                  f"Retrying in {backoff}s...")
            time.sleep(backoff)
        else:
            print(f"  Error: {transient_reason} persisted after {max_retries} attempts. Skipping.")

    return None, None


def fetch_with_retry(url, max_retries=MAX_RETRIES):
    """
    Fetch URL with exponential backoff retry logic for transient errors.

    Args:
        url: The URL to fetch
        max_retries: Maximum number of retry attempts

    Returns:
        tuple: (data, success) where data is the parsed JSON or None
    """
    data, status = fetch_with_status(url, max_retries)
    return data, status == 200


def lookup_character(character_name):
    """
    Look up a character and tell "does not exist" apart from "API failed".

    Callers that delete data based on the answer must only act on
    'missing'; 'error' means we simply don't know this run.

    Args:
        character_name: The character name to look up

    Returns:
        tuple: (status, character_dict) where status is 'found', 'missing'
        or 'error'. character_dict is only set when status is 'found'.
    """
    encoded_name = urllib.parse.quote(character_name)
    url = f"{TIBIADATA_BASE_URL}/character/{encoded_name}"
    data, status = fetch_with_status(url)

    if status == 404:
        return 'missing', None
    if status != 200 or not isinstance(data, dict):
        return 'error', None

    # Some TibiaData versions answer 200 with an error status or an empty
    # character block instead of a 404 for unknown names.
    api_status = data.get('information', {}).get('status', {})
    if api_status.get('http_code') == 404:
        return 'missing', None

    character = data.get('character', {})
    if not character.get('character', {}).get('name'):
        return 'missing', None
    return 'found', character


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
