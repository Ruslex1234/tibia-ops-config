"""
HTML generation functions for the online tracker
html_builder.py
"""
import json
import html as html_mod
import urllib.parse

import config
from utils import format_timedelta_from_epoch, extract_world_meta
from data_processing import categorize_players, sort_categories


# ========== HTML Template Components ==========
HTML_HEAD = """<!DOCTYPE html><html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
<title>__TITLE__</title>
<style>
  /* Base styles */
  * {box-sizing: border-box;}
  body {
    color:#eee;
    background-color:#2E2E2E;
    margin:0;
    padding:0;
    -webkit-font-smoothing: antialiased;
  }
  a:not([style]) {color:#1DAAE5;}
  h1,h2,h3{margin:0; padding:8px 0;}
  h1 {font-size: 1.8rem;}
  h2 {font-size: 1.3rem;}
  h3 {font-size: 1.1rem;}

  /* Tables - Desktop keeps original layout */
  table{border-collapse:collapse;margin-left:auto;margin-right:auto;}
  td{vertical-align:top;padding:0;}

  /* Main world grid table - shrink to content, don't stretch full width */
  .world-grid-table {
    border: 1px solid black;
    margin-left: auto;
    margin-right: auto;
    width: auto;
    table-layout: auto;
  }

  /* Each column sizes to its own longest row. No max cap: the row must
     never wrap, so the column is allowed to grow as wide as its widest line. */
  .world-col {
    width: 1%;               /* let the browser size to content */
    min-width: 200px;
    vertical-align: top;
    padding: 0 10px;         /* breathing room between columns */
    white-space: nowrap;     /* keep player rows on a single line */
  }

  /* World sections */
  .world {
    display: block;
  }

  /* Inner table sizes to its content, not a forced 100% */
  .world table {
    width: auto;
  }

  /* Player rows must never wrap onto a second line */
  .world td {
    white-space: nowrap;
  }

  /* Toolbar */
  .toolbar{
    max-width:100%;
    margin:8px auto 4px auto;
    padding:8px;
    border:1px solid #444;
    border-radius:10px;
    background:#2a2a2a;
  }
  .row{
    margin:4px 0;
    display:flex;
    flex-wrap:wrap;
    gap:6px;
    align-items:center;
    justify-content:center;
  }
  .label{font-size:12px;color:#aaa;margin-right:6px;}

  /* Chips - Enhanced for mobile */
  .chip{
    display:inline-block;
    padding:8px 14px;
    border-radius:16px;
    border:1px solid #555;
    text-decoration:none;
    color:#ddd;
    user-select:none;
    cursor:pointer;
    font-size:14px;
    min-height:44px;
    display:inline-flex;
    align-items:center;
    justify-content:center;
    touch-action: manipulation;
  }
  .chip:hover{background:#3a3a3a;}
  .chip.active{background:#444;border-color:#999;}
  .spacer{flex:1;}
  #hideEmptyWrap{font-size:14px;color:#bbb;}
  #hideEmptyWrap input[type="checkbox"] {
    width: 20px;
    height: 20px;
    vertical-align: middle;
    margin-right: 6px;
  }

  /* Better link touch targets on mobile */
  a {
    min-height: 24px;
    display: inline-block;
  }

  /* Mobile responsive styles - Stack worlds vertically on mobile */
  @media (max-width: 768px) {
    body {font-size: 16px;}
    h1 {font-size: 1.5rem;}
    h2 {font-size: 1.2rem;}
    h3 {font-size: 1rem;}

    /* Convert table to stacked layout on mobile */
    .world-grid-table,
    .world-grid-table tbody,
    .world-grid-table tr {
      display: block;
      width: 100%;
    }

    .world-col {
      display: block;
      width: 100% !important;
      min-width: 0;
      max-width: none;
      padding: 8px 4px;
      white-space: normal;   /* allow wrapping on narrow screens */
    }

    .world {
      background: #333;
      border-radius: 8px;
      padding: 12px;
      border: 1px solid #444;
      margin-bottom: 12px;
    }

    .world table {
      font-size: 0.85rem;
      width: 100%;
    }

    /* On mobile, let long names wrap rather than scroll sideways */
    .world td {
      white-space: normal;
    }

    .toolbar {
      padding: 6px;
      margin: 4px;
    }

    .chip {
      padding: 10px 12px;
      font-size: 13px;
    }

    .row {
      gap: 4px;
    }

    .label {
      width: 100%;
      margin-bottom: 4px;
      text-align: center;
    }
  }

  /* Very small screens */
  @media (max-width: 480px) {
    h1 {font-size: 1.3rem;}
    h2 {font-size: 1.1rem;}
    h3 {font-size: 0.95rem;}

    .world table {
      font-size: 0.8rem;
    }

    .chip {
      padding: 8px 10px;
      font-size: 12px;
    }

    td {padding: 1px 2px;}
  }
</style>
<script>
  // --- Auto-refresh using current URL (preserves active filters) ---
  const REFRESH_MS = __REFRESH_MS__;
  let refreshTimer = null;
  function startAutoRefresh(){
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = setInterval(function(){
      window.location.reload();
    }, REFRESH_MS);
  }

  // --- URL param helpers ---
  function _params(){ return new URLSearchParams(window.location.search); }
  function _setParam(k,v){
    const p = _params();
    if (v===null || v===undefined || v==='') p.delete(k); else p.set(k, v);
    const q = p.toString();
    const full = window.location.origin + window.location.pathname + (q ? '?' + q : '') + window.location.hash;
    try { window.history.replaceState({}, '', full); } catch (e) { window.location.search = q; }
  }
  function _getParam(k){ return _params().get(k); }
  function _hasParam(k){ return _params().has(k); }

  // clipboard helper: modern async API with legacy fallback
  function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).catch(function(){ _copyFallback(text); });
    } else {
      _copyFallback(text);
    }
  }
  function _copyFallback(text) {
    var tempInput = document.createElement("input");
    tempInput.style = "position: absolute; left: -1000px; top: -1000px";
    tempInput.value = text;
    document.body.appendChild(tempInput);
    tempInput.select();
    document.execCommand("copy");
    document.body.removeChild(tempInput);
  }

  // sanitize PvP tokens like "Retro Open" -> "retroopen"
  function _normPvP(s){ return (s||'').toLowerCase().replace(/[^a-z0-9]/g,'').replace(/pvp$/,''); }

  // Hide table columns whose world sections are all hidden
  function centerColumns(){
    const cols = document.querySelectorAll('td.world-col');
    cols.forEach(td=>{
      const sec = td.querySelector('section.world');
      const visible = sec && sec.style.display !== 'none';
      td.style.display = visible ? '' : 'none';
    });
  }

  // --- Filtering engine (EXACT match on PvP) ---
  function applyFilters(){
    const params = _params();
    const st  = _normPvP(params.get('servertype'));
    const wls = params.get('world');
    const showWorlds = wls ? new Set(wls.split(',').map(w=>w.trim().toLowerCase()).filter(Boolean)) : null;
    const hideEmpty = params.has('hideempty');

    const sections = document.querySelectorAll('section.world');
    let visibleCount = 0;
    sections.forEach(sec=>{
      const world = (sec.dataset.world||'').toLowerCase();
      const pvp   = (sec.dataset.pvp||'').toLowerCase();
      let vis = true;
      if (st) vis = (pvp === st);
      if (vis && showWorlds) vis = showWorlds.has(world);
      if (vis && hideEmpty)  vis = sec.querySelectorAll('tr[data-player-row]').length>0;
      sec.style.display = vis ? '' : 'none';
      if (vis) visibleCount++;
    });

    centerColumns();

    const banner = document.getElementById('filterBanner');
    const bits = [];
    if (st) bits.push('servertype='+st);
    if (wls) bits.push('world='+wls);
    if (hideEmpty) bits.push('hideempty=1');
    banner.textContent = bits.length ? ('Filters: '+bits.join(' | ')) : '';
    banner.style.display = bits.length ? 'block' : 'none';
    document.getElementById('noMatchMsg').style.display = (visibleCount===0)?'block':'none';
  }

  // --- Toolbar UI state ---
  function refreshUI(){
    const st  = _normPvP(_getParam('servertype'));
    const wls = (_getParam('world')||'').toLowerCase().split(',').filter(Boolean);
    const wset= new Set(wls);

    document.querySelectorAll('.chip.st').forEach(el=>{
      const val = el.dataset.val||'';
      if (!val && !st) el.classList.add('active');
      else if (val && st===val) el.classList.add('active');
      else el.classList.remove('active');
    });

    document.querySelectorAll('.chip.world').forEach(el=>{
      const w = (el.dataset.world||'').toLowerCase();
      if (wset.has(w)) el.classList.add('active'); else el.classList.remove('active');
    });

    const hideChk = document.getElementById('hideEmptyChk');
    hideChk.checked = _hasParam('hideempty');
  }

  // --- Event wiring ---
  function wireToolbar(){
    document.querySelectorAll('.chip.st').forEach(el=>{
      el.addEventListener('click', function(ev){
        ev.preventDefault(); ev.stopPropagation();
        const val = this.dataset.val||'';
        _setParam('servertype', val);
        applyFilters(); refreshUI();
      });
    });
    document.querySelectorAll('.chip.world').forEach(el=>{
      el.addEventListener('click', function(ev){
        ev.preventDefault(); ev.stopPropagation();
        const w = (this.dataset.world||'').toLowerCase();
        const cur = (_getParam('world')||'').toLowerCase().split(',').filter(Boolean);
        const set = new Set(cur);
        if (set.has(w)) set.delete(w); else set.add(w);
        if (set.size) _setParam('world', Array.from(set).join(','));
        else _setParam('world','');
        applyFilters(); refreshUI();
      });
    });
    const chk = document.getElementById('hideEmptyChk');
    chk.addEventListener('change', function(){
      if (this.checked) _setParam('hideempty','1'); else _setParam('hideempty','');
      applyFilters(); refreshUI();
    });
    const reset = document.getElementById('clearFilters');
    reset.addEventListener('click', function(ev){
      ev.preventDefault(); ev.stopPropagation();
      const full = window.location.origin + window.location.pathname + window.location.hash;
      try { history.replaceState({}, '', full); } catch(e) { window.location.search = ''; }
      applyFilters(); refreshUI();
    });
  }

  document.addEventListener('DOMContentLoaded', function(){
    const lastUpdated = document.body.dataset.lastUpdated || '';
    const el = document.getElementById('lastUpdatedText');
    const t = new Date(lastUpdated);
    const now = new Date();
    const diffMin = Math.floor((now - t)/60000);
    el.textContent = "Last Updated: " + diffMin + " minutes ago";
    if (diffMin <= __FRESH_MIN__) el.style.color = "green";
    else if (diffMin <= __STALE_MIN__) el.style.color = "orange";
    else el.style.color = "red";

    wireToolbar();
    applyFilters();
    refreshUI();
    startAutoRefresh();
  });
</script>
</head>
"""


