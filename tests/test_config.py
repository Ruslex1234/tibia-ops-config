"""
Tests for scripts/config.py - Validates configuration values.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from config import (  # noqa: E402
    TIBIADATA_BASE_URL,
    MAX_RETRIES,
    INITIAL_BACKOFF,
    TRANSIENT_ERROR_CODES,
    REQUEST_TIMEOUT,
    WORLDS,
    ENEMY_GUILDS,
    CONFIGS_DIR,
    TROLLS_FILE,
    BASTEX_FILE
)


class TestAPIConfig:
    """Test API configuration values."""

    def test_tibiadata_url_is_https(self):
        assert TIBIADATA_BASE_URL.startswith("https://")

    def test_tibiadata_url_is_v4(self):
        assert "/v4" in TIBIADATA_BASE_URL

    def test_max_retries_is_positive(self):
        assert MAX_RETRIES > 0

    def test_initial_backoff_is_positive(self):
        assert INITIAL_BACKOFF > 0

    def test_transient_error_codes_are_valid_http_codes(self):
        for code in TRANSIENT_ERROR_CODES:
            assert 400 <= code <= 599

    def test_request_timeout_is_reasonable(self):
        assert 5 <= REQUEST_TIMEOUT <= 120


class TestWorldConfig:
    """Test world configuration."""

    def test_worlds_is_not_empty(self):
        assert len(WORLDS) > 0

    def test_firmera_in_worlds(self):
        assert "Firmera" in WORLDS

    def test_tempestera_in_worlds(self):
        assert "Tempestera" in WORLDS

    def test_no_duplicate_worlds(self):
        assert len(WORLDS) == len(set(WORLDS))


class TestEnemyGuildConfig:
    """Test enemy guild configuration."""

    def test_enemy_guilds_is_not_empty(self):
        assert len(ENEMY_GUILDS) > 0

    def test_bastex_maps_to_firmera(self):
        assert ENEMY_GUILDS["Bastex"] == "Firmera"

    def test_bastex_ruzh_maps_to_tempestera(self):
        assert ENEMY_GUILDS["Bastex Ruzh"] == "Tempestera"

    def test_all_enemy_guild_worlds_exist_in_worlds_list(self):
        for guild, world in ENEMY_GUILDS.items():
            assert world in WORLDS, f"Guild '{guild}' maps to '{world}' which is not in WORLDS list"


class TestFilePathConfig:
    """Test file path configuration."""

    def test_trolls_file_is_under_configs_dir(self):
        assert TROLLS_FILE.startswith(CONFIGS_DIR)

    def test_bastex_file_is_under_configs_dir(self):
        assert BASTEX_FILE.startswith(CONFIGS_DIR)

    def test_all_files_are_json(self):
        assert TROLLS_FILE.endswith('.json')
        assert BASTEX_FILE.endswith('.json')
