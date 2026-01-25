#!/usr/bin/env python3
"""
Sanity check for bastex.json and trolls.json:
- Detects duplicates (case-insensitive)
- Removes duplicate entries
- Normalizes names to proper Tibia capitalization via TibiaData API
"""

import json
import urllib.request
import urllib.parse
import urllib.error
import gzip
import time
from io import BytesIO
from collections import defaultdict

# Files to check
CONFIG_FILES = [
    '.configs/trolls.json',
    '.configs/bastex.json'
]

# Retry configuration
MAX_RETRIES = 4
INITIAL_BACKOFF = 2  # seconds
TRANSIENT_ERROR_CODES = [429, 502, 503, 504]


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
                    print(f"      Warning: HTTP {e.code} error (attempt {attempt + 1}/{max_retries}). Retrying in {backoff}s...")
                    time.sleep(backoff)
                    continue
                else:
                    print(f"      Error: HTTP {e.code} error persisted after {max_retries} attempts.")
                    return None, False
            else:
                # 404 means character doesn't exist
                if e.code == 404:
                    return None, False
                print(f"      Error: HTTP {e.code} error (non-retryable).")
                return None, False

        except urllib.error.URLError as e:
            if attempt < max_retries - 1:
                backoff = INITIAL_BACKOFF * (2 ** attempt)
                print(f"      Warning: Network error: {e.reason} (attempt {attempt + 1}/{max_retries}). Retrying in {backoff}s...")
                time.sleep(backoff)
                continue
            else:
                print(f"      Error: Network error persisted after {max_retries} attempts: {e.reason}")
                return None, False

        except Exception as e:
            print(f"      Error: Unexpected error: {e}")
            return None, False

    return None, False


def get_correct_character_name(name):
    """
    Fetch the correct capitalization of a character name from TibiaData API.
    Returns the properly capitalized name, or None if character doesn't exist.
    """
    encoded_name = urllib.parse.quote(name)
    url = f"https://api.tibiadata.com/v4/character/{encoded_name}"
    data, success = fetch_with_retry(url)

    if success and data:
        character = data.get('character', {})
        char_info = character.get('character', {})
        correct_name = char_info.get('name', '')
        if correct_name:
            return correct_name

    return None


