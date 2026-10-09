"""
AWS Lambda handler for Bastex Online Tracker
Main entry point that orchestrates the data fetching, processing, and HTML generation.
lambda_function.py
"""
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

from config import (
    BUCKET_NAME, OUTPUT_FILE_NAME, PREMIUM_VOCATIONS, CHAT_ID_MYKERA,
    WORLDS, MAX_FAILURE_RATE, ABORT_ON_SERVER_ERROR
)
from utils import (
    load_combined_config, put_html_if_changed,
    load_last_known_worlds_data, save_last_known_worlds_data,
    utcnow_ts
)
from data_processing import (
    fetch_all_worlds, build_member_index, update_player_online_status
)
from html_builder import build_html


def lambda_handler(event, context):
    """
    Main Lambda handler function.
    Fetches world data, processes players, builds HTML, and uploads to S3.
    """
    t0 = time.time()
    print("Starting lambda_handler")

    # ========== Load Config + Fetch Worlds Concurrently ==========
    # The S3 config read and the API fan-out are independent; overlapping them
    # shaves the S3 round-trip off the critical path.
    with ThreadPoolExecutor(max_workers=2) as ex:
        cfg_future = ex.submit(load_combined_config)
        fetch_future = ex.submit(fetch_all_worlds)
        cfg = cfg_future.result()
        worlds_data, errors = fetch_future.result()

    t1 = time.time()
    print(f"Fetched config + all worlds in {t1-t0:.2f}s")

    alerts = cfg.get('alerts', [])
    trolls = cfg.get('trolls', [])
    enemy_block = cfg.get('block', [])
    bastex_no_guild = cfg.get('bastex', [])
    enemy_guilds = cfg.get('world_guilds_data', {})

    # ========== Pre-process Sets for O(1) Lookups ==========
    trolls_set = set(x.lower() for x in trolls)
    alert_set = set(x.lower() for x in alerts)
    enemy_block_set = set(x.lower() for x in enemy_block)
    bastex_no_guild_set = set(x.lower() for x in bastex_no_guild)
    dan_troll_set = set()  # Empty as per original code
    nontelegram_set = set()  # Empty as per original code
    premmy_voc_set = set(PREMIUM_VOCATIONS)

    # ========== Build Member Index for Guild Lookups ==========
    member_index = build_member_index(enemy_guilds)

    # Track which worlds we have FRESH data for this run.
    # Merged cache fills display gaps, but online timers must only be
    # pruned against fresh data, never against stale cache or absence.
    fresh_worlds = set(worlds_data.keys())

    # ========== Check for Critical Errors ==========
    total_worlds = len(WORLDS)
    failed_worlds = len(errors)
    successful_worlds = len(worlds_data)

    if failed_worlds > 0:
        failure_rate = (failed_worlds / total_worlds) * 100
        print(f"⚠️  API Errors: {failed_worlds}/{total_worlds} worlds failed ({failure_rate:.1f}%)")

        # Check for 5xx server errors (API is down)
        server_errors = [w for w, e in errors.items() if e.get('status_code', 0) >= 500]
        if server_errors and ABORT_ON_SERVER_ERROR:
            error_msg = f"ABORTED: API server errors detected for {len(server_errors)} worlds: {', '.join(server_errors)}"
            print(f"❌ {error_msg}")
            print("Keeping existing HTML to preserve last known good state")
            return {
                'statusCode': 503,
                'body': error_msg,
                'errorCount': failed_worlds,
                'failedWorlds': list(errors.keys())
            }

        # Check if failure rate exceeds threshold
        if failure_rate > MAX_FAILURE_RATE:
            error_msg = f"ABORTED: Failure rate {failure_rate:.1f}% exceeds threshold {MAX_FAILURE_RATE}%"
            print(f"❌ {error_msg}")
            print("Keeping existing HTML to preserve last known good state")
            return {
                'statusCode': 500,
                'body': error_msg,
                'errorCount': failed_worlds,
                'failedWorlds': list(errors.keys())
            }

        # Continue with partial data - merge with last known good data
        print(f"⚠️  Partial failure - merging with cached data")
        print(f"   New data from {successful_worlds} worlds, using cached data for {failed_worlds} failed worlds")

        # Load last known good data
        last_known_data = load_last_known_worlds_data()

        # Merge: keep new data for successful worlds, use cached data for failed worlds
        for failed_world in errors.keys():
            if failed_world in last_known_data:
                worlds_data[failed_world] = last_known_data[failed_world]
                print(f"   ↻ Using cached data for {failed_world}")
            else:
                print(f"   ⚠️  No cached data for {failed_world} - will be missing from output")
    else:
        print(f"✅ All {total_worlds} worlds fetched successfully")

    # ========== Update Online Status Tracker ==========
    # fresh_worlds prevents timer wipes for worlds served from cache or missing.
    online_tracker = update_player_online_status(
        worlds_data, alert_set, premmy_voc_set, CHAT_ID_MYKERA,
        fetched_worlds=fresh_worlds
    )
    t2 = time.time()
    print(f"Updated online status in {t2-t1:.2f}s")

    # ========== Build HTML ==========
    now_ts = utcnow_ts()
    last_updated_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    html_content = build_html(
        worlds_data=worlds_data,
        member_index=member_index,
        last_updated_iso=last_updated_iso,
        online_tracker=online_tracker,
        trolls_set=trolls_set,
        alert_set=alert_set,
        enemy_block_set=enemy_block_set,
        bastex_no_guild_set=bastex_no_guild_set,
        dan_troll_set=dan_troll_set,
        nontelegram_set=nontelegram_set,
        premmy_voc_set=premmy_voc_set,
        now_ts=now_ts
    )
    t3 = time.time()
    print(f"Built HTML in {t3-t2:.2f}s")

    # ========== Upload HTML + Save Backup Concurrently ==========
    # Two independent S3 PUTs; overlap them instead of running back-to-back.
    with ThreadPoolExecutor(max_workers=2) as ex:
        html_future = ex.submit(put_html_if_changed, BUCKET_NAME, OUTPUT_FILE_NAME, html_content)
        backup_future = ex.submit(save_last_known_worlds_data, worlds_data)
        html_future.result()
        backup_future.result()

    t4 = time.time()
    print(f"S3 uploads completed in {t4-t3:.2f}s")

    # ========== Performance Summary ==========
    total_time = t4 - t0
    print(f"Total execution time: {total_time:.2f}s")
    print(f"Breakdown - Fetch+Config: {t1-t0:.2f}s | Status: {t2-t1:.2f}s | HTML: {t3-t2:.2f}s | Upload: {t4-t3:.2f}s")

    return {
        'statusCode': 200,
        'body': 'OK',
        'executionTime': f"{total_time:.2f}s"
    }