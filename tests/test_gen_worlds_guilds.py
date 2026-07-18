"""
Tests for scripts/gen_worlds_guilds.py - World guild data generation.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import gen_worlds_guilds  # noqa: E402
from gen_worlds_guilds import build_world_data  # noqa: E402


def make_fetch_guild(responses):
    """Build a fake fetch_guild returning canned member lists per guild name."""
    def fake_fetch_guild(guild_name):
        return responses.get(guild_name)
    return fake_fetch_guild


class TestBuildWorldData:
    """Test that world data is rebuilt from the current guild list."""

    def test_fetches_members_for_active_guilds(self, monkeypatch):
        monkeypatch.setattr(gen_worlds_guilds, 'fetch_guild', make_fetch_guild({
            "Alpha": {"members": [{"name": "Player One"}, {"name": "Player Two"}]}
        }))
        world_data, processed, failed = build_world_data(
            [{"name": "Alpha"}], old_world_data={}
        )
        assert world_data == {"Alpha": ["Player One", "Player Two"]}
        assert processed == 1
        assert failed == 0

    def test_removes_disbanded_guilds(self, monkeypatch):
        """Guilds missing from the current guild list must be dropped."""
        monkeypatch.setattr(gen_worlds_guilds, 'fetch_guild', make_fetch_guild({
            "Alpha": {"members": [{"name": "Player One"}]}
        }))
        old_data = {
            "Alpha": ["Player One"],
            "Disbanded Guild": ["Old Player"]
        }
        world_data, _, _ = build_world_data([{"name": "Alpha"}], old_data)
        assert "Disbanded Guild" not in world_data
        assert world_data == {"Alpha": ["Player One"]}

    def test_keeps_old_data_when_guild_fetch_fails(self, monkeypatch):
        """A still-active guild whose member fetch fails keeps its old data."""
        monkeypatch.setattr(gen_worlds_guilds, 'fetch_guild', make_fetch_guild({}))
        old_data = {"Alpha": ["Player One", "Player Two"]}
        world_data, processed, failed = build_world_data(
            [{"name": "Alpha"}], old_data
        )
        assert world_data == {"Alpha": ["Player One", "Player Two"]}
        assert processed == 0
        assert failed == 1

    def test_failed_fetch_without_old_data_is_skipped(self, monkeypatch):
        monkeypatch.setattr(gen_worlds_guilds, 'fetch_guild', make_fetch_guild({}))
        world_data, processed, failed = build_world_data(
            [{"name": "Brand New Guild"}], old_world_data={}
        )
        assert world_data == {}
        assert failed == 1

    def test_ignores_guilds_without_a_name(self, monkeypatch):
        monkeypatch.setattr(gen_worlds_guilds, 'fetch_guild', make_fetch_guild({}))
        world_data, processed, failed = build_world_data(
            [{"name": ""}, {}], old_world_data={}
        )
        assert world_data == {}
        assert processed == 0
        assert failed == 0

    def test_empty_guild_list_clears_world(self, monkeypatch):
        """If the API reports no active guilds, old guilds are all removed."""
        monkeypatch.setattr(gen_worlds_guilds, 'fetch_guild', make_fetch_guild({}))
        old_data = {"Ghost Guild": ["Someone"]}
        world_data, _, _ = build_world_data([], old_data)
        assert world_data == {}

    def test_updates_member_list_of_existing_guild(self, monkeypatch):
        monkeypatch.setattr(gen_worlds_guilds, 'fetch_guild', make_fetch_guild({
            "Alpha": {"members": [{"name": "New Member"}]}
        }))
        old_data = {"Alpha": ["Old Member"]}
        world_data, _, _ = build_world_data([{"name": "Alpha"}], old_data)
        assert world_data == {"Alpha": ["New Member"]}
