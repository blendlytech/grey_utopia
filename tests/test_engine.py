"""test_engine.py -- Comprehensive unit test suite for GREY UTOPIA simulation engine."""
import unittest
import math
import os
import json
import random

from engine import steward
from engine.stats import Character, create_starter_fixer, STAT_SPEC, clamp
from engine.decay import (
    update_mood, relationship_retention, dose_effect,
    escalate_tolerance, recover_tolerance, withdrawal_severity,
    overdose_probability, end_of_day_decay
)
from engine.events import Event, Choice, Insert, load_events, eval_conditions
from engine.selector import (
    select_event, effective_weight, chain_depth, index_library,
    eligible_pool, is_ambient, on_shelf, district_for_slot,
    DEPTH_SCALE, MAX_DEPTH, DEADLINE_BONUS, AMBIENT_TAGS, AMBIENT_SLOTS_PER_DAY
)
from engine.districts import (
    apply_placements, auto_placement, clear_placements, district_hint,
    district_ids, district_name, load_districts, shelf_open_count
)
from engine.resolver import (
    choice_probability, resolve_choice, check_endings,
    eligible_choices, apply_dose, build_epilogue,
    desperation_edge, apply_rest, EDGE_STEP, EDGE_CAP, REST_DELTAS,
    MD_COLLAPSE_DAYS, SWITCH_SETTLE_DAY,
    SMALL_LIFE_SETTLE_DAY, SMALL_LIFE_MIN_MEANING, SMALL_LIFE_MIN_BODY
)


class TestStats(unittest.TestCase):
    def test_stat_clamping(self):
        c = Character()
        c.set("Wealth", -500)
        self.assertEqual(c.get("Wealth"), 0.0)

        c.set("Mental_Decay", 150)
        self.assertEqual(c.get("Mental_Decay"), 100.0)

        c.set("Tolerance", 15.0)
        self.assertEqual(c.get("Tolerance"), 10.0)

    def test_relationship_reinforce(self):
        c = create_starter_fixer()
        initial_sat = c.relationships["Mara (Sister)"].satisfaction
        initial_strength = c.relationships["Mara (Sister)"].strength

        c.reinforce("Mara (Sister)", 15.0)
        self.assertGreater(c.relationships["Mara (Sister)"].satisfaction, initial_sat)
        self.assertGreater(c.relationships["Mara (Sister)"].strength, initial_strength)

    def test_json_serialization(self):
        c = create_starter_fixer()
        c.apply_deltas({"Wealth": 250, "Heat": 15})
        json_str = c.to_json()
        data = json.loads(json_str)

        c2 = Character.from_dict(data)
        self.assertEqual(c2.get("Wealth"), c.get("Wealth"))
        self.assertEqual(c2.get("Heat"), c.get("Heat"))
        self.assertIn("Mara (Sister)", c2.relationships)


class TestDecayMath(unittest.TestCase):
    def test_ema_mood_smoothing(self):
        md = 20.0
        stress = 80.0
        new_md = update_mood(md, stress, alpha=0.30)
        self.assertAlmostEqual(new_md, 38.0, places=2)

    def test_ebbinghaus_retention(self):
        sat_base = 80.0
        strength = 10.0
        # t = 0
        self.assertAlmostEqual(relationship_retention(sat_base, 0, strength), 80.0, places=2)
        # t = 10 (crosses e^-1 factor = ~29.43)
        ret_10 = relationship_retention(sat_base, 10, strength)
        self.assertAlmostEqual(ret_10, 80.0 * math.exp(-1), places=2)

    def test_dose_effect_hill_curve(self):
        # Zero tolerance
        eff_0 = dose_effect(10.0, 0.0)
        self.assertAlmostEqual(eff_0, 50.0, places=2)

        # Tolerance = 1.0 (ED50 doubles to 20)
        eff_1 = dose_effect(10.0, 1.0)
        self.assertAlmostEqual(eff_1, 100.0 * 10 / 30.0, places=2)
        self.assertLess(eff_1, eff_0)

    def test_overdose_probability(self):
        p_normal = overdose_probability(10.0, 5.0, 90.0)
        self.assertLess(p_normal, 0.05)

        p_dangerous = overdose_probability(80.0, 90.0, 10.0)
        self.assertGreater(p_dangerous, 0.25)

        p_lethal = overdose_probability(150.0, 90.0, 5.0)
        self.assertGreater(p_lethal, 0.80)


class TestResolverAndEndings(unittest.TestCase):
    def test_choice_probability_bounds(self):
        ch = Choice(
            id="test",
            text="test choice",
            prob={"base": 0.5, "mods": [{"stat": "Recklessness", "coef": 0.01}]}
        )
        c = Character()
        c.set("Recklessness", 100.0)
        p = choice_probability(ch, c)
        self.assertLessEqual(p, 0.98)
        self.assertGreaterEqual(p, 0.02)

    def test_institutionalized_ending(self):
        c = Character()
        c.md_high_streak = MD_COLLAPSE_DAYS
        ending = check_endings(c)
        self.assertEqual(ending, "TERMINAL_institutionalized")

    def test_institutionalized_needs_streak_to_outlast_the_crisis(self):
        """One bad week is a breakdown, not a diagnosis -- the streak must hold."""
        c = Character()
        c.md_high_streak = MD_COLLAPSE_DAYS - 1
        self.assertIsNone(check_endings(c))

    def test_switch_is_carried_before_it_becomes_an_ending(self):
        """Holding the off-switch is a thing in a drawer until it outlasts you."""
        c = Character()
        c.set("Meaning", 60.0)   # keep the long-grey road out of this test
        c.flags.add("keeper_of_switch")
        c.day = SWITCH_SETTLE_DAY - 1
        self.assertIsNone(check_endings(c))
        c.day = SWITCH_SETTLE_DAY
        self.assertEqual(check_endings(c), "NEUTRAL_keeper_of_the_switch")

    def test_switch_distributed_settles_the_same_way(self):
        c = Character()
        c.set("Meaning", 60.0)
        c.flags.add("switch_distributed")
        c.day = SWITCH_SETTLE_DAY
        self.assertEqual(check_endings(c), "NEUTRAL_keeper_of_the_switch")

    def test_offgrid_ending(self):
        c = Character()
        c.flags.add("crossed_wire")
        ending = check_endings(c)
        self.assertEqual(ending, "GOOD_offgrid_escape")

    def test_offgrid_ending_requires_the_crossing(self):
        # exit_ready alone must never win -- only surviving The Crossing does.
        c = Character()
        c.day = 30
        c.set("Meaning", 90.0)
        c.set("Family_Friction", 5.0)
        c.set("Substance_Reliance", 5.0)
        c.set("Heat", 5.0)
        c.flags.add("exit_ready")
        self.assertIsNone(check_endings(c))


