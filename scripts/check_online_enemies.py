#!/usr/bin/env python3
"""
Check online enemies from configured enemy guilds.
For each online member, check their death list and add unguilded killers to trolls.json.

Features:
- Case-insensitive duplicate detection
- Automatic name normalization to proper Tibia capitalization
- Exponential backoff retry logic for API calls
"""

import json
import sys
import os

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ENEMY_GUILDS, TROLLS_FILE, BASTEX_FILE  # noqa: E402
from tibia_api import (  # noqa: E402
    get_online_guild_members,
    fetch_character,
    get_character_info
)


def extract_player_killers(deaths):
    """
    Extract player killer names from a death list.

    Args:
        deaths: List of death records from TibiaData API

    Returns:
        list: Unique player killer names
    """
    killers = set()
    for death in deaths:
        for killer in death.get('killers', []):
            if killer.get('player', False):
                name = killer.get('name', '')
                if name:
                    killers.add(name)
    return list(killers)


def load_json_list(filepath):
    """Load a JSON array from file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: {filepath} not found. Using empty list.")
        return []
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
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


def build_case_insensitive_map(names):
    """
    Build a case-insensitive lookup map.

    Returns:
        dict: lowercase_name -> (index, actual_name)
    """
    return {name.lower(): (idx, name) for idx, name in enumerate(names)}


def main():
    """Main function to check online enemies and update trolls list."""
    print("=" * 60)
    print("Checking Online Enemies - Death List Analysis")
    print("(with case-insensitive duplicate detection & normalization)")
    print("=" * 60)

    # Load existing trolls
    trolls = load_json_list(TROLLS_FILE)
    initial_count = len(trolls)

    # Load bastex list so we don't add people who are already tracked there
    bastex = load_json_list(BASTEX_FILE)
    bastex_set = {name.lower() for name in bastex}
    print(f"Loaded {len(trolls)} trolls and {len(bastex)} bastex entries")

    # Build case-insensitive lookup map for trolls
    trolls_lookup = build_case_insensitive_map(trolls)

    # Track changes
    new_trolls_added = []
    names_normalized = []
    list_modified = False

    for guild_name, world in ENEMY_GUILDS.items():
        print(f"\n[{guild_name}] ({world})")
        print("-" * 40)

        # Get online members
        online_members = get_online_guild_members(guild_name)
        if not online_members:
            print("  No online members found or failed to fetch guild data.")
            continue

        print(f"  Found {len(online_members)} online member(s)")

        for member_name in online_members:
            print(f"\n  Checking deaths for: {member_name}")

            # Fetch character data to get deaths
            char_data = fetch_character(member_name)
            if char_data is None:
                print("    Failed to fetch character data")
                continue

            deaths = char_data.get('deaths', [])
            if not deaths:
                print("    No deaths recorded")
                continue

            print(f"    Found {len(deaths)} death(s)")

            # Extract player killers from deaths
            killers = extract_player_killers(deaths)
            if not killers:
                print("    No player killers found in deaths")
                continue

            print(f"    Found {len(killers)} unique player killer(s)")

            # Check each killer
            for killer_name in killers:
                killer_lower = killer_name.lower()

                # Skip if already in bastex list (no API call needed)
                if killer_lower in bastex_set:
                    print(f"      [{killer_name}] Already in bastex list - skipping")
                    continue

                # Case-insensitive check if already in trolls list
                if killer_lower in trolls_lookup:
                    idx, existing_name = trolls_lookup[killer_lower]

                    # Check if the case matches
                    if existing_name == killer_name:
                        print(f"      [{killer_name}] Already in trolls list")
                    else:
                        # Name exists but with different case - need to normalize
                        print(f"      [{killer_name}] Found with different case: '{existing_name}'")

                        # Fetch correct name from TibiaData
                        correct_name, char_world, char_guild = get_character_info(killer_name)

                        if correct_name and correct_name != existing_name:
                            print(f"        [NORMALIZED] '{existing_name}' -> '{correct_name}'")
                            trolls[idx] = correct_name
                            trolls_lookup[killer_lower] = (idx, correct_name)
                            names_normalized.append((existing_name, correct_name))
                            list_modified = True
                        else:
                            print(f"        Keeping existing: '{existing_name}'")
                    continue

                print(f"      Checking [{killer_name}]...", end=" ")

                # Get character info to check world and guild
                correct_name, char_world, char_guild = get_character_info(killer_name)

                if correct_name is None:
                    print("Skipped (character not found)")
                    continue

                # Check if on different world
                if char_world and char_world.lower() != world.lower():
                    print(f"Skipped (different world: {char_world})")
                    continue

                # Check if has guild
                if char_guild:
                    print(f"Skipped (has guild: {char_guild})")
                    continue

                # Valid troll - add with correct name
                name_to_add = correct_name
                print(f"ADDING (unguilded on {world})")

                if correct_name != killer_name:
                    print(f"        [NORMALIZED] Using correct name: '{correct_name}'")

                trolls.append(name_to_add)
                trolls_lookup[name_to_add.lower()] = (len(trolls) - 1, name_to_add)
                new_trolls_added.append((name_to_add, world, member_name))
                list_modified = True

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Initial trolls count: {initial_count}")
    print(f"New trolls added: {len(new_trolls_added)}")
    print(f"Names normalized: {len(names_normalized)}")
    print(f"Final trolls count: {len(trolls)}")

    if new_trolls_added:
        print("\nNew entries added:")
        for name, world, killed_by in new_trolls_added:
            print(f"  - {name} ({world}) - killed {killed_by}")

    if names_normalized:
        print("\nNames normalized (case corrected):")
        for old_name, new_name in names_normalized:
            print(f"  - '{old_name}' -> '{new_name}'")

    # Save if there were any changes
    if list_modified:
        save_trolls(trolls)
    else:
        print("\nNo changes to save.")

    print("\nDone!")


if __name__ == "__main__":
    main()
