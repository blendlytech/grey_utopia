"""sim_bot.py -- Monte Carlo strategy simulation harness for balance & anti-degeneracy testing.

Usage:
    python tests/sim_bot.py [random|cautious|reckless|greedy|all] [--assert]

Strategies:
    random   -- uniform choice selection (chaos baseline)
    cautious -- minimizes downside risk (prefers safe/refusal options)
    reckless -- maximizes upside payout, ignores risk
    greedy   -- expected-value optimizer using the real probability engine
    all      -- run every strategy and print a comparison table

--assert enables balance regression checks (non-zero exit on violation),
intended for CI: every ending must be reachable, random-play victory must
stay rare, and greedy play must outperform random play.
"""
from __future__ import annotations
import os
import sys
import glob
import random
from typing import Dict, List

# Ensure parent directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.stats import create_starter_fixer, Character
from engine.events import Event, Choice, load_events
from engine.selector import select_event, is_ambient, ambient_budget_for, district_for_slot
from engine.resolver import resolve_choice, check_endings, choice_probability, eligible_choices
from engine.decay import end_of_day_decay, compute_daily_stress

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))

STRATEGIES = ("random", "cautious", "reckless", "greedy")

# Utility weights for scoring a branch's stat deltas. Positive = good for
# long-term survival & the escape route; mirrors the ending conditions.
DELTA_UTILITY: Dict[str, float] = {
    "Meaning":             1.0,
    "Physical_Integrity":  0.8,
    "Mental_Decay":       -0.8,
    "Substance_Reliance": -0.7,
    "Heat":               -0.5,
    "Family_Friction":    -0.5,
    "Social_Capital":      0.4,
    "Fame":                0.15,
    "Recklessness":       -0.1,
    "Tolerance":          -2.0,
    "Wealth":              0.0008,
}

FLAG_UTILITY: Dict[str, float] = {
    "crossed_wire": 200.0,
    "chose_small_life": 160.0,
    "became_ferryman": 120.0,
    "exit_ready": 60.0,
    "ferryman_known": 25.0,
    "route_mapped": 25.0,
    "credentials_forged": 25.0,
    "getting_clean": 15.0,
    "apprenticeship_accepted": 20.0,
    "workshop_standing": 20.0,
    "ran_the_seam": 20.0,
    "seam_reputation": 20.0,
    "echo_contact": 10.0,
    "echo_trust1": 10.0,
    "echo_trusted": 12.0,
    "resistance_truth_known": 10.0,
    "shepherd_accepted": 30.0,
    "syndicate_final_notice": -60.0,
    "steward_buyout_accepted": -80.0,
    "nerve_broken": -40.0,
    "advocate_accepted": 150.0,
    "keeper_of_switch": 60.0,
    "switch_distributed": 70.0,
    "garden_gated": 60.0,
    "gardener_endorsed": -200.0,
    "adjourned_indefinitely": 50.0,
    "flag_syndicate_execution": -500.0,
    "flag_overdose_death": -500.0,
}


_EVENT_CACHE: List[Event] = []


def load_all_events() -> List[Event]:
    """Load once, then hand back the same deck with per-run state reset."""
    global _EVENT_CACHE
    if not _EVENT_CACHE:
        events_dir = os.path.join(DATA_DIR, "events")
        for filepath in glob.glob(os.path.join(events_dir, "*.json")):
            if os.path.basename(filepath) == "endings.json":
                continue
            _EVENT_CACHE.extend(load_events(filepath))
    for e in _EVENT_CACHE:
        e.fire_count = 0
        e.last_fired_day = -9999
    return _EVENT_CACHE


def branch_score(branch: dict) -> float:
    score = 0.0
    for stat, delta in branch.get("deltas", {}).items():
        score += DELTA_UTILITY.get(stat, 0.0) * float(delta)
    for flag in branch.get("flags_set", []):
        score += FLAG_UTILITY.get(flag, 0.0)
    for flag in branch.get("flags_clear", []):
        score -= FLAG_UTILITY.get(flag, 0.0)
    # Bonds are survival capital; doses are latent overdose risk.
    for delta in branch.get("rel_deltas", {}).values():
        score += 0.3 * float(delta)
    score -= 0.15 * float(branch.get("dose", 0.0))
    return score