class TestConditionsAndRequires(unittest.TestCase):
    def test_item_faction_relationship_conditions(self):
        c = create_starter_fixer()
        c.add_item("burner_deck")
        c.factions["Resistance"] = 25.0
        self.assertTrue(eval_conditions({"all": [{"item": "burner_deck"}]}, c))
        self.assertFalse(eval_conditions({"all": [{"item": "signal_ghost"}]}, c))
        self.assertTrue(eval_conditions({"all": [{"item": "signal_ghost", "value": False}]}, c))
        self.assertTrue(eval_conditions({"all": [{"faction": "Resistance", "op": ">=", "value": 20}]}, c))
        self.assertTrue(eval_conditions(
            {"all": [{"relationship": "Mara (Sister)", "op": ">=", "value": 70}]}, c))
        self.assertFalse(eval_conditions(
            {"all": [{"relationship": "Echo (Resistance)", "op": ">=", "value": 1}]}, c))

    def test_clock_conditions(self):
        c = Character()
        self.assertFalse(eval_conditions({"all": [{"clock": "debt", "op": "<=", "value": 5}]}, c))
        self.assertTrue(eval_conditions({"all": [{"clock": "debt", "running": False}]}, c))
        c.start_clock("debt", 3)
        self.assertTrue(eval_conditions({"all": [{"clock": "debt", "op": "<=", "value": 5}]}, c))
        self.assertTrue(eval_conditions({"all": [{"clock": "debt", "running": True}]}, c))

    def test_requires_filters_choices(self):
        rich_only = Choice(id="a", text="a", prob={"base": 1.0},
                           requires={"all": [{"stat": "Wealth", "op": ">=", "value": 10000}]})
        always = Choice(id="b", text="b", prob={"base": 1.0})
        c = Character()
        visible = eligible_choices([rich_only, always], c)
        self.assertEqual([ch.id for ch in visible], ["b"])
        c.set("Wealth", 20000)
        visible = eligible_choices([rich_only, always], c)
        self.assertEqual([ch.id for ch in visible], ["a", "b"])


class TestEventInserts(unittest.TestCase):
    def test_compose_body_appends_matching_inserts_in_order(self):
        c = Character()
        c.set("Heat", 50.0)
        ev = Event(
            id="ev1", title="t", body="Base body.",
            inserts=[
                Insert(text="Low heat line.", when={"all": [{"stat": "Heat", "op": "<", "value": 10}]}),
                Insert(text="High heat line.", when={"all": [{"stat": "Heat", "op": ">=", "value": 10}]}),
                Insert(text="Always shown."),
            ]
        )
        composed = ev.compose_body(c)
        self.assertEqual(composed, "Base body.\n\nHigh heat line.\n\nAlways shown.")

    def test_compose_body_with_no_active_inserts_returns_bare_body(self):
        c = Character()
        ev = Event(id="ev2", title="t", body="Just this.",
                   inserts=[Insert(text="never", when={"all": [{"flag": "nope"}]})])
        self.assertEqual(ev.compose_body(c), "Just this.")

    def _minimal_choices(self):
        return [
            {"id": "a", "text": "a", "prob": {"base": 1.0}},
            {"id": "b", "text": "b", "prob": {"base": 1.0}},
            {"id": "c", "text": "c", "prob": {"base": 1.0}},
        ]

    def test_load_events_parses_inserts(self):
        payload = {"events": [{
            "id": "ins_ev", "title": "T", "body": "B",
            "inserts": [
                {"text": "conditional", "when": {"all": [{"stat": "Wealth", "op": ">=", "value": 100}]}},
                {"text": "unconditional"},
            ],
            "choices": self._minimal_choices(),
        }]}
        events = load_events(payload)
        self.assertEqual(len(events[0].inserts), 2)
        self.assertEqual(events[0].inserts[0].text, "conditional")
        self.assertEqual(events[0].inserts[1].when, {})

    def test_load_events_rejects_insert_missing_text(self):
        payload = {"events": [{
            "id": "bad1", "title": "T", "body": "B",
            "inserts": [{"when": {}}],
            "choices": self._minimal_choices(),
        }]}
        with self.assertRaises(AssertionError):
            load_events(payload)

    def test_load_events_rejects_insert_with_invalid_op(self):
        payload = {"events": [{
            "id": "bad2", "title": "T", "body": "B",
            "inserts": [{"text": "x", "when": {"all": [{"stat": "Heat", "op": "lte", "value": 5}]}}],
            "choices": self._minimal_choices(),
        }]}
        with self.assertRaises(AssertionError):
            load_events(payload)

    def test_load_events_rejects_insert_with_non_numeric_day(self):
        payload = {"events": [{
            "id": "bad3", "title": "T", "body": "B",
            "inserts": [{"text": "x", "when": {"all": [{"day": "soon"}]}}],
            "choices": self._minimal_choices(),
        }]}
        with self.assertRaises(AssertionError):
            load_events(payload)


