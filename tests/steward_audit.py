"""steward_audit.py -- is the Steward an antagonist you can anticipate? (A3)

`sim_bot.py` answers "where do runs end up?"; `coverage_audit.py` answers "what
was the player shown on the way there?". This answers "what did the Steward
*do*, and could the player see it coming?" -- which A3 needs and neither of the
other two instruments can see, because both are blind to which antagonist a
storylet belongs to.

Three modes, and the first two are the Step 0 measurements that overturned this
item's written premise:

    --presence   how often the Steward is already on screen, per strategy, and
                 whether the Continuity Review ladder completes
    --trigger    Heat vs the file, as candidate triggers. The measurement that
                 killed Heat: cautious runs spend 0.0% of their days at Heat >= 25.
    --cadence N  what a forced filing every N days would cost, against a control
                 that spends the same RNG and discards it

Usage:
    python tests/steward_audit.py --presence
    python tests/steward_audit.py --trigger
    python tests/steward_audit.py --cadence 7
    python tests/steward_audit.py --cadence 7 --control
    python tests/steward_audit.py --trigger -n 20 --seed-base 100
"""
from __future__ import annotations
import argparse
import os
import random
import statistics
import sys
from collections import Counter, defaultdict
from typing import Dict, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine import steward
from engine.decay import compute_daily_stress, end_of_day_decay
from engine.districts import apply_placements, auto_placement, clear_placements
from engine.resolver import check_endings, eligible_choices, resolve_choice
from engine.selector import (
    ambient_budget_for, district_for_slot, is_ambient, select_event)
from engine.stats import create_starter_fixer
from tests.sim_bot import STRATEGIES, load_all_events, pick_choice_by_strategy

RUNS = 40

# The Continuity Review ladder: the Steward's existing scheduled turn. Forced
# (`weight: 500000`), flag-chained, gated at days 0/10/20/30. A3's spec was
# written as though this did not exist.
REVIEW_LADDER = (
    "prologue_continuity_review",
    "review_second_session",
    "review_third_session",
    "review_final_session",
)

HEAT_THRESHOLDS = (15, 20, 25, 35, 45, 60)


def playout(strategy: str, seed: int, max_days: int = 100,
            cadence: Optional[int] = None, control: bool = False) -> dict:
    """One instrumented run. Mirrors sim_bot.run_single_simulation exactly except
    for the observations, which have to be taken inside the slot loop.

    `cadence` reserves one action slot on each filing day, standing in for a
    forced Steward event the way A1 Phase 1's harness stood in for a player
    choosing a district. `control` computes the same filing days and reserves
    nothing -- the honest A/B partner, because skipping a slot removes a
    `select_event` call and so reshuffles every subsequent draw (BACKLOG_HANDOFF
    §5, A1 Phase 2: "a change that alters RNG consumption cannot be A/B'd
    against a run that does not").
    """
    rng = random.Random(seed)
    character = create_starter_fixer()
    all_events = load_all_events()

    steward_fire_days: List[int] = []
    review_days: Dict[str, int] = {}
    fired_ids: set = set()
    heat_by_day: Dict[int, float] = {}
    file_by_day: Dict[int, int] = {}
    filings = 0
    slots_spent = 0
    slots_reserved = 0

    while character.day < max_days and not character.dead:
        if check_endings(character):
            character.dead = True
            break
        heat_by_day[character.day] = character.get("Heat")
        file_by_day[character.day] = steward.file_weight(character)

        slots = 3 if (character.get("Physical_Integrity") >= 30
                      and character.get("Mental_Decay") <= 80) else 2
        clear_placements(character)
        apply_placements(character, auto_placement(rng, character, slots))

        filing_today = steward.is_filing_day(character.day, cadence)
        if filing_today:
            filings += 1

        fired_today: set = set()
        ambient_today = 0
        for slot in range(slots):
            # The reserved slot: a forced filing would win this draw outright at
            # the deck's `weight: 500000` precedent, so the honest cost model is
            # that the slot never reaches select_event at all.
            if filing_today and slot == 0 and not control:
                slots_reserved += 1
                continue
            ev = select_event(all_events, character, character.day, rng,
                              exclude_ids=fired_today,
                              ambient_budget=ambient_budget_for(ambient_today),
                              district=district_for_slot(character, slot))
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
            fired_ids.add(ev.id)
            slots_spent += 1
            if "steward" in ev.tags:
                steward_fire_days.append(character.day)
            if ev.id in REVIEW_LADDER and ev.id not in review_days:
                review_days[ev.id] = character.day
            if is_ambient(ev):
                ambient_today += 1
            if check_endings(character):
                break

        end_of_day_decay(character, stress_today=compute_daily_stress(character, rng))

    return {
        "days": character.day,
        "ending": character.ending or check_endings(character) or "SURVIVED_MAX_DAYS",
        "steward_fire_days": steward_fire_days,
        "review_days": review_days,
        "fired_ids": fired_ids,
        "heat_by_day": heat_by_day,
        "file_by_day": file_by_day,
        "file_final": steward.file_weight(character),
        "filings": filings,
        "slots_spent": slots_spent,
        "slots_reserved": slots_reserved,
    }