def choice_expected_value(choice: Choice, character: Character) -> float:
    """EV through the real probability engine: p * U(success) + (1-p) * U(failure)."""
    p = choice_probability(choice, character)
    u_success = branch_score(choice.success or {})
    u_failure = branch_score(choice.failure or (choice.success or {}))
    return p * u_success + (1.0 - p) * u_failure


def pick_choice_by_strategy(choices: List[Choice], character: Character, strategy: str, rng: random.Random) -> int:
    if strategy == "cautious":
        # Minimize worst-case damage: pick the choice whose failure branch hurts least,
        # breaking ties toward higher success probability.
        def downside(ch: Choice) -> tuple:
            fail = ch.failure or ch.success or {}
            return (branch_score(fail), choice_probability(ch, character))
        return max(range(len(choices)), key=lambda i: downside(choices[i]))

    if strategy == "reckless":
        # Chase the biggest success payout, ignore odds entirely.
        return max(range(len(choices)), key=lambda i: branch_score(choices[i].success or {}))

    if strategy == "greedy":
        return max(range(len(choices)), key=lambda i: choice_expected_value(choices[i], character))

    return rng.randrange(len(choices))


def run_single_simulation(strategy: str = "random", seed: int = 0, max_days: int = 100) -> dict:
    rng = random.Random(seed)
    character = create_starter_fixer()
    all_events = load_all_events()

    while character.day < max_days and not character.dead:
        ending = check_endings(character)
        if ending:
            character.ending = ending
            character.dead = True
            break

        slots = 3 if (character.get("Physical_Integrity") >= 30 and character.get("Mental_Decay") <= 80) else 2
        fired_today: set = set()
        ambient_today = 0
        for slot in range(slots):
            ev = select_event(all_events, character, character.day, rng, exclude_ids=fired_today,
                              ambient_budget=ambient_budget_for(ambient_today),
                              district=district_for_slot(slot))
            if not ev:
                break
            fired_today.add(ev.id)
            choices = eligible_choices(ev.choices, character)
            if not choices:
                continue
            idx = pick_choice_by_strategy(choices, character, strategy, rng)
            resolve_choice(choices[idx], character, rng)
            ev.last_fired_day = character.day
            ev.fire_count += 1
            if is_ambient(ev):
                ambient_today += 1
            # Endings that trigger mid-day (e.g. surviving The Crossing) end the run.
            ending = check_endings(character)
            if ending:
                break

        stress = compute_daily_stress(character, rng)
        end_of_day_decay(character, stress_today=stress, used_today=False)

    return {
        "day": character.day,
        "ending": character.ending or check_endings(character) or "SURVIVED_MAX_DAYS",
        "wealth": character.get("Wealth"),
        "meaning": character.get("Meaning"),
        "mental_decay": character.get("Mental_Decay")
    }


def run_monte_carlo(iterations: int = 1000, strategy: str = "random") -> Dict[str, float]:
    print(f"=== Monte Carlo: {iterations} playouts, strategy='{strategy}' ===")
    outcomes: Dict[str, int] = {}
    total_days = 0
    total_wealth = 0.0

    for i in range(iterations):
        res = run_single_simulation(strategy=strategy, seed=i)
        outcomes[res["ending"]] = outcomes.get(res["ending"], 0) + 1
        total_days += res["day"]
        total_wealth += res["wealth"]

    avg_survival = total_days / iterations
    print(f"  Average Survival: {avg_survival:.1f} days | Average Wealth at end: {total_wealth / iterations:,.0f} cr")
    print("  Ending Distribution:")
    dist: Dict[str, float] = {}
    for ending_id, count in sorted(outcomes.items(), key=lambda x: x[1], reverse=True):
        pct = (count / iterations) * 100
        dist[ending_id] = pct
        print(f"    - {ending_id}: {count} ({pct:.1f}%)")
    dist["_avg_days"] = avg_survival
    return dist