class TestClocksAndDose(unittest.TestCase):
    def test_clock_ticks_and_expires(self):
        import random as _r
        c = Character()
        c.start_clock("syndicate_consignment", 2)
        end_of_day_decay(c, stress_today=10.0)
        self.assertEqual(c.clocks["syndicate_consignment"], 1)
        end_of_day_decay(c, stress_today=10.0)
        self.assertNotIn("syndicate_consignment", c.clocks)
        self.assertIn("clock_syndicate_consignment_expired", c.flags)
        c.start_clock("syndicate_consignment", 5)   # restarting clears the expiry flag
        c.stop_clock("syndicate_consignment")
        self.assertNotIn("clock_syndicate_consignment_expired", c.flags)

    def test_dose_accumulates_and_feeds_decay(self):
        import random as _r
        rng = _r.Random(1)
        c = Character()
        c.days_since_use = 5
        apply_dose(c, 10.0, rng)
        self.assertEqual(c.pending_dose, 10.0)
        end_of_day_decay(c, stress_today=10.0)
        self.assertEqual(c.days_since_use, 0)            # the day counted as a use day
        self.assertGreater(c.get("Tolerance"), 0.0)      # tolerance escalated
        self.assertEqual(c.pending_dose, 0.0)            # dose consumed

    def test_overdose_warning_then_death(self):
        import random as _r
        c = Character()
        c.set("Substance_Reliance", 95.0)
        c.set("Physical_Integrity", 5.0)
        c.set("Tolerance", 10.0)

        class AlwaysOD:
            def random(self):
                return 0.0
        outcome1 = apply_dose(c, 80.0, AlwaysOD())
        self.assertEqual(outcome1, "collapse")
        self.assertIn("near_overdose", c.flags)
        outcome2 = apply_dose(c, 80.0, AlwaysOD())
        self.assertEqual(outcome2, "death")
        self.assertEqual(check_endings(c), "TERMINAL_overdose_death")

    def test_naloxinol_patch_saves_once(self):
        c = Character()
        c.flags.add("near_overdose")
        c.add_item("naloxinol_patch")

        class AlwaysOD:
            def random(self):
                return 0.0
        outcome = apply_dose(c, 80.0, AlwaysOD())
        self.assertEqual(outcome, "collapse")
        self.assertFalse(c.has_item("naloxinol_patch"))


class TestResolverEffects(unittest.TestCase):
    def test_rel_deltas_and_rel_add(self):
        import random as _r
        c = create_starter_fixer()
        ch = Choice(id="x", text="x", prob={"base": 1.0}, success={
            "rel_deltas": {"Mara (Sister)": 10, "Vint (Informant)": -20},
            "rel_add": [{"name": "Echo (Resistance)", "satisfaction": 35}]
        })
        before_mara = c.relationships["Mara (Sister)"].satisfaction
        before_vint = c.relationships["Vint (Informant)"].satisfaction
        resolve_choice(ch, c, _r.Random(0))
        self.assertGreater(c.relationships["Mara (Sister)"].satisfaction, before_mara)
        self.assertLess(c.relationships["Vint (Informant)"].satisfaction, before_vint)
        self.assertIn("Echo (Resistance)", c.relationships)

    def test_clock_effects_from_branch(self):
        import random as _r
        c = Character()
        start = Choice(id="s", text="s", prob={"base": 1.0},
                       success={"clocks_start": {"loan_shark": 8}})
        resolve_choice(start, c, _r.Random(0))
        self.assertEqual(c.clocks["loan_shark"], 8)
        stop = Choice(id="t", text="t", prob={"base": 1.0},
                      success={"clocks_stop": ["loan_shark"]})
        resolve_choice(stop, c, _r.Random(0))
        self.assertNotIn("loan_shark", c.clocks)

    def test_new_endings(self):
        for flag, ending in [
            ("flag_syndicate_execution", "TERMINAL_syndicate_ledger"),
            ("became_ferryman", "NEUTRAL_the_open_door"),
            ("shepherd_accepted", "NEUTRAL_stewards_shepherd"),
        ]:
            c = Character()
            c.flags.add(flag)
            self.assertEqual(check_endings(c), ending, flag)

    def _small_life_character(self) -> Character:
        """A run that chose the workshop life and is still living it."""
        c = Character()
        c.flags.add("chose_small_life")
        c.day = SMALL_LIFE_SETTLE_DAY
        c.set("Meaning", SMALL_LIFE_MIN_MEANING + 5.0)
        c.set("Physical_Integrity", SMALL_LIFE_MIN_BODY + 20.0)
        return c

    def test_small_life_ending_when_the_life_held(self):
        self.assertEqual(check_endings(self._small_life_character()),
                         "GOOD_small_real_things")

    def test_small_life_must_be_lived_before_it_resolves(self):
        c = self._small_life_character()
        c.day = SMALL_LIFE_SETTLE_DAY - 1
        self.assertNotEqual(check_endings(c), "GOOD_small_real_things")

    def test_small_life_does_not_resolve_once_it_hollows_out(self):
        """Choosing the quiet life is not a shield; it has to stay worth living."""
        c = self._small_life_character()
        c.set("Meaning", SMALL_LIFE_MIN_MEANING - 5.0)
        self.assertNotEqual(check_endings(c), "GOOD_small_real_things")

        c = self._small_life_character()
        c.set("Physical_Integrity", SMALL_LIFE_MIN_BODY - 5.0)
        self.assertNotEqual(check_endings(c), "GOOD_small_real_things")

    def test_epilogue_composition(self):
        c = create_starter_fixer()
        c.flags.add("mara_coming")
        ending_data = {
            "epilogues": [
                {"when": {"all": [{"flag": "mara_coming"}]}, "text": "Together."},
                {"when": {"all": [{"flag": "left_mara_behind"}]}, "text": "Alone."},
            ]
        }
        self.assertEqual(build_epilogue(ending_data, c), ["Together."])


