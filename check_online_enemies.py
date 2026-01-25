#!/usr/bin/env python3
"""
Check online enemies from Bastex (Tempestera) and Bastex Ruzh (Firmera) guilds.
For each online member, check their death list and add unguilded killers to trolls.json.
"""

import json
import urllib.request
import urllib.parse
import urllib.error
import gzip
import time
from io import BytesIO

# Guild configurations: guild_name -> world
ENEMY_GUILDS = {
    "Bastex": "Firmera",
    "Bastex Ruzh": "Tempestera"
}

# Retry configuration
MAX_RETRIES = 4
INITIAL_BACKOFF = 2  # seconds
TRANSIENT_ERROR_CODES = [429, 502, 503, 504]

TROLLS_FILE = '.configs/trolls.json'


def fetch_with_retry(url, max_retries=MAX_RETRIES):
    """
    Fetch URL with exponential backoff retry logic for transient errors.
    Returns tuple: (data, success)
    """
    request = urllib.request.Request(url)
    request.add_header('Accept-Encoding', 'gzip')
    request.add_header('User-Agent', 'TibiaOpsConfig/1.0')

    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
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


def fetch_guild_members(guild_name):
    """Fetch guild data and return list of members with their online status."""
    encoded_guild_name = urllib.parse.quote(guild_name)
    url = f"https://api.tibiadata.com/v4/guild/{encoded_guild_name}"
    data, success = fetch_with_retry(url)

    if success and data:
        guild_data = data.get('guild', {})
        return guild_data.get('members', [])
    return None


def fetch_character_data(character_name):
    """Fetch character data including deaths and guild info."""
    encoded_name = urllib.parse.quote(character_name)
    url = f"https://api.tibiadata.com/v4/character/{encoded_name}"
    data, success = fetch_with_retry(url)

    if success and data:
        return data.get('character', {})
    return None


def get_online_members(guild_name):
    """Get list of online member names from a guild."""
    members = fetch_guild_members(guild_name)
    if members is None:
        return []

    online_members = []
    for member in members:
        if member.get('status') == 'online':
            online_members.append(member.get('name'))

    return online_members


def extract_killers_from_deaths(deaths, target_world):
    """
    Extract player killers from death list.
    Returns list of killer names that are players (not creatures).
    """
    killers = set()

    for death in deaths:
        # Each death has a list of killers
        death_killers = death.get('killers', [])
        for killer in death_killers:
            # Check if it's a player (players have 'player' set to True)
            if killer.get('player', False):
                killer_name = killer.get('name', '')
                if killer_name:
                    killers.add(killer_name)

    return list(killers)


def is_unguilded_player_on_world(character_name, target_world):
    """
    Check if a character is on the target world and has no guild.
    Returns tuple: (is_valid_troll, character_world)
    """
    char_data = fetch_character_data(character_name)
    if char_data is None:
        return False, None

    character_info = char_data.get('character', {})
    char_world = character_info.get('world', '')
    char_guild = character_info.get('guild', {})

    # Check if character is on the target world
    if char_world.lower() != target_world.lower():
        return False, char_world

    # Check if character has no guild (guild dict is empty or name is empty)
    guild_name = char_guild.get('name', '') if char_guild else ''
    if guild_name:
        return False, char_world

    return True, char_world


def load_trolls():
    """Load existing trolls list."""
    try:
        with open(TROLLS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: {TROLLS_FILE} not found. Creating new list.")
        return []
    except Exception as e:
        print(f"Error loading trolls file: {e}")
        return []


def save_trolls(trolls):
    """Save trolls list to file."""
    try:
        with open(TROLLS_FILE, 'w') as f:
            json.dump(trolls, f, indent=4)
        print(f"Successfully saved {len(trolls)} entries to {TROLLS_FILE}")
        return True
    except Exception as e:
        print(f"Error saving trolls file: {e}")
        return False


def main():
    """Main function to check online enemies and update trolls list."""
    print("=" * 60)
    print("Checking Online Enemies - Death List Analysis")
    print("=" * 60)

    # Load existing trolls
    trolls = load_trolls()
    trolls_set = set(trolls)  # For fast lookup
    initial_count = len(trolls)

    new_trolls_added = []

    for guild_name, world in ENEMY_GUILDS.items():
        print(f"\n[{guild_name}] ({world})")
        print("-" * 40)

        # Get online members
        online_members = get_online_members(guild_name)
        if not online_members:
            print(f"  No online members found or failed to fetch guild data.")
            continue

        print(f"  Found {len(online_members)} online member(s)")

        for member_name in online_members:
            print(f"\n  Checking deaths for: {member_name}")

            # Fetch character data to get deaths
            char_data = fetch_character_data(member_name)
            if char_data is None:
                print(f"    Failed to fetch character data")
                continue

            deaths = char_data.get('deaths', [])
            if not deaths:
                print(f"    No deaths recorded")
                continue

            print(f"    Found {len(deaths)} death(s)")

            # Extract player killers from deaths
            killers = extract_killers_from_deaths(deaths, world)
            if not killers:
                print(f"    No player killers found in deaths")
                continue

            print(f"    Found {len(killers)} unique player killer(s)")

            # Check each killer
            for killer_name in killers:
                # Skip if already in trolls list
                if killer_name in trolls_set:
                    print(f"      [{killer_name}] Already in trolls list")
                    continue

                print(f"      Checking [{killer_name}]...", end=" ")

                is_troll, char_world = is_unguilded_player_on_world(killer_name, world)

                if is_troll:
                    print(f"ADDING (unguilded on {world})")
                    trolls.append(killer_name)
                    trolls_set.add(killer_name)
                    new_trolls_added.append((killer_name, world, member_name))
                elif char_world and char_world.lower() != world.lower():
                    print(f"Skipped (different world: {char_world})")
                else:
                    print(f"Skipped (has guild)")

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Initial trolls count: {initial_count}")
    print(f"New trolls added: {len(new_trolls_added)}")
    print(f"Final trolls count: {len(trolls)}")

    if new_trolls_added:
        print("\nNew entries added:")
        for name, world, killed_by in new_trolls_added:
            print(f"  - {name} ({world}) - killed {killed_by}")

    # Save if there are new entries
    if new_trolls_added:
        save_trolls(trolls)
    else:
        print("\nNo changes to save.")

    print("\nDone!")


if __name__ == "__main__":
    main()