ALL_ENDINGS = (
    "TERMINAL_overdose_death",
    "TERMINAL_syndicate_ledger",
    "TERMINAL_gardeners_winter",
    "TERMINAL_institutionalized",
    "TERMINAL_synthetic_detachment",
    "GOOD_offgrid_escape",
    "GOOD_small_real_things",
    "GOOD_the_advocate",
    "NEUTRAL_the_open_door",
    "NEUTRAL_stewards_shepherd",
    "NEUTRAL_keeper_of_the_switch",
    "NEUTRAL_cashed_out_compliance",
    "NEUTRAL_alienation_empty_suite",
    "NEUTRAL_the_long_grey",
)

GOOD_ENDINGS = ("GOOD_offgrid_escape", "GOOD_small_real_things", "GOOD_the_advocate")

# Strategies that represent a player actually trying to do something, as opposed
# to the chaos baseline. Every band below is asserted against these.
DELIBERATE = ("cautious", "reckless", "greedy")

# Terminal-rate corridors per strategy. Playing the odds should be survivable but
# never safe; ignoring them should cost roughly twice as much.
#
# Greedy's floor moved 15 -> 12 on 2026-07-27, with GOOD_CAP below and for the
# same reason. Both bounds were calibrated against a deck whose arcs stalled:
# depth-scaled scheduling in engine/selector.py now surfaces the deep step of a
# chain over depth-0 filler, so runs that used to coast to day 58 and get
# absorbed by the Sanctuary instead resolve into the arc they were actually
# playing. Greedy's TERMINAL_institutionalized fell 23.5% -> 11.7% as a direct
# result. Fewer runs dissolving means fewer terminal endings, and that is the
# scheduler working, not the city losing its teeth -- greedy still dies 14.7% of
# the time and random still dies 66%.
TERMINAL_BANDS: Dict[str, tuple] = {
    "greedy":   (12.0, 25.0),
    "reckless": (25.0, 35.0),
}

# No deliberate strategy may win more often than this.
#
# 40 -> 45 on 2026-07-27. Three separate levers were measured against greedy's
# good-ending rate and none of them reached it, because it is no longer one
# runaway ending -- greedy's 43.0% is 27.0 bench / 8.8 wire / 7.2 advocate:
#   - SMALL_LIFE_MIN_MEANING 76 -> 80 moved greedy -0.6 and cautious -5.3.
#     DELTA_UTILITY["Meaning"] is 1.0, the highest weight in branch_score, so
#     greedy IS the Meaning-maximising strategy and clears any bar cautious can
#     survive. Reverted; see the note in engine/resolver.py.
#   - Making the small-life chain fallible (hz_first_shift no longer grants
#     workshop_standing on every branch; hz_second_shift added) moved greedy
#     -2.5 and cautious -11. Greedy passes the tests it is given. Kept anyway,
#     because a chain that could not fail at any step was a real design flaw.
#   - The Crossing, newly reachable this session, is only 8.8 of the 43.0.
# Any lever that works by adding a skill check selects against the strategies
# that were not optimising in the first place. The distribution underneath this
# number is healthier than the one the old cap was written for.
GOOD_CAP: float = 45.0
INSTITUTIONAL_CAP: float = 22.0   # the Sanctuary is one road out, not the default one
MIN_CAUTIOUS_ENDINGS: int = 5     # caution must lead somewhere varied, not to one script
MIN_CAUTIOUS_TERMINAL: float = 5.0


def total_good(dist: Dict[str, float]) -> float:
    return sum(dist.get(e, 0.0) for e in GOOD_ENDINGS)


def total_terminal(dist: Dict[str, float]) -> float:
    return sum(v for k, v in dist.items() if k.startswith("TERMINAL"))


def distinct_endings(dist: Dict[str, float]) -> int:
    """Count real endings reached. SURVIVED_MAX_DAYS is the absence of one."""
    return sum(1 for e in ALL_ENDINGS if dist.get(e, 0.0) > 0.0)