def _sweep(strategy: str, n: int, base: int, **kw) -> List[dict]:
    return [playout(strategy, base + i, **kw) for i in range(n)]


def _longest_silence(run: dict) -> int:
    days = sorted(set(run["steward_fire_days"]))
    if not days:
        return run["days"]
    marks = [0] + days + [run["days"]]
    return max(b - a for a, b in zip(marks, marks[1:]))


def report_presence(n: int, base: int) -> None:
    print(f"\n=== PRESENCE: is the Steward already on screen? (n={n}, seeds {base}..{base+n-1}) ===\n")
    print(f"{'strategy':10s} {'med days':>9s} {'fires/run':>10s} {'days seen':>10s} "
          f"{'% of days':>10s} {'longest gap':>12s}")
    print("-" * 65)
    ladder: Dict[str, Counter] = {}
    for strat in STRATEGIES:
        runs = _sweep(strat, n, base)
        med = statistics.median(r["days"] for r in runs)
        fires = statistics.mean(len(r["steward_fire_days"]) for r in runs)
        seen = statistics.mean(len(set(r["steward_fire_days"])) for r in runs)
        pct = statistics.mean(
            100.0 * len(set(r["steward_fire_days"])) / max(r["days"], 1) for r in runs)
        gap = statistics.mean(_longest_silence(r) for r in runs)
        print(f"{strat:10s} {med:9.0f} {fires:10.1f} {seen:10.1f} {pct:9.1f}% {gap:12.1f}")
        ladder[strat] = Counter()
        for r in runs:
            for rid in REVIEW_LADDER:
                if rid in r["review_days"]:
                    ladder[strat][rid] += 1

    print(f"\n--- Continuity Review ladder: runs of {n} in which each session fired ---")
    print(f"{'session':30s}" + "".join(f"{s:>11s}" for s in STRATEGIES))
    for rid in REVIEW_LADDER:
        print(f"{rid:30s}" + "".join(f"{ladder[s][rid]:>11d}" for s in STRATEGIES))
    print("\nThe ladder is forced (weight 500000), flag-chained and day-gated at "
          "0/10/20/30.\nIt is the scheduled Steward turn A3's spec assumed did not exist -- and it\n"
          "stops at day 30 against deliberate runs of 54-62 days.")


