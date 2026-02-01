"""
Tests for scripts/tibia_api.py - API client unit tests.
Uses mocking to avoid real API calls during CI.
"""

import sys
import os
import json
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from tibia_api import (  # noqa: E402
    fetch_with_retry,
    fetch_character,
    fetch_guild,
    get_online_guild_members,
    get_character_info
)


class TestFetchWithRetry:
    """Test the core retry logic."""

    @patch('tibia_api.urllib.request.urlopen')
    def test_successful_fetch(self, mock_urlopen):
        """Test that a successful API call returns data."""
        mock_response = MagicMock()
        mock_response.info.return_value = {}
        mock_response.read.return_value = json.dumps({"key": "value"}).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        data, success = fetch_with_retry("https://api.example.com/test")
        assert success is True
        assert data == {"key": "value"}

    @patch('tibia_api.urllib.request.urlopen')
    def test_returns_none_on_permanent_error(self, mock_urlopen):
        """Test that a 404 error returns None without retry."""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "https://api.example.com", 404, "Not Found", {}, None
        )

        data, success = fetch_with_retry("https://api.example.com/test", max_retries=1)
        assert success is False
        assert data is None


class TestFetchCharacter:
    """Test character fetching."""

    @patch('tibia_api.fetch_with_retry')
    def test_returns_character_data(self, mock_fetch):
        mock_fetch.return_value = (
            {"character": {"character": {"name": "Ruslex", "world": "Firmera"}}},
            True
        )
        result = fetch_character("Ruslex")
        assert result is not None
        assert result["character"]["name"] == "Ruslex"

    @patch('tibia_api.fetch_with_retry')
    def test_returns_none_on_failure(self, mock_fetch):
        mock_fetch.return_value = (None, False)
        result = fetch_character("NonExistent")
        assert result is None

    @patch('tibia_api.fetch_with_retry')
    def test_url_encodes_character_name(self, mock_fetch):
        mock_fetch.return_value = ({"character": {}}, True)
        fetch_character("Name With Spaces")
        called_url = mock_fetch.call_args[0][0]
        assert "Name%20With%20Spaces" in called_url


class TestFetchGuild:
    """Test guild fetching."""

    @patch('tibia_api.fetch_with_retry')
    def test_returns_guild_data(self, mock_fetch):
        mock_fetch.return_value = (
            {"guild": {"name": "Bastex", "members": []}},
            True
        )
        result = fetch_guild("Bastex")
        assert result is not None
        assert result["name"] == "Bastex"


class TestGetOnlineGuildMembers:
    """Test online member extraction."""

    @patch('tibia_api.fetch_guild')
    def test_returns_online_members_only(self, mock_fetch_guild, sample_guild_response):
        mock_fetch_guild.return_value = sample_guild_response["guild"]
        result = get_online_guild_members("Bastex")
        assert len(result) == 2
        assert "Player One" in result
        assert "Player Three" in result
        assert "Player Two" not in result  # offline

    @patch('tibia_api.fetch_guild')
    def test_returns_empty_on_failure(self, mock_fetch_guild):
        mock_fetch_guild.return_value = None
        result = get_online_guild_members("NonExistent")
        assert result == []


class TestGetCharacterInfo:
    """Test character info extraction."""

    @patch('tibia_api.fetch_character')
    def test_returns_character_info(self, mock_fetch):
        mock_fetch.return_value = {
            "character": {
                "name": "Some Troll",
                "world": "Firmera",
                "guild": {"name": ""}
            }
        }
        name, world, guild = get_character_info("Some Troll")
        assert name == "Some Troll"
        assert world == "Firmera"
        assert guild == ""

    @patch('tibia_api.fetch_character')
    def test_returns_guild_name(self, mock_fetch):
        mock_fetch.return_value = {
            "character": {
                "name": "Guilded Player",
                "world": "Firmera",
                "guild": {"name": "Bastex"}
            }
        }
        name, world, guild = get_character_info("Guilded Player")
        assert guild == "Bastex"

    @patch('tibia_api.fetch_character')
    def test_returns_none_on_failure(self, mock_fetch):
        mock_fetch.return_value = None
        name, world, guild = get_character_info("Ghost")
        assert name is None
        assert world is None
        assert guild is None