class TestDesperationEdgeAndRest(unittest.TestCase):
    def _gamble(self, base=0.5):
        return Choice(id="g", text="g", prob={"base": base, "mods": []},
                      success={"text": "ok"}, failure={"text": "no"})

    def test_edge_grows_with_failures_and_caps(self):
        c = Character()
        self.assertEqual(desperation_edge(c), 0.0)
        c.fail_streak = 2
        self.assertAlmostEqual(desperation_edge(c), 2 * EDGE_STEP)
        c.fail_streak = 50
        self.assertAlmostEqual(desperation_edge(c), EDGE_CAP)

    def test_edge_raises_gamble_probability_only(self):
        c = Character()
        gamble = self._gamble(0.5)
        safe = Choice(id="s", text="s", prob={"base": 0.5, "mods": []},
                      success={"text": "ok"})   # no failure branch: not a gamble
        base_p = choice_probability(gamble, c)
        c.fail_streak = 3
        self.assertAlmostEqual(choice_probability(gamble, c), base_p + EDGE_CAP)
        self.assertAlmostEqual(choice_probability(safe, c), 0.5)

    def test_streak_updates_on_genuine_rolls_only(self):
        import random as _r

        class AlwaysFail:
            def random(self):
                return 0.999
        c = Character()
        resolve_choice(self._gamble(0.5), c, AlwaysFail())
        resolve_choice(self._gamble(0.5), c, AlwaysFail())
        self.assertEqual(c.fail_streak, 2)

        # A safe choice resolves without touching the streak
        safe = Choice(id="s", text="s", prob={"base": 1.0}, success={"text": "ok"})
        resolve_choice(safe, c, _r.Random(0))
        self.assertEqual(c.fail_streak, 2)

        class AlwaysWin:
            def random(self):
                return 0.0
        resolve_choice(self._gamble(0.5), c, AlwaysWin())
        self.assertEqual(c.fail_streak, 0)

    def test_fail_streak_survives_serialization(self):
        c = Character()
        c.fail_streak = 2
        c2 = Character.from_dict(json.loads(c.to_json()))
        self.assertEqual(c2.fail_streak, 2)

    def test_apply_rest_recovers_and_costs_meaning(self):
        import random as _r
        c = Character()
        c.set("Physical_Integrity", 50.0)
        c.set("Mental_Decay", 60.0)
        c.set("Heat", 30.0)
        before_meaning = c.get("Meaning")
        text = apply_rest(c, _r.Random(0))
        self.assertTrue(isinstance(text, str) and text)
        self.assertEqual(c.get("Physical_Integrity"), 50.0 + REST_DELTAS["Physical_Integrity"])
        self.assertEqual(c.get("Mental_Decay"), 60.0 + REST_DELTAS["Mental_Decay"])
        self.assertEqual(c.get("Heat"), 30.0 + REST_DELTAS["Heat"])
        self.assertEqual(c.get("Meaning"), before_meaning + REST_DELTAS["Meaning"])


class TestChainDepthScheduling(unittest.TestCase):
    """Arc steps are scheduled on how deep a chain they sit in, not on flag count alone."""

    def _library(self):
        def granter(eid, flag, requires=None):
            return Event(
                id=eid, title=eid, body="b", weight=1.0,
                preconditions={"all": [{"flag": f} for f in (requires or [])]},
                choices=[Choice(id="c", text="c", prob={"base": 1.0},
                                success={"flags_set": [flag]})],
            )

        filler = Event(id="filler", title="f", body="b", weight=1.0)
        origin_gated = Event(
            id="origin_gated", title="o", body="b", weight=1.0,
            # 'origin_auditor' is handed out at character creation, not by a
            # storylet, so it buys no momentum.
            preconditions={"all": [{"flag": "origin_auditor"}]},
            choices=[Choice(id="c", text="c", prob={"base": 1.0})],
        )
        self_gated = Event(
            id="self_gated", title="s", body="b", weight=1.0,
            preconditions={"all": [{"flag": "loop"}]},
            choices=[Choice(id="c", text="c", prob={"base": 1.0},
                            success={"flags_set": ["loop"]})],
        )
        return [
            filler, origin_gated, self_gated,
            granter("step1", "step1_done"),
            granter("step2", "step2_done", ["step1_done"]),
            granter("step3", "step3_done", ["step1_done", "step2_done"]),
            granter("step4", "step4_done", ["step1_done", "step2_done", "step3_done"]),
            granter("step5", "step5_done",
                    ["step1_done", "step2_done", "step3_done", "step4_done"]),
        ]

    def _by_id(self, events):
        return {e.id: e for e in events}

    def test_chain_depth_counts_only_event_granted_flags(self):
        events = self._library()
        index_library(events)
        ev = self._by_id(events)
        self.assertEqual(chain_depth(ev["filler"]), 0)
        self.assertEqual(chain_depth(ev["origin_gated"]), 0)   # not granted by any storylet
        self.assertEqual(chain_depth(ev["self_gated"]), 0)     # grants its own gate
        self.assertEqual(chain_depth(ev["step1"]), 0)
        self.assertEqual(chain_depth(ev["step2"]), 1)
        self.assertEqual(chain_depth(ev["step3"]), 2)
        self.assertEqual(chain_depth(ev["step4"]), 3)
        self.assertEqual(chain_depth(ev["step5"]), MAX_DEPTH)  # capped

    def test_deep_steps_outweigh_depth_zero_filler(self):
        events = self._library()
        index_library(events)
        ev = self._by_id(events)
        c = Character()
        c.flags.update({"step1_done", "step2_done", "step3_done", "step4_done"})
        base = effective_weight(ev["filler"], c)
        weights = [effective_weight(ev[f"step{i}"], c) for i in range(1, 5)]
        self.assertEqual(weights[0], base)
        for shallower, deeper in zip(weights, weights[1:]):
            self.assertGreater(deeper, shallower)
        self.assertAlmostEqual(weights[3], base * DEPTH_SCALE ** 3)

    def test_deadline_pressure_survives_independent_of_depth(self):
        c = Character()
        c.start_clock("debt", 2)
        urgent = Event(id="urgent", title="u", body="b", weight=1.0,
                       preconditions={"all": [{"clock": "debt", "op": "<=", "value": 3}]})
        index_library([urgent])
        self.assertEqual(chain_depth(urgent), 0)
        self.assertAlmostEqual(effective_weight(urgent, c), 1.0 + DEADLINE_BONUS)

    def test_select_event_indexes_the_deck_it_is_handed(self):
        import random as _r
        events = self._library()
        index_library([])            # stale index: nothing is event-granted
        c = Character()
        c.flags.update({"step1_done", "step2_done"})
        select_event(events, c, day=1, rng=_r.Random(0))
        self.assertEqual(chain_depth(self._by_id(events)["step3"]), 2)


