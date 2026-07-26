"""test_ambient.py -- Coverage for engine/ambient.py's state-aware prose layer."""
from __future__ import annotations
import unittest

from engine.stats import Character, create_starter_fixer
from engine.ambient import morning_report, steward_ledger_line, MARA_SILENCE_ONSET


class TestMorningReport(unittest.TestCase):
    def _healthy_character(self) -> Character:
        c = Character()
        c.set("Meaning", 90.0)
        c.set("Physical_Integrity", 95.0)
        c.set("Heat", 0.0)
        c.set("Substance_Reliance", 0.0)
        c.days_since_use = 0
        return c

    def test_no_signals_for_a_healthy_character(self):
        self.assertEqual(morning_report(self._healthy_character()), [])

    def test_caps_at_two_lines_even_with_many_active_signals(self):
        c = self._healthy_character()
        c.set("Physical_Integrity", 5.0)     # severe
        c.set("Heat", 90.0)                  # severe
        c.set("Meaning", 5.0)                # severe
        c.set("Substance_Reliance", 90.0)
        c.days_since_use = 10                # severe withdrawal
        report = morning_report(c)
        self.assertEqual(len(report), 2)

    def test_higher_urgency_signal_wins_over_earlier_listed_signal(self):
        c = self._healthy_character()
        c.set("Physical_Integrity", 60.0)   # mild tier (urgency 1)
        c.set("Heat", 90.0)                 # severe tier (urgency 5), listed after PI internally
        report = morning_report(c)
        self.assertEqual(len(report), 2)
        # Heat is more urgent than the mild physical ache, so it leads despite
        # physical being evaluated first.
        self.assertIn("burning", report[0].lower())

    def test_mara_signal_requires_onset_days_of_silence(self):
        c = create_starter_fixer()
        c.set("Meaning", 90.0)
        c.set("Physical_Integrity", 95.0)
        c.set("Heat", 0.0)
        c.set("Substance_Reliance", 0.0)

        c.day = MARA_SILENCE_ONSET - 1
        self.assertEqual(morning_report(c), [])

        c.day = MARA_SILENCE_ONSET + 5
        report = morning_report(c)
        self.assertEqual(len(report), 1)
        self.assertIn("Mara", report[0])

    def test_no_mara_signal_without_a_mara_relationship(self):
        c = self._healthy_character()
        c.day = 999
        self.assertEqual(morning_report(c), [])


class TestStewardLedgerLine(unittest.TestCase):
    def test_empty_summary_reports_no_prior_entry(self):
        self.assertIn("no prior entry", steward_ledger_line(Character(), None).lower())
        self.assertIn("no prior entry", steward_ledger_line(Character(), {}).lower())

    def test_clocks_expired_takes_priority(self):
        c = Character()
        c.day = 6
        summary = {
            "clocks_expired": ["loan_shark"],
            "overnight": {"Heat": 20.0},
            "withdrawal": True,
            "stress": 50.0,
        }
        line = steward_ledger_line(c, summary)
        self.assertIn("loan shark", line)
        self.assertIn("deadline closed", line)
        self.assertIn("Day 5", line)

    def test_overnight_cites_the_largest_magnitude_stat(self):
        c = Character()
        c.day = 6
        summary = {
            "overnight": {"Heat": 2.0, "Physical_Integrity": -12.5},
            "withdrawal": True,
            "stress": 50.0,
        }
        line = steward_ledger_line(c, summary)
        self.assertIn("your body", line)
        self.assertIn("down", line)
        self.assertIn("12.5", line)

    def test_withdrawal_flag_used_when_no_deltas_recorded(self):
        c = Character()
        c.day = 6
        summary = {"overnight": {}, "withdrawal": True, "stress": 12.0}
        line = steward_ledger_line(c, summary)
        self.assertIn("dependency event", line)

    def test_stress_is_the_final_fallback(self):
        c = Character()
        c.day = 6
        summary = {"overnight": {}, "withdrawal": False, "stress": 33.4}
        line = steward_ledger_line(c, summary)
        self.assertIn("33.4", line)


if __name__ == "__main__":
    unittest.main()
