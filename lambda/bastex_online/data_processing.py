"""
Data processing functions for fetching and processing world and player data
data_processing.py
"""
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed

import config
from utils import (
    http_get_json, http_pool, load_online_status, save_online_status,
    send_alert, _escape_markdown, utcnow_ts, APIError,
    format_timedelta_from_epoch, ALERTED_REGISTRY_KEY
)


# ========== API Fetching Functions ==========
def fetch_world_online_players(world_name):
    """Fetch online players for a specific world, filtered to level > settings min_level"""
    url = config.settings.world_url.replace("{world_name}", world_name)
    data = http_get_json(url)

    players = data['world'].get('online_players')
    if players is not None:
        min_level = config.settings.min_level
        data['world']['online_players'] = [
            p for p in players if p.get('level', 0) > min_level
        ]

    return data


def fetch_all_worlds(world_list=None):
    """
    Fetch online players for all worlds concurrently.
    Returns: (results_dict, errors_dict)
        results_dict: {world_name: world_data}
        errors_dict: {world_name: error_info}
    """
    if world_list is None:
        world_list = config.settings.worlds
    results = {}
    errors = {}
    workers = min(len(world_list), config.settings.max_parallel_requests or len(world_list))
    http_pool(workers)

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
def update_player_online_status(online_players, alert_set, chat_ids, fetched_worlds=None):
    """
    Update player online status tracking and send alerts for new logins.

    chat_ids: Telegram chat IDs that receive login/logoff alerts.

    fetched_worlds: set of world names we actually have data for this run.
    Worlds NOT in this set are left untouched, so a failed fetch with no
    cached fallback no longer wipes everyone's "online since" timers.

    Returns the updated online_status dict with epoch timestamps.
    """
    if fetched_worlds is None:
        fetched_worlds = set(online_players.keys())

    s = config.settings
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

            is_target = nm.lower() in alert_set and p.get('vocation') in s.premium_vocations
            is_new_login = nm not in online_status[world]

            if is_new_login:
                online_status[world][nm] = now_ts
                changed = True

                # Alert for anyone in alert_set with a premium vocation
                if is_target:
                    pending_alerts.append(s.login_message.format(name=_escape_markdown(nm)))

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
                pending_alerts.append(
                    s.logoff_message.format(name=_escape_markdown(n), duration=duration)
                )
                world_alerted.pop(n, None)

        online_status[world] = kept

    if changed:
        save_online_status(online_status)

    # Send alerts after state is persisted so a Telegram hiccup can't
    # delay or interfere with the tracking write.
    for msg in pending_alerts:
        for chat_id in chat_ids:
            send_alert(chat_id, msg)

    return online_status


# ========== Player Categorization ==========
def categorize_players(online_players_sorted, member_idx, trolls_set, alert_set,
                       enemy_block_set, bastex_no_guild_set):
    """
    Categorize players based on their guild membership and special lists.
    Returns a dict of {category label: [players]}
    """
    s = config.settings
    labels = s.labels
    categorized_players = {labels[k]: [] for k in ('trolls', 'alerts', 'enemy_block', 'others')}

    for player in online_players_sorted:
        name = player.get('name', '')
        if not name:
            continue

        lname = name.lower()

        if lname in trolls_set:
            player_category = labels['trolls']
        elif lname in alert_set:
            player_category = (labels['alerts'] if player.get('vocation', '') in s.premium_vocations
                               else s.unguilded_enemy_label)
        elif lname in enemy_block_set:
            player_category = labels['enemy_block']
        elif lname in bastex_no_guild_set:
            player_category = s.unguilded_enemy_label
        else:
            player_category = member_idx.get(name) or member_idx.get(lname) or labels['others']

        categorized_players.setdefault(player_category, []).append(player)

    return categorized_players


# ========== Category Sorting ==========
def sort_categories(categorized_players):
    """Order: show_first lists, enemies, friends, dan, any other guild, Others"""
    s = config.settings
    others = s.labels['others']
    ordered = OrderedDict()

    for group in (s.show_first, s.enemies, s.friends, s.dan):
        for c in group:
            if c in categorized_players and c not in ordered:
                ordered[c] = categorized_players[c]

    for c, players in categorized_players.items():
        if c not in ordered and c != others:
            ordered[c] = players

    if others in categorized_players:
        ordered[others] = categorized_players[others]

    return ordered
