"""
Shared test fixtures for all test modules.
"""

import sys
import os
import json
import pytest

# Add scripts directory to path so tests can import project modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))


@pytest.fixture
def sample_deaths():
    """Sample death data mimicking TibiaData API response."""
    return [
        {
            "killers": [
                {"name": "Evil Player", "player": True},
                {"name": "a dragon lord", "player": False}
            ],
            "time": "2025-01-15T10:30:00Z"
        },
        {
            "killers": [
                {"name": "Another Troll", "player": True},
                {"name": "Evil Player", "player": True}
            ],
            "time": "2025-01-14T08:00:00Z"
        },
        {
            "killers": [
                {"name": "a demon", "player": False}
            ],
            "time": "2025-01-13T12:00:00Z"
        }
    ]


@pytest.fixture
def sample_trolls_list():
    """Sample trolls list for testing."""
    return ["Ruslex", "Rodlex", "Monlex", "Trip Wick"]


@pytest.fixture
def sample_bastex_list():
    """Sample bastex list for testing."""
    return ["Guild Member One", "Guild Member Two", "Evil Player"]


@pytest.fixture
def sample_character_response():
    """Sample TibiaData character API response."""
    return {
        "character": {
            "character": {
                "name": "Some Troll",
                "world": "Firmera",
                "guild": {}
            },
            "deaths": []
        }
    }


@pytest.fixture
def sample_guild_response():
    """Sample TibiaData guild API response."""
    return {
        "guild": {
            "name": "Bastex",
            "members": [
                {"name": "Player One", "status": "online"},
                {"name": "Player Two", "status": "offline"},
                {"name": "Player Three", "status": "online"}
            ]
        }
    }


@pytest.fixture
def tmp_configs(tmp_path):
    """Create temporary config files for testing."""
    configs_dir = tmp_path / ".configs"
    configs_dir.mkdir()

    trolls_file = configs_dir / "trolls.json"
    trolls_file.write_text(json.dumps(["Ruslex", "Rodlex"]))

    bastex_file = configs_dir / "bastex.json"
    bastex_file.write_text(json.dumps(["Guild Member One"]))

    return {
        "dir": str(configs_dir),
        "trolls": str(trolls_file),
        "bastex": str(bastex_file)
    }
