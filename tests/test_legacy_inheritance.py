"""test_legacy_inheritance.py -- Layer 1 (inheritance table) and Layer 2 (echo
flags) coverage for engine/legacy.py, per docs/LEGACY_SYSTEM_OUTLINE.md.
"""
from __future__ import annotations
import json
import os
import unittest
from unittest.mock import patch

from engine.stats import create_starter_fixer, STAT_SPEC
from engine import legacy
from pipeline.lint_content import RESOLVER_ENDINGS


class TestInheritanceTableShape(unittest.TestCase):
    """Static sanity checks on data/legacy_inheritance.json."""

    @classmethod
    def setUpClass(cls):
        with open(legacy.INHERITANCE_PATH, "r", encoding="utf-8") as fh:
            cls.table = json.load(fh)
        cast_path = os.path.join(legacy.DATA_DIR, "cast.json")
        with open(cast_path, "r", encoding="utf-8") as fh:
            cls.cast_names = {c["name"] for c in json.load(fh).get("cast", [])}

    def test_every_key_is_a_resolver_ending(self):
        for ending_id in self.table:
            self.assertIn(ending_id, RESOLVER_ENDINGS)

    def test_every_stat_key_is_in_stat_spec(self):
        for ending_id, entry in self.table.items():
            for stat in entry.get("stat_deltas", {}):
                self.assertIn(stat, STAT_SPEC, f"{ending_id}: unknown stat {stat!r}")

    def test_every_delta_within_cap(self):
        for ending_id, entry in self.table.items():
            for group in ("stat_deltas", "faction_deltas", "rel_deltas"):
                for key, delta in entry.get(group, {}).items():
                    self.assertLessEqual(abs(delta), 8, f"{ending_id}.{group}[{key!r}] = {delta}")

    def test_every_rel_key_is_a_cast_name(self):
        for ending_id, entry in self.table.items():
            for name in entry.get("rel_deltas", {}):
                self.assertIn(name, self.cast_names, f"{ending_id}: {name!r} not in cast.json")


class TestApplyLegacyInheritance(unittest.TestCase):
    def test_syndicate_ledger_lowers_kael_satisfaction_on_starter_fixer(self):
        stub = {
            "cycles": 1,
            "endings_seen": {"TERMINAL_syndicate_ledger": 1},
            "last_ending": "TERMINAL_syndicate_ledger",
        }
        with patch.object(legacy, "load", return_value=stub):
            c = create_starter_fixer()
            before = c.relationships["Kael (Broker)"].satisfaction
            applied = legacy.apply_legacy_inheritance(c)

        self.assertTrue(applied)
        self.assertLess(c.relationships["Kael (Broker)"].satisfaction, before)


class TestSimBotStaysLegacyFree(unittest.TestCase):
    def test_sim_bot_never_calls_legacy(self):
        sim_bot_path = os.path.join(os.path.dirname(__file__), "sim_bot.py")
        with open(sim_bot_path, "r", encoding="utf-8") as fh:
            source = fh.read()
        self.assertNotIn("legacy", source.lower())


if __name__ == "__main__":
    unittest.main()
