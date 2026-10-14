#!/usr/bin/env python3
"""
Remove characters that no longer exist from trolls.json.

Safety rules (this script deletes data, so it errs on the side of keeping):
- A name is only removed when TibiaData says the character does not exist,
  and says so again on a second lookup later in the same run.
- API errors (502s, timeouts, rate limits) never remove anything.
- Requests are paced, and names that errored get retried in later passes
  after a cooldown, because TibiaData answers bursts with 502s.
- If too many names look missing at once, assume the API is broken and
  abort without touching the file.

While it is at it, the script also:
- Replaces renamed characters with their current name (TibiaData resolves
  former names to the live character).
- Fixes capitalization to match Tibia.
- Drops case-insensitive duplicates.
"""

import json
import os
import sys
import time

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import TROLLS_FILE  # noqa: E402
from tibia_api import lookup_character  # noqa: E402

# Abort if more than this share of the list looks missing in one run.
MAX_REMOVAL_RATIO = 0.25

# TibiaData scrapes tibia.com per request and returns 502s when hit in a
# burst. This job runs once a day, so trade speed for fewer errors.
REQUEST_DELAY = 2  # seconds between lookups
RETRY_PASSES = 2  # extra passes over names that errored
RETRY_COOLDOWN = 60  # seconds to wait before each retry pass


def load_trolls(filepath=TROLLS_FILE):
    """Load the trolls list. Raises on a missing or malformed file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{filepath} must contain a JSON array")
    return data


def save_trolls(trolls, filepath=TROLLS_FILE):
    """Save the trolls list in the same format check_online_enemies uses."""
    with open(filepath, 'w') as f:
        json.dump(trolls, f, indent=4)


def dedupe(names):
    """Drop case-insensitive duplicates, keeping the first occurrence."""
    seen = set()
    result = []
    for name in names:
        key = name.lower()
        if key not in seen:
            seen.add(key)
            result.append(name)
    return result


def check_names(names, lookup=lookup_character):
    """
    Look up every name.

    Returns:
        tuple: (current_names, missing, errors) where current_names maps
        each found name to its live Tibia name, missing is a list of names
        that do not exist, and errors is a list of names we could not check.
    """
    current_names = {}
    missing = []
    errors = []
    for i, name in enumerate(names):
        if i:
            time.sleep(REQUEST_DELAY)
        print(f"[{i + 1}/{len(names)}] {name}")
        status, character = lookup(name)
        if status == 'found':
            current_names[name] = character['character']['name']
        elif status == 'missing':
            missing.append(name)
        else:
            errors.append(name)
    return current_names, missing, errors


def clean(trolls, lookup=lookup_character, max_removal_ratio=MAX_REMOVAL_RATIO):
    """
    Build the cleaned trolls list.

    Returns:
        dict with keys: trolls (new list or None if aborted), removed,
        renamed (list of (old, new)), errors, duplicates, aborted (reason or None).
    """
    unique = dedupe(trolls)
    duplicates = len(trolls) - len(unique)

    current_names, missing, errors = check_names(unique, lookup)

    # Errors are usually TibiaData being overloaded, not the character.
    # Let it cool down and try those names again.
    for attempt in range(RETRY_PASSES):
        if not errors:
            break
        print(f"\n{len(errors)} lookup(s) failed. Waiting {RETRY_COOLDOWN}s, "
              f"then retry pass {attempt + 1}/{RETRY_PASSES}...")
        time.sleep(RETRY_COOLDOWN)
        found, now_missing, errors = check_names(errors, lookup)
        current_names.update(found)
        missing.extend(now_missing)

    # Second opinion: only names that are missing twice get removed.
    # Anything that flips to found or error on the recheck is kept.
    confirmed = []
    if missing:
        recheck_found, confirmed, recheck_errors = check_names(missing, lookup)
        current_names.update(recheck_found)
        errors.extend(recheck_errors)

    result = {
        'trolls': None,
        'removed': confirmed,
        'renamed': [],
        'errors': errors,
        'duplicates': duplicates,
        'aborted': None,
    }

    if unique and len(confirmed) / len(unique) > max_removal_ratio:
        result['aborted'] = (
            f"{len(confirmed)} of {len(unique)} names look missing, above the "
            f"{max_removal_ratio:.0%} safety limit. Assuming an API problem."
        )
        return result

    removed = set(confirmed)
    cleaned = []
    for name in unique:
        if name in removed:
            continue
        new_name = current_names.get(name, name)
        if new_name != name:
            result['renamed'].append((name, new_name))
        cleaned.append(new_name)

    # A rename can collide with a name already on the list.
    result['trolls'] = dedupe(cleaned)
    result['duplicates'] += len(cleaned) - len(result['trolls'])
    return result


def main():
    print("=" * 60)
    print("Trolls Cleanup - remove characters that no longer exist")
    print("=" * 60)

    trolls = load_trolls()
    print(f"Loaded {len(trolls)} entries from {TROLLS_FILE}\n")

    result = clean(trolls)

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    if result['errors']:
        print(f"Could not check (kept): {len(result['errors'])}")
        for name in result['errors']:
            print(f"  - {name}")

    if result['aborted']:
        print(f"\nABORTED: {result['aborted']}")
        print("trolls.json left unchanged.")
        sys.exit(1)

    print(f"Removed (character does not exist): {len(result['removed'])}")
    for name in result['removed']:
        print(f"  - {name}")
    print(f"Renamed / recapitalized: {len(result['renamed'])}")
    for old, new in result['renamed']:
        print(f"  - '{old}' -> '{new}'")
    print(f"Duplicates dropped: {result['duplicates']}")

    if result['trolls'] == trolls:
        print("\nNo changes to save.")
        return

    save_trolls(result['trolls'])
    print(f"\nSaved {len(result['trolls'])} entries (was {len(trolls)}).")


if __name__ == "__main__":
    main()
