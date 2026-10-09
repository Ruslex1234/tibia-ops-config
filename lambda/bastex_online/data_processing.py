"""
Data processing functions for fetching and processing world and player data
data_processing.py
"""
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import (
    BASE_API_URL, WORLDS, MAX_WORKERS, MIN_LEVEL_FILTER,
    SPECIAL_GUILDS, PRIORITY_CATEGORIES, GREEN_CATEGORIES
)
from utils import (
    http_get_json, load_online_status, save_online_status,
    send_alert, _escape_markdown, utcnow_ts, APIError,
    format_timedelta_from_epoch, ALERTED_REGISTRY_KEY
)


# ========== API Fetching Functions ==========
def fetch_world_online_players(world_name):
    """Fetch online players for a specific world, filtered to level > MIN_LEVEL_FILTER"""
    url = BASE_API_URL.format(world_name=world_name)
    data = http_get_json(url)

    players = data['world'].get('online_players')
    if players is not None:
        data['world']['online_players'] = [
            p for p in players if p.get('level', 0) > MIN_LEVEL_FILTER
        ]

    return data


def fetch_all_worlds(world_list=WORLDS):
    """
    Fetch online players for all worlds concurrently.
    Returns: (results_dict, errors_dict)
        results_dict: {world_name: world_data}
        errors_dict: {world_name: error_info}
    """
    results = {}
    errors = {}
    workers = min(len(world_list), MAX_WORKERS)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        fut = {ex.submit(fetch_world_online_players, w): w for w in world_list}
        for f in as_completed(fut):
            w = fut[f]
            try:
                results[w] = f.result()['world']
            except APIError as e:
                error_msg = f"API Error {e.status_code}: {e.message}"
                print(f"{w} - {error_msg}")
                errors[w] = {
                    'type': 'api_error',
                    'status_code': e.status_code,
                    'message': error_msg
                }
            except Exception as e:
                error_msg = f"Unexpected error: {type(e).__name__}: {str(e)}"
                print(f"{w} - {error_msg}")
                errors[w] = {
                    'type': 'exception',
                    'message': error_msg
                }

    return results, errors


# ========== Member Index Building ==========
def build_member_index(world_guilds):
    """
    Build reverse index for O(1) guild lookup.
    Input: {"World": {"Guild": ["Member1", ...], ...}, ...}
    Output: {"World": {"MemberName": "Guild", "membername": "Guild", ...}, ...}
    """
    out = {}
    for world, guilds in (world_guilds or {}).items():
        m = {}
        for g, members in (guilds or {}).items():
            if not members:
                continue
            for nm in members:
                if not nm:
                    continue
                m[nm] = g
                m[nm.lower()] = g
        out[world] = m
    return out