class TestAmbientQuota(unittest.TestCase):
    """Ambient filler is budgeted per day so arc first-links can win a draw."""

    def _event(self, eid: str, tags: list) -> Event:
        return Event(id=eid, title=eid, body="b", weight=1.0, tags=tags,
                     choices=[Choice(id="c", text="c", prob={"base": 1.0})])

    def _mixed(self):
        return [
            self._event("noise", ["ambient"]),
            self._event("chatter", ["micro"]),
            self._event("thread", ["arc"]),
        ]

    def _ids(self, pool):
        return {e.id for e in pool}

    def test_is_ambient_covers_both_budgeted_tags(self):
        self.assertEqual(AMBIENT_TAGS, frozenset({"ambient", "micro"}))
        self.assertTrue(is_ambient(self._event("a", ["ambient"])))
        self.assertTrue(is_ambient(self._event("m", ["micro", "vice"])))
        self.assertFalse(is_ambient(self._event("j", ["job", "arc"])))

    def test_unbudgeted_pool_keeps_everything(self):
        pool = eligible_pool(self._mixed(), Character(), day=1)
        self.assertEqual(self._ids(pool), {"noise", "chatter", "thread"})

    def test_remaining_budget_keeps_ambient_in_the_draw(self):
        pool = eligible_pool(self._mixed(), Character(), day=1, ambient_budget=1)
        self.assertEqual(self._ids(pool), {"noise", "chatter", "thread"})

    def test_budget_helper_tracks_the_shipped_setting(self):
        """One switch drives every caller, so main/server/sim_bot cannot disagree."""
        import engine.selector as sel
        original = sel.AMBIENT_SLOTS_PER_DAY
        try:
            sel.AMBIENT_SLOTS_PER_DAY = None
            self.assertIsNone(sel.ambient_budget_for(0))
            self.assertIsNone(sel.ambient_budget_for(3))
            sel.AMBIENT_SLOTS_PER_DAY = 1
            self.assertEqual(sel.ambient_budget_for(0), 1)
            self.assertEqual(sel.ambient_budget_for(1), 0)
            self.assertEqual(sel.ambient_budget_for(2), -1)   # spent, and then some
        finally:
            sel.AMBIENT_SLOTS_PER_DAY = original

    def test_quota_ships_disabled(self):
        """Measured decision, not an oversight -- see the note in engine/selector.py.
        Flipping this to an int is a balance change and requires a pargate run."""
        self.assertIsNone(AMBIENT_SLOTS_PER_DAY)

    def test_spent_budget_drops_ambient_and_micro(self):
        pool = eligible_pool(self._mixed(), Character(), day=1, ambient_budget=0)
        self.assertEqual(self._ids(pool), {"thread"})

    def test_spent_budget_falls_back_rather_than_burning_the_slot(self):
        """The quota must never starve the day. Early game is the live trigger:
        almost everything eligible on day 1 carries an ambient tag, so a strict
        filter would hand back None and silently eat the player's action."""
        ambient_only = [self._event("noise", ["ambient"]), self._event("chatter", ["micro"])]
        pool = eligible_pool(ambient_only, Character(), day=1, ambient_budget=0)
        self.assertEqual(self._ids(pool), {"noise", "chatter"})

        import random as _r
        picked = select_event(ambient_only, Character(), day=1, rng=_r.Random(0),
                              ambient_budget=0)
        self.assertIsNotNone(picked)

    def test_exclusions_still_apply_under_the_quota(self):
        pool = eligible_pool(self._mixed(), Character(), day=1,
                             exclude_ids={"thread"}, ambient_budget=0)
        # 'thread' is excluded and the ambient pair is over budget: falling back
        # beats returning nothing, but the exclusion is never overridden.
        self.assertEqual(self._ids(pool), {"noise", "chatter"})

    def test_select_event_honours_a_spent_budget(self):
        import random as _r
        for seed in range(8):
            picked = select_event(self._mixed(), Character(), day=1,
                                  rng=_r.Random(seed), ambient_budget=0)
            self.assertEqual(picked.id, "thread")


class TestDistrictShelves(unittest.TestCase):
    """A1: a placed action slot draws a district's shelf, not the whole deck."""

    def _event(self, eid: str, tags: list, district=None) -> Event:
        return Event(id=eid, title=eid, body="b", weight=1.0, tags=tags, district=district,
                     choices=[Choice(id="c", text="c", prob={"base": 1.0})])

    def _mixed(self):
        return [
            self._event("chain_a", ["arc"], district="the_archive"),
            self._event("chain_b", ["arc"], district="the_archive"),
            self._event("elsewhere", ["arc"], district="the_terraces"),
            self._event("noise", ["ambient"]),
            self._event("job", ["job"]),
        ]

    def _ids(self, pool):
        return {e.id for e in pool}

    def test_district_defaults_to_neutral_and_loads_from_json(self):
        self.assertIsNone(self._event("x", []).district)
        loaded = load_events(json.dumps([{
            "id": "shelved", "title": "t", "body": "b", "district": "the_archive",
            "choices": [{"id": c, "text": c, "prob": {"base": 1.0}} for c in "abc"],
        }]))
        self.assertEqual(loaded[0].district, "the_archive")

    def test_unplaced_slot_does_not_filter_at_all(self):
        """Districted events stay drawable from an unplaced slot. Exclusivity would
        make every shelved event unreachable to a player who leaves their slots in
        the Row -- a legal play, and the whole game before the map is finished.
        See docs/A1_DESIGN.md §2 and §7.6."""
        pool = eligible_pool(self._mixed(), Character(), day=1, district=None)
        self.assertEqual(self._ids(pool),
                         {"chain_a", "chain_b", "elsewhere", "noise", "job"})

    def test_placed_slot_draws_only_the_shelf(self):
        pool = eligible_pool(self._mixed(), Character(), day=1, district="the_archive")
        # own content only: not the other district, not the job, not the filler
        self.assertEqual(self._ids(pool), {"chain_a", "chain_b"})

    def test_shelf_ships_without_the_neutral_ambient_pool(self):
        """Measured, not assumed: mixing all ~88 neutral ambient events into every
        placed draw took ambient from 21.3% to 45.7% of picks and pushed never-fired
        103 -> 134. See the note in engine/selector.py and BACKLOG_HANDOFF.md §3."""
        import engine.selector as sel
        self.assertFalse(sel.SHELF_INCLUDES_AMBIENT)

    def test_shelf_can_carry_neutral_ambient_when_enabled(self):
        import engine.selector as sel
        original = sel.SHELF_INCLUDES_AMBIENT
        try:
            sel.SHELF_INCLUDES_AMBIENT = True
            pool = eligible_pool(self._mixed(), Character(), day=1, district="the_archive")
            self.assertEqual(self._ids(pool), {"chain_a", "chain_b", "noise"})
        finally:
            sel.SHELF_INCLUDES_AMBIENT = original

    def test_empty_shelf_falls_back_rather_than_burning_the_slot(self):
        """Same discipline as the ambient quota's fallback: a district whose chain
        is exhausted or still day-gated degrades into the general deck, never into
        a dead slot."""
        import engine.selector as sel
        original = sel.SHELF_INCLUDES_AMBIENT
        try:
            sel.SHELF_INCLUDES_AMBIENT = False
            events = self._mixed()
            pool = eligible_pool(events, Character(), day=1, district="nowhere_at_all")
            self.assertEqual(len(pool), len(events))
            import random as _r
            self.assertIsNotNone(
                select_event(events, Character(), day=1, rng=_r.Random(0),
                             district="nowhere_at_all"))
        finally:
            sel.SHELF_INCLUDES_AMBIENT = original

    def test_exclusions_and_ambient_budget_compose_with_the_shelf(self):
        pool = eligible_pool(self._mixed(), Character(), day=1,
                             exclude_ids={"chain_a"}, ambient_budget=0,
                             district="the_archive")
        # chain_a is spent for the day and the ambient quota is exhausted: what is
        # left is the rest of the shelf, and no filter overrides another.
        self.assertEqual(self._ids(pool), {"chain_b"})

    def test_select_event_stays_on_the_shelf(self):
        import random as _r
        for seed in range(8):
            picked = select_event(self._mixed(), Character(), day=1, rng=_r.Random(seed),
                                  district="the_archive")
            self.assertIn(picked.id, {"chain_a", "chain_b"})

    def test_district_for_slot_reads_the_morning_placement(self):
        """One read site drives every caller, so main/server/sim_bot cannot disagree
        about where a slot is standing."""
        c = Character()
        self.assertIsNone(district_for_slot(c, 0))
        apply_placements(c, {1: "the_archive"})
        self.assertIsNone(district_for_slot(c, 0))
        self.assertEqual(district_for_slot(c, 1), "the_archive")
        self.assertIsNone(district_for_slot(c, 2))

    def test_on_shelf_ignores_other_districts_ambient(self):
        """Ambient rides along only while it is neutral. Once Phase 3 gives filler
        a home, it belongs to that district and nowhere else."""
        theirs = self._event("their_noise", ["ambient"], district="the_terraces")
        self.assertFalse(on_shelf(theirs, "the_archive"))
        self.assertTrue(on_shelf(theirs, "the_terraces"))

    def test_every_shelved_event_names_a_registered_district(self):
        """The lint check's runtime twin: a typo'd district id is worse than none,
        because the shelf it names is one no placement can ever reach."""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "data", "districts.json"), encoding="utf-8") as fh:
            known = {d["id"] for d in json.load(fh)["districts"]}
        import glob
        for path in glob.glob(os.path.join(root, "data", "events", "*.json")):
            if os.path.basename(path) == "endings.json":
                continue
            with open(path, encoding="utf-8") as fh:
                for e in json.load(fh).get("events", []):
                    if e.get("district") is not None:
                        self.assertIn(e["district"], known,
                                      f"{os.path.basename(path)}:{e['id']}")