def render_head():
    """HTML_HEAD with page settings filled in"""
    s = config.settings
    return (HTML_HEAD
            .replace("__TITLE__", html_mod.escape(s.page_title))
            .replace("__REFRESH_MS__", str(s.refresh_seconds * 1000))
            .replace("__FRESH_MIN__", str(s.fresh_minutes))
            .replace("__STALE_MIN__", str(s.stale_minutes)))


def build_toolbar():
    """Build the filter toolbar HTML"""
    s = config.settings
    parts = ['<div class="toolbar">']
    parts.append('<div class="row"><span class="label">Server type:</span>')

    for val, label in s.server_types:
        parts.append(f'<a href="#" class="chip st" data-val="{val}">{html_mod.escape(label)}</a>')
    parts.append('</div>')

    parts.append('<div class="row"><span class="label">Worlds:</span>')
    for w in s.worlds:
        w_html = html_mod.escape(w)
        parts.append(f'<a href="#" class="chip world" data-world="{w_html.lower()}">{w_html}</a>')
    parts.append('</div>')

    parts.append('''
      <div class="row">
        <span id="hideEmptyWrap"><label><input type="checkbox" id="hideEmptyChk"> Hide empty</label></span>
        <span class="spacer"></span>
        <a href="#" id="clearFilters" class="chip">Reset</a>
      </div>
    ''')
    parts.append('</div>')

    return "".join(parts)