def load_json_file(filepath):
    """Load a JSON file and return its contents."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"  ERROR: File not found: {filepath}")
        return None
    except json.JSONDecodeError as e:
        print(f"  ERROR: Invalid JSON in {filepath}: {e}")
        return None


def save_json_file(filepath, data):
    """Save data to a JSON file."""
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        print(f"  ERROR: Failed to save {filepath}: {e}")
        return False


def find_duplicates(names):
    """
    Find duplicates in a list (case-insensitive).
    Returns a dict mapping lowercase name -> list of actual names found.
    """
    name_map = defaultdict(list)
    for name in names:
        name_map[name.lower()].append(name)

    # Filter to only those with duplicates
    duplicates = {k: v for k, v in name_map.items() if len(v) > 1}
    return duplicates


def deduplicate_and_normalize(names, file_label):
    """
    Remove duplicates and normalize names to proper Tibia capitalization.
    Returns the cleaned list and stats.
    """
    print(f"\n  Analyzing {len(names)} entries...")

    # Track statistics
    stats = {
        'original_count': len(names),
        'duplicates_found': [],
        'names_normalized': [],
        'names_not_found': [],
        'final_count': 0
    }

    # Step 1: Find duplicates (case-insensitive)
    duplicates = find_duplicates(names)

    if duplicates:
        print(f"\n  [DUPLICATES FOUND] {len(duplicates)} case-insensitive duplicate(s) detected:")
        for lowercase_name, variants in duplicates.items():
            print(f"    - '{lowercase_name}' appears {len(variants)} times as: {variants}")
            stats['duplicates_found'].append({
                'name': lowercase_name,
                'variants': variants,
                'count': len(variants)
            })
    else:
        print(f"\n  [OK] No duplicates found.")

    # Step 2: Build unique list (case-insensitive), keeping first occurrence
    seen_lowercase = set()
    unique_names = []

    for name in names:
        if name.lower() not in seen_lowercase:
            seen_lowercase.add(name.lower())
            unique_names.append(name)

    print(f"\n  After deduplication: {len(unique_names)} unique entries (removed {len(names) - len(unique_names)} duplicates)")

    # Step 3: Normalize names via TibiaData API
    print(f"\n  [NORMALIZING] Checking proper capitalization via TibiaData API...")
    normalized_names = []

    for i, name in enumerate(unique_names):
        if (i + 1) % 50 == 0:
            print(f"    Progress: {i + 1}/{len(unique_names)} names checked...")

        correct_name = get_correct_character_name(name)

        if correct_name:
            if correct_name != name:
                print(f"    [NORMALIZED] '{name}' -> '{correct_name}'")
                stats['names_normalized'].append({
                    'old': name,
                    'new': correct_name
                })
            normalized_names.append(correct_name)
        else:
            # Character doesn't exist or API error - keep original
            print(f"    [NOT FOUND] '{name}' - character may not exist, keeping original")
            stats['names_not_found'].append(name)
            normalized_names.append(name)

        # Small delay to avoid rate limiting
        time.sleep(0.1)

    stats['final_count'] = len(normalized_names)

    return normalized_names, stats


def print_summary(file_label, stats):
    """Print a summary of the sanity check results."""
    print(f"\n  {'=' * 50}")
    print(f"  SUMMARY FOR {file_label}")
    print(f"  {'=' * 50}")
    print(f"  Original entries:     {stats['original_count']}")
    print(f"  Duplicates removed:   {stats['original_count'] - stats['final_count'] + len(stats['names_normalized'])}")
    print(f"  Names normalized:     {len(stats['names_normalized'])}")
    print(f"  Names not found:      {len(stats['names_not_found'])}")
    print(f"  Final entries:        {stats['final_count']}")

    if stats['duplicates_found']:
        print(f"\n  Duplicate details:")
        for dup in stats['duplicates_found']:
            print(f"    - '{dup['name']}': {dup['variants']}")

    if stats['names_normalized']:
        print(f"\n  Normalization details:")
        for norm in stats['names_normalized']:
            print(f"    - '{norm['old']}' -> '{norm['new']}'")

    if stats['names_not_found']:
        print(f"\n  Names not found on Tibia (may be deleted characters):")
        for name in stats['names_not_found']:
            print(f"    - '{name}'")


def main():
    """Main function to run sanity checks on all config files."""
    print("=" * 60)
    print("SANITY CHECK - Duplicate Detection & Name Normalization")
    print("=" * 60)

    total_changes = 0

    for filepath in CONFIG_FILES:
        file_label = filepath.split('/')[-1]
        print(f"\n{'#' * 60}")
        print(f"# Processing: {file_label}")
        print(f"{'#' * 60}")

        # Load the file
        names = load_json_file(filepath)
        if names is None:
            print(f"  Skipping {file_label} due to load error.")
            continue

        if not isinstance(names, list):
            print(f"  ERROR: {file_label} is not a JSON array. Skipping.")
            continue

        # Deduplicate and normalize
        cleaned_names, stats = deduplicate_and_normalize(names, file_label)

        # Print summary
        print_summary(file_label, stats)

        # Check if changes were made
        changes_made = (
            len(stats['duplicates_found']) > 0 or
            len(stats['names_normalized']) > 0
        )

        if changes_made:
            print(f"\n  [SAVING] Writing cleaned list to {filepath}...")
            if save_json_file(filepath, cleaned_names):
                print(f"  [SUCCESS] {file_label} has been updated.")
                total_changes += 1
            else:
                print(f"  [FAILED] Could not save {file_label}.")
        else:
            print(f"\n  [NO CHANGES] {file_label} is already clean.")

    # Final summary
    print(f"\n{'=' * 60}")
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"Files processed: {len(CONFIG_FILES)}")
    print(f"Files modified:  {total_changes}")
    print("\nSanity check complete!")


if __name__ == "__main__":
    main()
