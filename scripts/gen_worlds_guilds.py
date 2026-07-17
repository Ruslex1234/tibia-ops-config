#!/usr/bin/env python3
"""
Generate world guilds data by fetching guild member lists from TibiaData API.
Processes all configured worlds and saves the data to world_guilds_data.json.

Features:
- Preserves old data if API fetches fail
- Removes guilds that no longer exist in the world's active guild list
- Exponential backoff retry logic for transient errors
- Continues processing even if individual requests fail
"""

import json
import sys
import os

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import WORLDS, WORLD_GUILDS_FILE  # noqa: E402
from tibia_api import fetch_world_guilds, fetch_guild  # noqa: E402


def load_existing_data():
    """Load existing world guilds data from file."""
    try:
        with open(WORLD_GUILDS_FILE, 'r') as f:
            data = json.load(f)
        print(f"Loaded existing data with {len(data)} worlds")
        return data
    except FileNotFoundError:
        print("No existing data file found - starting fresh")
        return {}
    except Exception as e:
        print(f"Warning: Could not load existing data: {e}")
        return {}


def save_data(data):
    """Save world guilds data to file."""
    try:
        with open(WORLD_GUILDS_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"\nSuccessfully wrote data to {WORLD_GUILDS_FILE}")
        return True
    except Exception as e:
        print(f"\nFailed to write file: {e}")
        return False


def build_world_data(guilds, old_world_data):
    """
    Build the guild -> members mapping for a world from its current guild list.

    Only guilds present in the current API guild list are included, so guilds
    that were disbanded since the last run are dropped. If fetching an
    individual guild's member list fails, the old data for that guild is kept
    (the guild still exists, we just couldn't refresh it).

    Args:
        guilds: List of guild dicts from fetch_world_guilds
        old_world_data: Previous guild -> members mapping for this world

    Returns:
        tuple: (world_data, processed_count, failed_count)
    """
    world_data = {}
    processed = 0
    failed = 0

    for guild in guilds:
        guild_name = guild.get('name')
        if not guild_name:
            continue

        print(f"  - {guild_name}...", end=" ")
        guild_data = fetch_guild(guild_name)

        members = guild_data.get('members') if guild_data else None
        if members:
            member_names = [m['name'] for m in members]
            world_data[guild_name] = member_names
            print(f"OK ({len(member_names)} members)")
            processed += 1
        else:
            # Keep old data if we had it
            if guild_name in old_world_data:
                world_data[guild_name] = old_world_data[guild_name]
                print(f"Failed - keeping old data ({len(old_world_data[guild_name])} members)")
            else:
                print("Failed or no members")
            failed += 1

    return world_data, processed, failed


def main():
    """Main handler that fetches guild data for all worlds."""
    print("=" * 60)
    print("Generating World Guilds Data")
    print("=" * 60)
    print("\nStarting data fetch...")

    # Load existing data to preserve it if fetches fail
    existing_data = load_existing_data()
    worlds_data = existing_data.copy()

    # Statistics
    total_worlds = len(WORLDS)
    successful_worlds = 0
    failed_worlds = 0
    total_guilds_processed = 0
    total_guilds_failed = 0

    for world in WORLDS:
        print(f"\n[{world}]")

        guilds = fetch_world_guilds(world)
        if guilds is None:
            print(f"  Failed to fetch guild list for {world}. Keeping old data.")
            failed_worlds += 1
            continue

        # Rebuild this world's data from the current guild list so that
        # guilds that no longer exist are removed
        old_world_data = existing_data.get(world, {})

        successful_worlds += 1
        print(f"  Found {len(guilds)} guilds")

        world_data, processed, failed = build_world_data(guilds, old_world_data)
        worlds_data[world] = world_data
        total_guilds_processed += processed
        total_guilds_failed += failed

        removed_guilds = sorted(set(old_world_data) - set(world_data))
        if removed_guilds:
            print(f"  Removed {len(removed_guilds)} guild(s) no longer active: "
                  f"{', '.join(removed_guilds)}")

    # Drop worlds that are no longer configured so their data doesn't linger
    stale_worlds = [w for w in worlds_data if w not in WORLDS]
    for world in stale_worlds:
        del worlds_data[world]
        print(f"\nRemoved unconfigured world from data: {world}")

    # Summary
    print(f"\n{'=' * 60}")
    print("Summary")
    print("=" * 60)
    print(f"Worlds: {successful_worlds}/{total_worlds} successful, {failed_worlds} failed")
    print(f"Guilds: {total_guilds_processed} processed, {total_guilds_failed} failed/skipped")

    # Save data
    if not save_data(worlds_data):
        raise RuntimeError("Failed to save data file")

    # Only fail the entire job if we got zero successful worlds
    if successful_worlds == 0:
        raise RuntimeError("Failed to fetch data for all worlds. Check API availability.")

    print(f"\nJob completed with {successful_worlds}/{total_worlds} worlds processed")


if __name__ == "__main__":
    main()