def render_player_row(world, player, category, online_tracker, now_ts,
                      alert_set, enemy_block_set):
    """Render a single player row"""
    s = config.settings
    name = player.get("name", "")
    if not name:
        return ""

    vocation = player.get("vocation", "")
    level = player.get("level", 0)
    lname = name.lower()

    # Calculate online time directly from epoch (no string parsing)
    start_ts = online_tracker.get(world, {}).get(name, now_ts)
    online_since = format_timedelta_from_epoch(start_ts, now_ts)
    hours_online = max(0, now_ts - start_ts) // 3600

    # Determine color
    is_enemy = category in s.enemies_set or category == s.unguilded_enemy_label
    if is_enemy:
        color = s.enemy_color if level >= s.enemy_low_level_below else s.enemy_low_level_color
    elif category in s.dan_set:
        color = s.dan_color
    elif category in s.friends_set:
        color = s.friend_color
    else:
        color = s.label_colors.get(category, s.label_colors[s.labels['others']])

    display_color = color

    # Gray out tracked players online > threshold hours
    if hours_online > s.gray_after_hours and (
        is_enemy or
        (player.get("guild") in s.enemies_set) or
        (lname in enemy_block_set) or
        (lname in alert_set)
    ):
        display_color = s.gray_color

    # Vocation initials
    initials = "".join([v[0] for v in vocation.split()]) if vocation else ""

    # Safe encodings for URL, JS, and HTML contexts
    name_url = urllib.parse.quote(name, safe='')
    name_html = html_mod.escape(name)
    js_name_literal = html_mod.escape(json.dumps(name), quote=True)
    exiva_literal = html_mod.escape(json.dumps(f'exiva "{name}"'), quote=True)

    profile_url = html_mod.escape(s.profile_url.replace("{name}", name_url))
    extra_links = "".join(
        f"""
    <a href="{html_mod.escape(url.replace('{name}', name_url))}"
       target="_blank" rel="noopener noreferrer"
       style="color: {s.link_color};">[{html_mod.escape(label)}]</a>"""
        for label, url in s.character_links
    )

    return f"""
<tr data-player-row="1">
  <td>[{level}]</td>
  <td>
    <span style="cursor: pointer;" onclick='copyToClipboard({js_name_literal})'>{initials}</span>
  </td>
  <td>
    <a href="{profile_url}"
       target="_blank" rel="noopener noreferrer"
       style="color: {display_color};">{name_html}</a>{extra_links}
    (<span style="cursor: pointer;" onclick='copyToClipboard({exiva_literal})'>{online_since}</span>)
  </td>
</tr>
"""