# ========== Online Status Tracking ==========
def update_player_online_status(online_players, alert_set, premmy_voc_set,
                                chat_id_mykera, fetched_worlds=None):
    """
    Update player online status tracking and send alerts for new logins.

    fetched_worlds: set of world names we actually have data for this run.
    Worlds NOT in this set are left untouched, so a failed fetch with no
    cached fallback no longer wipes everyone's "online since" timers.

    Returns the updated online_status dict with epoch timestamps.
    """
    if fetched_worlds is None:
        fetched_worlds = set(online_players.keys())

    online_status = load_online_status()
    now_ts = utcnow_ts()
    changed = False
    pending_alerts = []

    # Registry of targets who qualified for alerts while online.
    # Needed because vocation can't be checked once a player is offline.
    alerted = online_status.setdefault(ALERTED_REGISTRY_KEY, {})

    for world, data in online_players.items():
        players = data.get('online_players') or []
        if world not in online_status:
            online_status[world] = {}
            changed = True

        world_alerted = alerted.setdefault(world, {})

        for p in players:
            nm = p.get('name')
            if not nm:
                continue

            is_target = nm.lower() in alert_set and p.get('vocation') in premmy_voc_set
            is_new_login = nm not in online_status[world]

            if is_new_login:
                online_status[world][nm] = now_ts
                changed = True

                # Alert Mykera's group for anyone in alert_set with premium vocation
                if is_target and chat_id_mykera:
                    pending_alerts.append(f"*{_escape_markdown(nm)} just logged on!*")

            # Register targets for logoff alerts. Also covers targets already
            # online at deploy time (registered silently, no login alert).
            if is_target and nm not in world_alerted:
                world_alerted[nm] = True
                changed = True

    # Remove players who are no longer online.
    # Only prune worlds we have fresh data for; skip failed/missing worlds
    # so timers survive a temporary outage.
    for world in list(online_status.keys()):
        if world == ALERTED_REGISTRY_KEY:
            continue
        if world not in fetched_worlds:
            continue
        current = online_players.get(world, {}).get('online_players') or []
        online_names = {p.get('name') for p in current if p.get('name')}

        world_alerted = alerted.get(world, {})
        kept = {}
        for n, t in online_status[world].items():
            if n in online_names:
                kept[n] = t
                continue
            changed = True
            # Player logged off: notify with session duration if registered
            if n in world_alerted:
                duration = format_timedelta_from_epoch(t, now_ts)
                if chat_id_mykera:
                    pending_alerts.append(
                        f"*{_escape_markdown(n)} logged off!* Online for {duration}"
                    )
                world_alerted.pop(n, None)

        online_status[world] = kept

    if changed:
        save_online_status(online_status)

    # Send alerts after state is persisted so a Telegram hiccup can't
    # delay or interfere with the tracking write.
    for msg in pending_alerts:
        send_alert(chat_id_mykera, msg)

    return online_status


# ========== Player Categorization ==========
def categorize_players(online_players_sorted, member_idx, trolls_set, alert_set,
                       enemy_block_set, bastex_no_guild_set, dan_troll_set,
                       nontelegram_set, premmy_voc_set):
    """
    Categorize players based on their guild membership and special lists.
    Returns a dict of {category: [players]}
    """
    categorized_players = {
        'Trolls': [], 'Alerts': [], 'Enemy Block': [],
        'Dan': [], 'Sleeping Beauty': [], 'Watch The Throne': [], 'Others': []
    }

    for player in online_players_sorted:
        name = player.get('name', '')
        if not name:
            continue

        lname = name.lower()
        vocation = player.get('vocation', '')

        if lname in trolls_set:
            player_category = 'Trolls'
        elif lname in alert_set:
            player_category = 'Alerts' if vocation in premmy_voc_set else 'Bastex'
        elif lname in enemy_block_set:
            player_category = 'Enemy Block'
        elif lname in bastex_no_guild_set:
            player_category = 'Bastex'
        elif lname in dan_troll_set:
            player_category = 'Dan'
        elif lname in nontelegram_set:
            player_category = 'Alerts'
        else:
            guild_name = member_idx.get(name) or member_idx.get(lname)
            player_category = guild_name if guild_name else 'Others'

        categorized_players.setdefault(player_category, []).append(player)

    return categorized_players


# ========== Category Sorting ==========
def sort_categories(categorized_players, special_guilds_list=SPECIAL_GUILDS,
                    priority_categories=PRIORITY_CATEGORIES,
                    green_categories=GREEN_CATEGORIES):
    """Sort categories in priority order"""
    ordered = OrderedDict()

    for c in priority_categories:
        if c in categorized_players:
            ordered[c] = categorized_players[c]

    for g in special_guilds_list:
        if g in categorized_players:
            ordered[g] = categorized_players[g]

    for c in green_categories:
        if c in categorized_players:
            ordered[c] = categorized_players[c]

    for c, players in categorized_players.items():
        if c not in ordered and c != "Others":
            ordered[c] = players

    if "Others" in categorized_players:
        ordered["Others"] = categorized_players["Others"]

    return ordered