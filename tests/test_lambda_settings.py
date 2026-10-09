"""
Tests for lambda/bastex_online/config.py apply_settings() and the
.configs/settings.json file that drives it.
"""

import importlib.util
import json
import os

import pytest

REPO_ROOT = os.path.join(os.path.dirname(__file__), '..')
LAMBDA_CONFIG = os.path.join(REPO_ROOT, 'lambda', 'bastex_online', 'config.py')
SETTINGS_FILE = os.path.join(REPO_ROOT, '.configs', 'settings.json')


@pytest.fixture
def lcfg():
    """Fresh copy of the Lambda config module (name differs from scripts/config.py)."""
    spec = importlib.util.spec_from_file_location('bastex_lambda_config', LAMBDA_CONFIG)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def settings():
    with open(SETTINGS_FILE, encoding='utf-8') as f:
        return json.load(f)


class TestRepoSettingsFile:
    def test_every_key_applies(self, lcfg, settings):
        applied = lcfg.apply_settings(settings)
        assert sorted(applied) == sorted(settings.keys())

    def test_worlds_unique(self, settings):
        assert len(settings['worlds']) == len(set(settings['worlds']))

    def test_matches_scripts_worlds(self, settings):
        import sys
        sys.path.insert(0, os.path.join(REPO_ROOT, 'scripts'))
        from config import WORLDS
        assert WORLDS == settings['worlds']


class TestApplySettings:
    def test_lists_updated_in_place(self, lcfg):
        worlds_ref = lcfg.WORLDS
        lcfg.apply_settings({'worlds': ['Antica', 'Secura']})
        assert worlds_ref == ['Antica', 'Secura']

    def test_sets_follow_lists(self, lcfg):
        set_ref = lcfg.SPECIAL_GUILDS_SET
        lcfg.apply_settings({'special_guilds': ['New Guild']})
        assert set_ref == {'New Guild'}

    def test_color_map_in_place(self, lcfg):
        ref = lcfg.COLOR_MAP
        lcfg.apply_settings({'color_map': {'Alerts': '#000000'}})
        assert ref == {'Alerts': '#000000'}

    def test_scalars_rebound(self, lcfg):
        lcfg.apply_settings({'min_level_filter': 50, 'abort_on_server_error': False})
        assert lcfg.MIN_LEVEL_FILTER == 50
        assert lcfg.ABORT_ON_SERVER_ERROR is False

    @pytest.mark.parametrize('bad', [
        {'worlds': []},
        {'worlds': 'Antica'},
        {'worlds': ['Antica', 5]},
        {'min_level_filter': '8'},
        {'min_level_filter': True},
        {'abort_on_server_error': 1},
        {'color_map': ['x']},
    ])
    def test_invalid_values_keep_current(self, lcfg, bad):
        before = (list(lcfg.WORLDS), lcfg.MIN_LEVEL_FILTER, lcfg.ABORT_ON_SERVER_ERROR, dict(lcfg.COLOR_MAP))
        assert lcfg.apply_settings(bad) == []
        after = (list(lcfg.WORLDS), lcfg.MIN_LEVEL_FILTER, lcfg.ABORT_ON_SERVER_ERROR, dict(lcfg.COLOR_MAP))
        assert before == after

    @pytest.mark.parametrize('missing', [None, {}, [], 'x'])
    def test_missing_or_malformed_block(self, lcfg, missing):
        assert lcfg.apply_settings(missing) == []

    def test_unknown_keys_ignored(self, lcfg):
        assert lcfg.apply_settings({'something_new': 1}) == []