def render_world_section(world, data, member_idx, online_tracker, now_ts,
                         trolls_set, alert_set, enemy_block_set,
                         bastex_no_guild_set):
    """Render a complete world section"""
    parts = []

    # Extract meta for filtering
    pvp_norm, loc_norm = extract_world_meta(data)

    online_players = data.get('online_players') or []
    online_players_sorted = sorted(online_players, key=lambda x: x.get('level', 0), reverse=True)

    # Categorize players
    categorized_players = categorize_players(
        online_players_sorted, member_idx,
        trolls_set, alert_set, enemy_block_set,
        bastex_no_guild_set
    )

    total_in_cat = sum(len(v) for v in categorized_players.values())

    # World wrapper with data attributes
    parts.append(f'<section class="world" data-world="{world}" data-pvp="{pvp_norm}" data-location="{loc_norm}">')
    parts.append("================================\n")
    parts.append(f"<center><h2>{world} ({total_in_cat})</h2></center>\n")
    parts.append("================================<br>")
    parts.append("<table>")

    # Sort categories
    categorized_players = sort_categories(categorized_players)

    # Render each category
    for category, players in categorized_players.items():
        if not players:
            continue
        cat_html = html_mod.escape(category)
        parts.append(f'<tr><td colspan="3"><center><h3>{cat_html} ({len(players)})</h3></center></td></tr>')
        for p in players:
            parts.append(render_player_row(
                world, p, category, online_tracker, now_ts,
                alert_set, enemy_block_set
            ))

    parts.append("</table>")
    parts.append("</section>")

    return "".join(parts)


# ========== Main HTML Builder ==========
def build_html(worlds_data, member_index, last_updated_iso, online_tracker,
               trolls_set, alert_set, enemy_block_set, bastex_no_guild_set, now_ts):
    """Build the complete HTML page"""
    parts = []

    # Head and body start
    parts.append(render_head())
    parts.append(f'<body data-last-updated="{last_updated_iso}">')
    parts.append(f"<center><h1>{html_mod.escape(config.settings.page_title)}</h1></center>")

    # Toolbar
    parts.append(build_toolbar())

    # Filter messages
    parts.append('<center><div id="filterBanner" style="display:none; margin:6px 0; font-size:12px; color:#bbb;"></div></center>')
    parts.append('<center><div id="noMatchMsg" style="display:none; margin:6px 0; font-size:13px; color:#f99;">No worlds match current filters.</div></center>')
    parts.append('<center><h4 id="lastUpdatedText">Last Updated: </h4></center>')

    # World grid table (desktop shows side-by-side, mobile stacks)
    parts.append('<table class="world-grid-table"><tr>')

    for world in config.settings.worlds:
        if world not in worlds_data:
            continue
        data = worlds_data[world]
        if data.get('players_online', 0) == 0:
            continue

        parts.append('<td class="world-col">')
        parts.append(render_world_section(
            world, data, member_index.get(world, {}),
            online_tracker, now_ts,
            trolls_set, alert_set, enemy_block_set,
            bastex_no_guild_set
        ))
        parts.append('</td>')

    parts.append("</tr></table>")
    parts.append("<center>===================================</center>")
    parts.append("<center>===================================</center>")
    parts.append("</body></html>")

    return "".join(parts)