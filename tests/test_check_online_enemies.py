"""
Tests for scripts/check_online_enemies.py - Enemy tracker unit tests.
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from check_online_enemies import (
    extract_player_killers,
    build_case_insensitive_map,
    load_json_list,
    save_trolls
)


class TestExtractPlayerKillers:
    """Test death list killer extraction."""

    def test_extracts_player_killers(self, sample_deaths):
        killers = extract_player_killers(sample_deaths)
        assert "Evil Player" in killers
        assert "Another Troll" in killers

    def test_excludes_creatures(self, sample_deaths):
        killers = extract_player_killers(sample_deaths)
        assert "a dragon lord" not in killers
        assert "a demon" not in killers

    def test_deduplicates_killers(self, sample_deaths):
        """Evil Player appears in two deaths but should only be listed once."""
        killers = extract_player_killers(sample_deaths)
        assert killers.count("Evil Player") == 1

    def test_empty_deaths_returns_empty(self):
        killers = extract_player_killers([])
        assert killers == []

    def test_deaths_with_no_players(self):
        deaths = [{"killers": [{"name": "a dragon", "player": False}]}]
        killers = extract_player_killers(deaths)
        assert killers == []


class TestBuildCaseInsensitiveMap:
    """Test the case-insensitive lookup map builder."""

    def test_builds_map_from_list(self, sample_trolls_list):
        lookup = build_case_insensitive_map(sample_trolls_list)
        assert "ruslex" in lookup
        assert "rodlex" in lookup

    def test_map_stores_index_and_original_name(self, sample_trolls_list):
        lookup = build_case_insensitive_map(sample_trolls_list)
        idx, name = lookup["ruslex"]
        assert idx == 0
        assert name == "Ruslex"

    def test_case_insensitive_lookup(self, sample_trolls_list):
        lookup = build_case_insensitive_map(sample_trolls_list)
        assert "trip wick" in lookup
        assert "TRIP WICK" not in lookup  # Only lowercase keys

    def test_empty_list_returns_empty_map(self):
        lookup = build_case_insensitive_map([])
        assert lookup == {}


class TestLoadJsonList:
    """Test JSON file loading."""

    def test_loads_existing_file(self, tmp_configs):
        result = load_json_list(tmp_configs["trolls"])
        assert "Ruslex" in result
        assert "Rodlex" in result

    def test_returns_empty_for_missing_file(self):
        result = load_json_list("/nonexistent/path.json")
        assert result == []

    def test_returns_empty_for_invalid_json(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json{{{")
        result = load_json_list(str(bad_file))
        assert result == []


class TestSaveTrolls:
    """Test trolls list saving."""

    def test_saves_list_to_file(self, tmp_path, monkeypatch):
        out_file = tmp_path / "trolls.json"
        monkeypatch.setattr(
            'check_online_enemies.TROLLS_FILE',
            str(out_file)
        )
        result = save_trolls(["Player One", "Player Two"])
        assert result is True

        with open(str(out_file)) as f:
            saved = json.load(f)
        assert saved == ["Player One", "Player Two"]

    def test_save_uses_indent(self, tmp_path, monkeypatch):
        out_file = tmp_path / "trolls.json"
        monkeypatch.setattr(
            'check_online_enemies.TROLLS_FILE',
            str(out_file)
        )
        save_trolls(["Test"])
        content = out_file.read_text()
        assert "    " in content  # 4-space indent


class TestDuplicateDetection:
    """Test that the system correctly handles duplicates."""

    def test_bastex_members_would_be_in_lookup(self, sample_bastex_list):
        """Verify bastex set is built correctly for skip logic."""
        bastex_set = {name.lower() for name in sample_bastex_list}
        assert "evil player" in bastex_set
        assert "guild member one" in bastex_set

    def test_case_insensitive_match_catches_variants(self):
        trolls = ["Ruslex", "Trip Wick"]
        lookup = build_case_insensitive_map(trolls)
        # Simulating what the main loop does
        assert "ruslex" in lookup       # exact lowercase
        assert "trip wick" in lookup     # with space
