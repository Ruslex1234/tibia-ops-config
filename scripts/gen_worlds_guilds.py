#!/usr/bin/env python3
"""
Generate world guilds data by fetching guild member lists from TibiaData API.
Processes all configured worlds and saves the data to world_guilds_data.json.

Features:
- Preserves old data if API fetches fail
- Exponential backoff retry logic for transient errors
- Continues processing even if individual requests fail
"""

import json
import sys
import os

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import WORLDS, WORLD_GUILDS_FILE
from tibia_api import fetch_world_guilds, fetch_guild


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

        # Start with old data for this world, then update what we can fetch
        old_world_data = existing_data.get(world, {})
        worlds_data[world] = old_world_data.copy()

        successful_worlds += 1
        print(f"  Found {len(guilds)} guilds")

        for guild in guilds:
            guild_name = guild.get('name')
            if not guild_name:
                continue

            print(f"  - {guild_name}...", end=" ")
            guild_data = fetch_guild(guild_name)

            if guild_data and 'members' in guild_data and guild_data['members']:
                member_names = [m['name'] for m in guild_data.get('members', [])]
                worlds_data[world][guild_name] = member_names
                print(f"OK ({len(member_names)} members)")
                total_guilds_processed += 1
            else:
                # Keep old data if we had it
                if guild_name in old_world_data:
                    print(f"Failed - keeping old data ({len(old_world_data[guild_name])} members)")
                else:
                    print("Failed or no members")
                total_guilds_failed += 1

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