class TestMorningPlacement(unittest.TestCase):
    """A1 Phase 2: placement is a decision the player makes each morning."""

    def test_registry_is_non_empty_and_ids_are_unique(self):
        ids = district_ids()
        self.assertTrue(ids, "the map needs at least one district to place into")
        self.assertEqual(len(ids), len(set(ids)))
        for d in load_districts():
            self.assertTrue(d.get("name") and d.get("blurb"),
                            f"{d['id']} needs a name and a blurb for the placement screen")

    def test_placement_stamps_last_visited_and_clears_on_the_next_day(self):
        c = Character(day=5)
        apply_placements(c, {0: "the_archive"})
        self.assertEqual(c.placements, {0: "the_archive"})
        self.assertEqual(c.last_visited["the_archive"], 5)
        c.day = 6
        clear_placements(c)
        # The placement expires with the day; the memory of the visit does not,
        # because it is what the next morning's hint line is computed from.
        self.assertEqual(c.placements, {})
        self.assertEqual(c.last_visited["the_archive"], 5)

    def test_unregistered_district_degrades_to_unplaced(self):
        """A typo must not create a shelf no content can reach. Lint catches this
        on the content side; this is the runtime half, and it matters because
        /api/place takes the id straight off the wire."""
        c = Character()
        apply_placements(c, {0: "not_a_real_place", 1: "the_archive"})
        self.assertEqual(c.placements, {1: "the_archive"})
        self.assertNotIn("not_a_real_place", c.last_visited)

    def test_placements_survive_a_save_load_round_trip(self):
        """server.py persists placement by riding on the character, so this is the
        whole of its save-compat story."""
        c = Character(day=9)
        apply_placements(c, {2: "the_archive"})
        restored = Character.from_dict(json.loads(c.to_json()))
        self.assertEqual(restored.placements, {2: "the_archive"})
        self.assertEqual(restored.last_visited, {"the_archive": 9})

    def test_a_pre_a1_save_loads_as_unplaced(self):
        old = {"day": 3, "stats": {}, "flags": [], "relationships": {}}
        restored = Character.from_dict(old)
        self.assertEqual(restored.placements, {})
        self.assertEqual(restored.last_visited, {})

    def test_auto_placement_spends_one_draw_a_day_and_can_choose_the_row(self):
        """coverage_audit proves itself honest by reproducing sim_bot seed for
        seed, so the two loops must consume RNG identically -- which means this
        policy must draw exactly once whatever it decides."""
        import random as _r
        c = Character()
        picks = []
        for seed in range(60):
            rng = _r.Random(seed)
            picks.append(auto_placement(rng, c, 3))
            # Exactly two draws, whatever it decided: a reference stream that has
            # spent the same whether-then-where pair must stay in lockstep after.
            ref = _r.Random(seed)
            ref.random()
            ref.randrange(len(district_ids()))
            self.assertEqual(rng.random(), ref.random())
        chose_row = [p for p in picks if not p]
        chose_district = [p for p in picks if p]
        self.assertTrue(chose_row, "'stay in the Row' must be a reachable option")
        self.assertTrue(chose_district, "districts must be reachable")
        for p in chose_district:
            self.assertEqual(list(p), [0], "the stand-in commits one slot, not the day")
            self.assertIn(p[0], district_ids())

    def test_stay_in_the_row_survives_any_registry_size(self):
        """The Phase 3 regression, pinned at the extreme rather than at today's map.

        Phase 2 derived the commitment rate from the map's size
        (`min(1.0, len(districts) / 5)`), which saturates at five districts --
        so a seventh district silently removed 'stay in the Row' as an outcome
        and reserved a slot every single day. A constant that is a function of
        *content* has to be tested at the sizes that content can reach, not just
        the size it happens to have.
        """
        import random as _r
        from engine import districts as _d
        real = _d.load_districts()
        try:
            for n in (1, 2, 7, 12, 30):
                _d._registry = [{"id": f"d{i}", "name": f"D{i}", "blurb": ""}
                                for i in range(n)]
                picks = [auto_placement(_r.Random(s), Character(), 3) for s in range(80)]
                self.assertTrue([p for p in picks if not p],
                                f"'stay in the Row' unreachable at {n} district(s)")
                self.assertTrue([p for p in picks if p],
                                f"no district reachable at {n} district(s)")
        finally:
            _d._registry = real

    def test_auto_placement_draw_count_is_independent_of_slot_count(self):
        import random as _r
        for slots in (1, 2, 3):
            a, b = _r.Random(7), _r.Random(7)
            auto_placement(a, Character(), slots)
            auto_placement(b, Character(), 3)
            self.assertEqual(a.random(), b.random(),
                             "a 2-slot day must not desynchronise the stream")

    def test_hint_reports_an_empty_shelf_and_a_stocked_one(self):
        events = [
            Event(id="open_now", title="t", body="b", district="the_archive",
                  choices=[Choice(id="c", text="c", prob={"base": 1.0})]),
            Event(id="gated", title="t", body="b", district="the_archive",
                  preconditions={"all": [{"flag": "never_granted"}]},
                  choices=[Choice(id="c", text="c", prob={"base": 1.0})]),
            Event(id="elsewhere", title="t", body="b",
                  choices=[Choice(id="c", text="c", prob={"base": 1.0})]),
        ]
        c = Character(day=4)
        self.assertEqual(shelf_open_count(events, c, "the_archive"), 1)
        self.assertIn("not set foot", district_hint(events, c, "the_archive"))
        apply_placements(c, {0: "the_archive"})
        c.day = 6
        self.assertIn("2 days since", district_hint(events, c, "the_archive"))
        self.assertEqual(shelf_open_count(events, c, "no_such_district"), 0)
        self.assertIn("Nothing here", district_hint(events, c, "no_such_district"))

    def test_district_name_falls_back_to_the_row(self):
        self.assertEqual(district_name(None), "the Row at large")
        self.assertEqual(district_name("the_archive"), "The Archive Stacks")

    def test_exclusive_shelves_hide_districted_content_from_unplaced_slots(self):
        """SHELF_EXCLUSIVE ships Off; this pins what it does when it is not.

        Phase 3 measured it as a coverage catastrophe (never-fired 107 -> 212)
        and rejected it, but the switch is kept so the measurement stays
        reproducible -- so its semantics need to be nailed down, including the
        empty-pool fallback every other branch of eligible_pool honours.
        """
        from engine import selector as sel
        events = [
            Event(id="shelved", title="t", body="b", district="the_archive",
                  choices=[Choice(id="c", text="c", prob={"base": 1.0})]),
            Event(id="neutral", title="t", body="b",
                  choices=[Choice(id="c", text="c", prob={"base": 1.0})]),
        ]
        c = Character(day=4)
        ids = lambda pool: sorted(e.id for e in pool)
        self.assertEqual(ids(sel.eligible_pool(events, c, c.day)),
                         ["neutral", "shelved"])
        prior = sel.SHELF_EXCLUSIVE
        try:
            sel.SHELF_EXCLUSIVE = True
            self.assertEqual(ids(sel.eligible_pool(events, c, c.day)), ["neutral"])
            # Nothing neutral left: hand back the unfiltered pool rather than
            # burning the player's slot.
            only_shelved = [events[0]]
            self.assertEqual(ids(sel.eligible_pool(only_shelved, c, c.day)),
                             ["shelved"])
        finally:
            sel.SHELF_EXCLUSIVE = prior

    def test_arc_is_a_field_not_a_tag_and_defaults_off(self):
        """`arc` must never reach `effective_weight`, which multiplies off tags."""
        plain = Event(id="a", title="t", body="b")
        marked = Event(id="b", title="t", body="b", arc=True)
        self.assertFalse(plain.arc)
        self.assertTrue(marked.arc)
        self.assertNotIn("arc", marked.tags)
        c = Character()
        self.assertEqual(effective_weight(plain, c), effective_weight(marked, c))

    def test_shipped_content_carries_the_arc_classification(self):
        """`ambitions_pack` is the case that motivated the field.

        Its 24 storylets are three 8-link chains and the tag-only classifier
        scored them 0.0% arc, because they are tagged existential/undercity. If
        the field ever stops loading, `MIN_ARC_SHARE` silently starts measuring
        the old wrong thing again.
        """
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        events = load_events(os.path.join(root, "data", "events", "ambitions_pack.json"))
        self.assertTrue(events)
        self.assertTrue(all(e.arc for e in events),
                        "every ambitions storylet should be classified arc")
        self.assertTrue(all("arc" not in e.tags for e in events),
                        "arc must stay a field -- a tag would reach effective_weight")


