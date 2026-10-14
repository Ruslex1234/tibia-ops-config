"""
Tests for scripts/cleanup_trolls.py - trolls.json cleanup logic.
Lookups are faked, so no real API calls are made.
"""

import sys
import os
import json
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from cleanup_trolls import clean, dedupe, load_trolls, save_trolls  # noqa: E402
from tibia_api import lookup_character  # noqa: E402


def make_lookup(table):
    """Fake lookup: table maps name -> live name, 'missing', 'error' or a list of those per call."""
    calls = {}

    def lookup(name):
        verdict = table[name]
        if isinstance(verdict, list):
            verdict = verdict[min(calls.get(name, 0), len(verdict) - 1)]
        calls[name] = calls.get(name, 0) + 1
        if verdict in ('missing', 'error'):
            return verdict, None
        return 'found', {'character': {'name': verdict}}
    return lookup


class TestDedupe:

    def test_keeps_first_case_insensitive(self):
        assert dedupe(["Sleeping Booty", "Krod", "sleeping booty"]) == ["Sleeping Booty", "Krod"]


class TestClean:

    def test_removes_confirmed_missing(self):
        names = ["A", "B", "C", "D", "Gone"]
        lookup = make_lookup({"A": "A", "B": "B", "C": "C", "D": "D", "Gone": "missing"})
        result = clean(names, lookup)
        assert result['trolls'] == ["A", "B", "C", "D"]
        assert result['removed'] == ["Gone"]

    def test_never_removes_on_api_error(self):
        lookup = make_lookup({"A": "A", "Flaky": "error"})
        result = clean(["A", "Flaky"], lookup)
        assert result['trolls'] == ["A", "Flaky"]
        assert result['removed'] == []
        assert result['errors'] == ["Flaky"]

    def test_keeps_name_that_is_found_on_recheck(self):
        names = ["A", "B", "C", "D", "Blip"]
        lookup = make_lookup({"A": "A", "B": "B", "C": "C", "D": "D", "Blip": ["missing", "Blip"]})
        result = clean(names, lookup)
        assert "Blip" in result['trolls']
        assert result['removed'] == []

    def test_keeps_name_that_errors_on_recheck(self):
        names = ["A", "B", "C", "D", "Blip"]
        lookup = make_lookup({"A": "A", "B": "B", "C": "C", "D": "D", "Blip": ["missing", "error"]})
        result = clean(names, lookup)
        assert "Blip" in result['trolls']

    def test_aborts_when_too_many_missing(self):
        lookup = make_lookup({"A": "missing", "B": "missing", "C": "C"})
        result = clean(["A", "B", "C"], lookup)
        assert result['trolls'] is None
        assert result['aborted']

    def test_applies_renames_and_case_fixes(self):
        lookup = make_lookup({"old name": "New Name", "krod": "Krod"})
        result = clean(["old name", "krod"], lookup)
        assert result['trolls'] == ["New Name", "Krod"]
        assert ("old name", "New Name") in result['renamed']

    def test_rename_colliding_with_existing_entry_is_deduped(self):
        lookup = make_lookup({"Current": "Current", "Former": "Current"})
        result = clean(["Current", "Former"], lookup)
        assert result['trolls'] == ["Current"]

    def test_drops_duplicates(self):
        lookup = make_lookup({"Krod": "Krod"})
        result = clean(["Krod", "krod"], lookup)
        assert result['trolls'] == ["Krod"]
        assert result['duplicates'] == 1


class TestFileIO:

    def test_round_trip(self, tmp_path):
        path = tmp_path / "trolls.json"
        save_trolls(["Ruslex", "Rodlex"], str(path))
        assert load_trolls(str(path)) == ["Ruslex", "Rodlex"]
        assert json.loads(path.read_text()) == ["Ruslex", "Rodlex"]


class TestLookupCharacter:

    @patch('tibia_api.fetch_with_status')
    def test_found(self, mock_fetch):
        mock_fetch.return_value = ({"character": {"character": {"name": "Krod"}}}, 200)
        status, character = lookup_character("krod")
        assert status == 'found'
        assert character['character']['name'] == "Krod"

    @patch('tibia_api.fetch_with_status')
    def test_http_404_is_missing(self, mock_fetch):
        mock_fetch.return_value = (None, 404)
        assert lookup_character("Nobody")[0] == 'missing'

    @patch('tibia_api.fetch_with_status')
    def test_api_status_404_is_missing(self, mock_fetch):
        mock_fetch.return_value = ({"information": {"status": {"http_code": 404}}}, 200)
        assert lookup_character("Nobody")[0] == 'missing'

    @patch('tibia_api.fetch_with_status')
    def test_empty_name_is_missing(self, mock_fetch):
        mock_fetch.return_value = ({"character": {"character": {"name": ""}}}, 200)
        assert lookup_character("Nobody")[0] == 'missing'

    @patch('tibia_api.fetch_with_status')
    def test_persistent_502_is_error(self, mock_fetch):
        mock_fetch.return_value = (None, None)
        assert lookup_character("Sir kurogane")[0] == 'error'

    @patch('tibia_api.fetch_with_status')
    def test_other_http_error_is_error(self, mock_fetch):
        mock_fetch.return_value = (None, 403)
        assert lookup_character("Someone")[0] == 'error'