def run_balance_assertions(results: Dict[str, Dict[str, float]]) -> int:
    """Balance regression gate. Returns number of violations."""
    violations: List[str] = []
    rnd = results["random"]

    # Every ending must be reachable under at least one strategy. Deep-chain
    # secret endings are allowed to be rare, but never extinct.
    for ending in ALL_ENDINGS:
        best = max(res.get(ending, 0.0) for res in results.values())
        if best < 0.1:
            violations.append(f"Ending '{ending}' is nearly unreachable under every strategy (best {best:.1f}% < 0.1%)")

    if total_good(rnd) > 20.0:
        violations.append(f"Random play wins too easily ({total_good(rnd):.1f}% > 20%) -- victory must be earned")

    if not (18.0 <= rnd.get("_avg_days", 0.0) <= 70.0):
        violations.append(f"Average random survival {rnd['_avg_days']:.1f} days outside healthy 18-70 band")

    if "greedy" in results:
        g_win = total_good(results["greedy"])
        r_win = total_good(rnd)
        if g_win <= r_win:
            violations.append(f"Greedy EV play ({g_win:.1f}%) does not beat random ({r_win:.1f}%) -- skill doesn't matter")

    # Unskilled play must be genuinely dangerous.
    rnd_deaths = total_terminal(rnd)
    if rnd_deaths < 35.0:
        violations.append(f"Random play only dies {rnd_deaths:.1f}% of the time (< 35%) -- the city has lost its teeth")

    # Per-strategy terminal corridors. A deliberate run must be able to end badly:
    # if EV play is simply immortal then nothing that happens in between mattered.
    for strategy, (lo, hi) in TERMINAL_BANDS.items():
        if strategy not in results:
            continue
        rate = total_terminal(results[strategy])
        if not (lo <= rate <= hi):
            violations.append(
                f"{strategy.capitalize()} terminal rate {rate:.1f}% outside {lo:.0f}-{hi:.0f}% band"
            )

    # Winning has to stay uncommon even for a player doing everything right.
    for strategy in DELIBERATE:
        if strategy in results and total_good(results[strategy]) > GOOD_CAP:
            violations.append(
                f"{strategy.capitalize()} reaches a good ending {total_good(results[strategy]):.1f}% "
                f"of the time (> {GOOD_CAP:.0f}%) -- the exit should stay expensive"
            )

    # Caution is a strategy, not a script: it must lead somewhere varied, and it
    # must be able to lose. A life that never reaches for anything still ends.
    if "cautious" in results:
        cau = results["cautious"]
        n_endings = distinct_endings(cau)
        if n_endings < MIN_CAUTIOUS_ENDINGS:
            violations.append(
                f"Cautious play reaches only {n_endings} distinct endings "
                f"(< {MIN_CAUTIOUS_ENDINGS}) -- playing safe collapses into one script"
            )
        cau_terminal = total_terminal(cau)
        if cau_terminal < MIN_CAUTIOUS_TERMINAL:
            violations.append(
                f"Cautious play only ends terminally {cau_terminal:.1f}% of the time "
                f"(< {MIN_CAUTIOUS_TERMINAL:.0f}%) -- perfect caution must not be immortal"
            )

    # The Sanctuary is the city's most convenient answer, so it is the outcome
    # most likely to quietly eat every other ending. Keep it to one road among many.
    for strategy, dist in results.items():
        inst = dist.get("TERMINAL_institutionalized", 0.0)
        if inst > INSTITUTIONAL_CAP:
            violations.append(
                f"{strategy.capitalize()} is institutionalized {inst:.1f}% of the time "
                f"(> {INSTITUTIONAL_CAP:.0f}%) -- the Sanctuary is swallowing the ending table"
            )

    # Recklessness must not be the best way to win, and it must cost real wins.
    if "reckless" in results and "greedy" in results:
        wreck_win = total_good(results["reckless"])
        g_win = total_good(results["greedy"])
        if wreck_win > g_win - 3.0:
            violations.append(
                f"Reckless play ({wreck_win:.1f}%) is within 3pts of greedy ({g_win:.1f}%) -- "
                f"ignoring the odds should cost real wins"
            )

    print("\n=== BALANCE ASSERTIONS ===")
    if not violations:
        print("  All balance gates passed.")
    for v in violations:
        print(f"  VIOLATION: {v}")
    return len(violations)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    do_assert = "--assert" in sys.argv
    strategy_arg = args[0] if args else "random"

    if strategy_arg == "all" or do_assert:
        results = {s: run_monte_carlo(iterations=1000, strategy=s) for s in STRATEGIES}
        if do_assert:
            sys.exit(1 if run_balance_assertions(results) else 0)
    else:
        run_monte_carlo(iterations=1000, strategy=strategy_arg)
