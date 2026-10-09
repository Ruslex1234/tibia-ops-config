"""
Tests for the bastex_online Lambda: settings parsing (lambda/bastex_online/config.py),
the .configs/settings.json file that drives it, and an end-to-end handler run
with S3 and the TibiaData API stubbed.
"""

import copy
import importlib.util
import json
import os
import subprocess
import sys
import textwrap

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LAMBDA_DIR = os.path.join(REPO_ROOT, 'lambda', 'bastex_online')
SETTINGS_FILE = os.path.join(REPO_ROOT, '.configs', 'settings.json')


@pytest.fixture(scope='module')
def lcfg():
    """The Lambda config module (its name collides with scripts/config.py)."""
    spec = importlib.util.spec_from_file_location('bastex_lambda_config', os.path.join(LAMBDA_DIR, 'config.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def raw():
    with open(SETTINGS_FILE, encoding='utf-8') as f:
        return json.load(f)


def _set(d, path, value):
    *parents, last = path.split('.')
    for p in parents:
        d = d[p]
    if value is _DELETE:
        del d[last]
    else:
        d[last] = value


_DELETE = object()


class TestRepoSettingsFile:
    def test_parses(self, lcfg, raw):
        s = lcfg.parse_settings(raw)
        assert s.worlds and s.enemies and s.friends

    def test_scripts_read_same_file(self, raw):
        sys.path.insert(0, os.path.join(REPO_ROOT, 'scripts'))
        from config import WORLDS, ENEMY_GUILDS
        assert WORLDS == raw['worlds']
        assert ENEMY_GUILDS == raw['death_watch']

    def test_no_guild_in_two_groups(self, raw):
        g = raw['guilds']
        enemies, friends, dan = set(g['enemies']['names']), set(g['friends']['names']), set(g['dan']['names'])
        assert not enemies & friends, enemies & friends
        assert not enemies & dan, enemies & dan
        assert not friends & dan, friends & dan

    def test_enemy_orange_friend_green(self, raw):
        assert raw['guilds']['enemies']['color'].upper() == '#FF8C00'
        assert raw['guilds']['friends']['color'].upper() == '#1D8102'


class TestParseSettings:
    @pytest.mark.parametrize('path,value', [
        ('worlds', []),
        ('worlds', 'Antica'),
        ('worlds', ['Antica', 'Antica']),
        ('worlds', _DELETE),
        ('guilds.enemies.names', ['Ok', 5]),
        ('guilds.enemies.color', 'orange'),
        ('guilds.friends', _DELETE),
        ('lists.others.color', '#12345'),
        ('lists.alerts.label', 'Trolls'),
        ('show_first', ['nope']),
        ('min_level', '8'),
        ('min_level', True),
        ('abort.max_failed_worlds_percent', 101),
        ('abort.on_server_error', 1),
        ('telegram.alert_recipients', ['Mykera']),
        ('telegram.login_message', '{nme} logged on'),
        ('telegram.logoff_message', '{name} {oops}'),
        ('api.world_url', 'http://api.tibiadata.com/v4/world/{world_name}'),
        ('api.world_url', 'https://api.tibiadata.com/v4/world/'),
        ('page.refresh_seconds', 1),
        ('page.character_links', [{'label': 'R', 'url': 'https://x.test/'}]),
        ('page.server_types', [{'value': 'Retro Open', 'label': 'Retro Open'}]),
        ('death_watch', {'Bastex': 'Nowhere'}),
    ])
    def test_rejects(self, lcfg, raw, path, value):
        bad = copy.deepcopy(raw)
        _set(bad, path, value)
        with pytest.raises(lcfg.SettingsError) as e:
            lcfg.parse_settings(bad)
        assert path.split('.')[0] in str(e.value)

    @pytest.mark.parametrize('value', [None, [], 'x'])
    def test_rejects_non_object(self, lcfg, value):
        with pytest.raises(lcfg.SettingsError):
            lcfg.parse_settings(value)

    def test_reports_every_error(self, lcfg, raw):
        bad = copy.deepcopy(raw)
        bad['min_level'] = 'x'
        bad['page']['title'] = ''
        with pytest.raises(lcfg.SettingsError) as e:
            lcfg.parse_settings(bad)
        assert len(e.value.errors) == 2

    def test_show_first_resolves_labels(self, lcfg, raw):
        s = lcfg.parse_settings(raw)
        assert s.show_first == tuple(raw['lists'][k]['label'] for k in raw['show_first'])


HANDLER_RUN = textwrap.dedent('''
    import json, sys
    import lambda_function as lf, data_processing, utils
    settings = json.load(open(sys.argv[1]))
    enemy = settings["guilds"]["enemies"]["names"][0]
    friend = settings["guilds"]["friends"]["names"][0]
    cfg = {"settings": settings, "alerts": ["Target"], "trolls": ["Troll"], "block": [], "bastex": [],
           "world_guilds_data": {w: {enemy: ["Foe"], friend: ["Pal"]} for w in settings["worlds"]}}
    utils.load_combined_config = lf.load_combined_config = lambda: cfg
    seen, sent, out = [], [], {}
    def fake_get(url):
        w = url.rsplit("/", 1)[1]
        seen.append(w)
        return {"world": {"name": w, "players_online": 5, "online_players": [
            {"name": "Foe", "level": 500, "vocation": "Elite Knight"},
            {"name": "Pal", "level": 200, "vocation": "Elder Druid"},
            {"name": "Troll", "level": 100, "vocation": "Knight"},
            {"name": "Target", "level": 400, "vocation": settings["premium_vocations"][0]},
            {"name": "Tiny", "level": 1, "vocation": "None"}]}}
    data_processing.http_get_json = fake_get
    data_processing.load_online_status = lambda: {}
    data_processing.save_online_status = lambda s: None
    data_processing.send_alert = lambda chat, msg: sent.append((chat, msg))
    lf.put_html_if_changed = lambda b, k, h: out.setdefault("html", h)
    lf.save_last_known_worlds_data = lambda d: None
    result = lf.lambda_handler({}, None)
    print("RESULT=" + json.dumps({"result": result, "seen": seen, "sent": sent, "html": out.get("html", "")}))
''')


def _run_handler(settings, extra_env=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith('AWS_')}
    env.update({
        'AWS_DEFAULT_REGION': 'us-east-1', 'BUCKET_NAME': 'b', 'OUTPUT_FILE_NAME': 'o.html',
        'CONFIG_S3_KEY': 'configs/combined.json', 'CHAT_ID_MYKERA': '42',
    })
    env.update(extra_env or {})
    proc = subprocess.run(
        [sys.executable, '-c', HANDLER_RUN, settings],
        cwd=LAMBDA_DIR, env=env, capture_output=True, text=True, timeout=60,
    )
    line = [x for x in proc.stdout.splitlines() if x.startswith('RESULT=')]
    assert line, proc.stdout + proc.stderr
    return json.loads(line[0][len('RESULT='):])


@pytest.fixture(scope='module')
def run():
    pytest.importorskip('boto3')
    return _run_handler(SETTINGS_FILE)


class TestHandler:
    def test_ok(self, run):
        assert run['result']['statusCode'] == 200

    def test_fetches_every_world_from_settings(self, run, raw):
        assert sorted(run['seen']) == sorted(raw['worlds'])

    def test_enemy_orange_friend_green(self, run, raw):
        html = run['html']
        assert f"color: {raw['guilds']['enemies']['color']};\">Foe<" in html
        assert f"color: {raw['guilds']['friends']['color']};\">Pal<" in html

    def test_low_levels_filtered(self, run):
        assert '>Tiny<' not in run['html']

    def test_alert_sent_to_named_recipient(self, run):
        assert run['sent'] and all(chat == '42' for chat, _ in run['sent'])
        assert 'Target' in run['sent'][0][1]

    def test_page_settings_applied(self, run, raw):
        assert f"<title>{raw['page']['title']}</title>" in run['html']
        assert f"REFRESH_MS = {raw['page']['refresh_seconds'] * 1000};" in run['html']
        for placeholder in ('__TITLE__', '__REFRESH_MS__', '__FRESH_MIN__', '__STALE_MIN__'):
            assert placeholder not in run['html']

    def test_missing_env_aborts(self):
        pytest.importorskip('boto3')
        run = _run_handler(SETTINGS_FILE, {'OUTPUT_FILE_NAME': ''})
        assert run['result']['statusCode'] == 500
        assert 'html' not in run or run['html'] == ''

    def test_invalid_settings_aborts_cold(self, tmp_path, raw):
        pytest.importorskip('boto3')
        bad = copy.deepcopy(raw)
        bad['worlds'] = []
        path = tmp_path / 'bad.json'
        path.write_text(json.dumps(bad))
        run = _run_handler(str(path))
        assert run['result']['statusCode'] == 503
        assert run['html'] == ''