class TestInventoryAndFactions(unittest.TestCase):
    def test_inventory_management(self):
        c = Character()
        self.assertFalse(c.has_item("burner_deck"))
        c.add_item("burner_deck")
        self.assertTrue(c.has_item("burner_deck"))
        c.remove_item("burner_deck")
        self.assertFalse(c.has_item("burner_deck"))

    def test_faction_standing(self):
        c = Character()
        c.add_faction("Steward", 25.0)
        self.assertEqual(c.factions["Steward"], 15.0)  # Started at -10.0 + 25.0


class TestStewardFile(unittest.TestCase):
    """A3 Phase 1: the file, and the schedule it acts on. Shipped disabled."""

    def test_the_mechanism_ships_disabled(self):
        """The whole of A3's ship-safety story. A filing consumes an action slot
        and carries consequence, so enabling it is a balance change that needs
        its own pargate against content that does not exist yet."""
        self.assertIsNone(steward.STEWARD_CADENCE,
                          "A3 ships disabled until the filings are authored and gated")
        self.assertFalse(steward.is_filing_day(999))
        self.assertIsNone(steward.next_filing_day(0))
        self.assertIsNone(steward.days_until_filing(0))
        self.assertIsNone(steward.filing_notice(Character(day=40)))

    def test_a_heat_raising_branch_writes_a_line(self):
        c = Character()
        ch = Choice(id="x", text="x", prob={"base": 1.0},
                    success={"deltas": {"Heat": 8.0}})
        resolve_choice(ch, c, random.Random(0))
        self.assertEqual(steward.file_weight(c), 1)

    def test_a_dossier_flag_writes_a_line_even_with_no_heat(self):
        """The 47 events that already grant these flags feed the counter on day
        one, which is why A3 needs no new content to have a trigger."""
        c = Character()
        ch = Choice(id="x", text="x", prob={"base": 1.0},
                    success={"flags_set": ["steward_biometric_dossier"]})
        resolve_choice(ch, c, random.Random(0))
        self.assertEqual(steward.file_weight(c), 1)

    def test_the_same_dossier_flag_counts_every_time(self):
        """The defect this reads past: the deck's dossier flags are booleans, so
        a player who trips the biometric dossier 26 times is charged once."""
        c = Character()
        ch = Choice(id="x", text="x", prob={"base": 1.0},
                    success={"flags_set": ["steward_civic_dossier"]})
        for _ in range(5):
            resolve_choice(ch, c, random.Random(0))
        self.assertEqual(steward.file_weight(c), 5)
        self.assertEqual(c.flags, {"steward_civic_dossier"})

    def test_a_quiet_branch_writes_nothing(self):
        c = Character()
        ch = Choice(id="x", text="x", prob={"base": 1.0},
                    success={"deltas": {"Meaning": 4.0}})
        resolve_choice(ch, c, random.Random(0))
        self.assertEqual(steward.file_weight(c), 0)

    def test_the_file_never_cools(self):
        """The property that makes it usable where Heat is not: cautious runs
        spend 0.0% of their days at Heat >= 25 because K_COOL drains the stock,
        so the file reads its integral and is monotonic by construction."""
        c = Character()
        up = Choice(id="u", text="u", prob={"base": 1.0}, success={"deltas": {"Heat": 30.0}})
        down = Choice(id="d", text="d", prob={"base": 1.0}, success={"deltas": {"Heat": -60.0}})
        resolve_choice(up, c, random.Random(0))
        resolve_choice(down, c, random.Random(0))
        self.assertEqual(c.get("Heat"), 0.0)
        self.assertEqual(steward.file_weight(c), 1)

    def test_heat_already_at_the_ceiling_does_not_write_a_line(self):
        """Heat clamps at 100, so a raise that cannot land is not a raise. This
        is the edge the 'raised Heat' feed has to get right or a maxed-out run
        accrues file weight for nothing."""
        c = Character()
        c.set("Heat", 100.0)
        ch = Choice(id="x", text="x", prob={"base": 1.0}, success={"deltas": {"Heat": 20.0}})
        resolve_choice(ch, c, random.Random(0))
        self.assertEqual(steward.file_weight(c), 0)

    def test_tiers_are_ordered_and_every_tier_is_reachable(self):
        thresholds = [t for t, _, _ in steward.TIERS]
        self.assertEqual(thresholds, sorted(thresholds))
        self.assertEqual(thresholds[0], 0, "tier 0 must cover a fresh character")
        indices = [i for _, i, _ in steward.TIERS]
        self.assertEqual(indices, list(range(len(steward.TIERS))))
        for threshold, index, name in steward.TIERS:
            self.assertEqual(steward.tier_for(threshold), (index, name))

    def test_tier_lookup_between_and_above_the_cuts(self):
        self.assertEqual(steward.tier_for(0)[1], "Open")
        self.assertEqual(steward.tier_for(7)[1], "Open")
        self.assertEqual(steward.tier_for(8)[1], "Under Review")
        self.assertEqual(steward.tier_for(10_000)[1], steward.TIERS[-1][2])
        self.assertIsNone(steward.next_tier(10_000))
        self.assertEqual(steward.next_tier(0)[0], steward.TIERS[1][0])

    def test_cadence_schedule_starts_after_the_review_ladder(self):
        """The Continuity Review occupies days 0/10/20/30 and completes 40/40 in
        deliberate play, so filings begin after it rather than colliding."""
        self.assertGreater(steward.FILING_ONSET, 30)
        self.assertFalse(steward.is_filing_day(steward.FILING_ONSET - 1, cadence=7))
        self.assertTrue(steward.is_filing_day(steward.FILING_ONSET, cadence=7))
        self.assertTrue(steward.is_filing_day(steward.FILING_ONSET + 7, cadence=7))
        self.assertFalse(steward.is_filing_day(steward.FILING_ONSET + 3, cadence=7))

    def test_countdown_is_monotonic_and_hits_zero_on_filing_days(self):
        cadence = 7
        for day in range(0, steward.FILING_ONSET + 3 * cadence):
            left = steward.days_until_filing(day, cadence)
            self.assertIsNotNone(left)
            self.assertGreaterEqual(left, 0)
            self.assertLessEqual(left, max(cadence, steward.FILING_ONSET))
            self.assertEqual(left == 0, steward.is_filing_day(day, cadence))

    def test_notice_names_the_tier_and_the_countdown(self):
        c = Character(day=steward.FILING_ONSET - 2)
        c.steward_file = 18
        line = steward.filing_notice(c, cadence=7)
        self.assertIn("2 days", line)
        self.assertIn("Flagged", line)
        c.day = steward.FILING_ONSET
        self.assertIn("today", steward.filing_notice(c, cadence=7))

    def test_the_file_survives_a_save_load_round_trip(self):
        c = Character(day=12)
        c.steward_file = 17
        restored = Character.from_dict(json.loads(c.to_json()))
        self.assertEqual(restored.steward_file, 17)
        self.assertEqual(steward.tier_of(restored), steward.tier_for(17))

    def test_a_pre_a3_save_loads_with_an_empty_file(self):
        old = {"day": 3, "stats": {}, "flags": [], "relationships": {}}
        self.assertEqual(Character.from_dict(old).steward_file, 0)


if __name__ == "__main__":
    unittest.main()
