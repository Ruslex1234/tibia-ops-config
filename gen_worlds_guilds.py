import json
import urllib.request
import urllib.parse
import urllib.error
import gzip
import time
from io import BytesIO

# Worlds to fetch guilds from
WORLDS = ['Quidera', 'Firmera', 'Aethera', 'Monstera', 'Talera', 'Lobera', 'Quintera', 'Wintera', 'Eclipta', 'Epoca', 'Zunera', 'Mystera', 'Xymera', 'Tempestera']

# Retry configuration
MAX_RETRIES = 4
INITIAL_BACKOFF = 2  # seconds
TRANSIENT_ERROR_CODES = [429, 502, 503, 504]  # Rate limit, Bad Gateway, Service Unavailable, Gateway Timeout

def fetch_with_retry(url, max_retries=MAX_RETRIES):
    """
    Fetch URL with exponential backoff retry logic for transient errors.
    Returns tuple: (data, success)
    """
    request = urllib.request.Request(url)
    request.add_header('Accept-Encoding', 'gzip')

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
                    print(f"  ⚠ HTTP {e.code} error (attempt {attempt + 1}/{max_retries}). Retrying in {backoff}s...")
                    time.sleep(backoff)
                    continue
                else:
                    print(f"  ✗ HTTP {e.code} error persisted after {max_retries} attempts. Skipping.")
                    return None, False
            else:
                print(f"  ✗ HTTP {e.code} error (non-retryable). Skipping.")
                return None, False

        except urllib.error.URLError as e:
            if attempt < max_retries - 1:
                backoff = INITIAL_BACKOFF * (2 ** attempt)
                print(f"  ⚠ Network error: {e.reason} (attempt {attempt + 1}/{max_retries}). Retrying in {backoff}s...")
                time.sleep(backoff)
                continue
            else:
                print(f"  ✗ Network error persisted after {max_retries} attempts: {e.reason}")
                return None, False

        except Exception as e:
            print(f"  ✗ Unexpected error: {e}")
            return None, False

    return None, False

def fetch_guilds_for_world(world):
    """Fetch all guilds for a given world with retry logic."""
    url = f"https://api.tibiadata.com/v4/guilds/{world}"
    data, success = fetch_with_retry(url)

    if success and data:
        return data.get('guilds', {}).get('active', [])
    return None

def fetch_guild_data(guild_name):
    """Fetch detailed data for a specific guild with retry logic."""
    encoded_guild_name = urllib.parse.quote(guild_name)
    url = f"https://api.tibiadata.com/v4/guild/{encoded_guild_name}"
    data, success = fetch_with_retry(url)

    if success and data:
        return data.get('guild', {})
    return None

def lambda_handler(event, context):
    """
    Main handler that fetches guild data for all worlds.
    Continues processing even if individual requests fail.
    """
    print("Starting data fetch...")
    worlds_data = {}
    total_worlds = len(WORLDS)
    successful_worlds = 0
    failed_worlds = 0
    total_guilds_processed = 0
    total_guilds_failed = 0

    for world in WORLDS:
        print(f"\n[{world}]")
        worlds_data[world] = {}

        guilds = fetch_guilds_for_world(world)
        if guilds is None:
            print(f"  ✗ Failed to fetch guild list for {world}. Skipping world.")
            failed_worlds += 1
            continue

        successful_worlds += 1
        print(f"  Found {len(guilds)} guilds")

        for guild in guilds:
            guild_name = guild.get('name')
            if not guild_name:
                continue

            print(f"  - {guild_name}...", end=" ")
            guild_data = fetch_guild_data(guild_name)

            if guild_data and 'members' in guild_data and guild_data['members']:
                worlds_data[world][guild_name] = [member['name'] for member in guild_data.get('members', [])]
                print(f"✓ ({len(guild_data['members'])} members)")
                total_guilds_processed += 1
            else:
                print("✗ Failed or no members")
                total_guilds_failed += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Worlds: {successful_worlds}/{total_worlds} successful, {failed_worlds} failed")
    print(f"  Guilds: {total_guilds_processed} processed, {total_guilds_failed} failed/skipped")
    print(f"{'='*60}")

    # Convert the data structure to JSON
    json_data = json.dumps(worlds_data, indent=4)

    # Write the JSON to a local file
    try:
        with open('.configs/world_guilds_data.json', 'w') as f:
            f.write(json_data)
        print("\n✓ Successfully wrote data to .configs/world_guilds_data.json")
    except Exception as e:
        print(f"\n✗ Failed to write file: {e}")
        raise

    # Only fail the entire job if we got zero successful worlds
    if successful_worlds == 0:
        raise RuntimeError("Failed to fetch data for all worlds. Check API availability.")

    print(f"\n✓ Job completed with {successful_worlds}/{total_worlds} worlds processed")

lambda_handler(None, None)