def report_trigger(n: int, base: int) -> None:
    print(f"\n=== TRIGGER: Heat vs the file (n={n}, seeds {base}..{base+n-1}) ===\n")
    heat_days: Dict[str, list] = {}
    peaks: Dict[str, list] = {}
    file_curve: Dict[str, Dict[int, list]] = {}
    file_final: Dict[str, list] = {}
    rate: Dict[str, list] = {}

    for strat in STRATEGIES:
        runs = _sweep(strat, n, base)
        heat_days[strat] = [h for r in runs for h in r["heat_by_day"].values()]
        peaks[strat] = [max(r["heat_by_day"].values()) for r in runs]
        curve: Dict[int, list] = defaultdict(list)
        for r in runs:
            for d, w in r["file_by_day"].items():
                curve[d].append(w)
        file_curve[strat] = curve
        file_final[strat] = [r["file_final"] for r in runs]
        rate[strat] = [r["file_final"] / max(r["days"], 1) * 10 for r in runs]

    print("--- Heat: share of all run-days at or above each threshold ---")
    print(f"{'strategy':10s} {'mean':>7s} {'peak(med)':>10s}   "
          + "".join(f"{'>=%d' % t:>8s}" for t in HEAT_THRESHOLDS))
    print("-" * 74)
    for strat in STRATEGIES:
        vals = heat_days[strat]
        row = (f"{strat:10s} {statistics.mean(vals):7.2f} "
               f"{statistics.median(peaks[strat]):10.1f}   ")
        for t in HEAT_THRESHOLDS:
            row += f"{100.0 * sum(1 for v in vals if v >= t) / len(vals):7.1f}%"
        print(row)
    spread = max(statistics.mean(heat_days[s]) for s in STRATEGIES) / \
        max(1e-9, min(statistics.mean(heat_days[s]) for s in STRATEGIES))
    print(f"\nmean-Heat spread across strategies: {spread:.1f}x -- Heat is a *stock*, and "
          f"decay.K_COOL\ndrains it to zero for anyone careful. A Heat-gated Steward never "
          f"speaks to the\ncautious player at all.")

    print(f"\n--- The file: median weight at day D ---")
    print(f"{'day':>5s}" + "".join(f"{s:>11s}" for s in STRATEGIES))
    for d in (5, 10, 20, 30, 40, 50, 60):
        row = f"{d:>5d}"
        for s in STRATEGIES:
            v = file_curve[s].get(d, [])
            row += f"{(statistics.median(v) if v else float('nan')):>11.1f}"
        print(row)

    print(f"\n{'strategy':10s} {'final (med)':>12s} {'per 10 days':>12s}")
    print("-" * 36)
    for s in STRATEGIES:
        print(f"{s:10s} {statistics.median(file_final[s]):12.1f} "
              f"{statistics.mean(rate[s]):12.2f}")
    rates = [statistics.mean(rate[s]) for s in STRATEGIES]
    print(f"\nfile-rate spread across strategies: {max(rates)/min(rates):.2f}x")

    print(f"\n--- Tier reach: runs of {n} whose file ever reached each tier ---")
    print(f"{'tier':22s}" + "".join(f"{s:>11s}" for s in STRATEGIES))
    for threshold, index, name in steward.TIERS:
        label = f"{index} {name} (>={threshold})"
        print(f"{label:22s}"
              + "".join(f"{sum(1 for w in file_final[s] if w >= threshold):>11d}"
                        for s in STRATEGIES))


def report_cadence(cadence: int, n: int, base: int) -> None:
    print(f"\n=== CADENCE: a forced filing every {cadence} days from day "
          f"{steward.FILING_ONSET} (n={n}) ===\n")
    print(f"{'strategy':10s} {'mode':>8s} {'med days':>9s} {'filings':>8s} "
          f"{'slots kept':>11s} {'reserved':>9s} {'uniq/run':>9s} {'never fired':>12s}")
    print("-" * 84)
    for strat in STRATEGIES:
        for mode, ctl in (("control", True), ("live", False)):
            runs = _sweep(strat, n, base, cadence=cadence, control=ctl)
            deck = len(load_all_events())
            seen = set()
            for r in runs:
                seen |= r["fired_ids"]
            print(f"{strat:10s} {mode:>8s} "
                  f"{statistics.median(r['days'] for r in runs):9.0f} "
                  f"{statistics.mean(r['filings'] for r in runs):8.1f} "
                  f"{statistics.mean(r['slots_spent'] for r in runs):11.1f} "
                  f"{statistics.mean(r['slots_reserved'] for r in runs):9.1f} "
                  f"{statistics.mean(len(r['fired_ids']) for r in runs):9.1f} "
                  f"{deck - len(seen):12d}")
    print("\n`control` computes the same filing days and reserves nothing, so the two rows\n"
          "differ only by the reserved slot. Comparing `live` against a no-cadence run\n"
          "instead would confound the reservation with the RNG reshuffle it causes.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--presence", action="store_true",
                    help="how often the Steward is already on screen")
    ap.add_argument("--trigger", action="store_true",
                    help="Heat vs the file as candidate triggers")
    ap.add_argument("--cadence", type=int, metavar="N",
                    help="cost of a forced filing every N days")
    ap.add_argument("-n", type=int, default=RUNS, help=f"runs per strategy (default {RUNS})")
    ap.add_argument("--seed-base", type=int, default=0, help="first seed (default 0)")
    args = ap.parse_args()

    if not (args.presence or args.trigger or args.cadence):
        args.presence = args.trigger = True

    if args.presence:
        report_presence(args.n, args.seed_base)
    if args.trigger:
        report_trigger(args.n, args.seed_base)
    if args.cadence:
        report_cadence(args.cadence, args.n, args.seed_base)


if __name__ == "__main__":
    main()
