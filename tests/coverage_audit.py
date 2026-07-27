"""coverage_audit.py -- reachability and draw-composition audit for the storylet deck.

`sim_bot.py` answers "where do runs end up?". This answers "what did the player
actually get shown on the way there?" -- which of the 483 storylets are reachable
under real play, how big the eligible pool is, and how much of each draw's weight
reaches arc content rather than ambient filler.

The playout is the same one `sim_bot.run_single_simulation` drives
(select_event -> eligible_choices -> resolve_choice -> end_of_day_decay), re-stated
here only because the pool has to be observed *before* each pick and `select_event`
builds it internally. `--parity` re-runs the same seeds through sim_bot and checks
both loops land on the same day and ending, which is what keeps the copy honest.

Usage:
    python tests/coverage_audit.py                    # 40 runs, full report
    python tests/coverage_audit.py -n 10              # quick read
    python tests/coverage_audit.py --assert           # standing gate; exit 1 on violation
    python tests/coverage_audit.py --parity           # cross-check against sim_bot
    python tests/coverage_audit.py --ambient-slots 0  # A/B the ambient quota
    # A/B an A1 district shelf: place 1 slot there every 5th day and report it
    python tests/coverage_audit.py --district the_archive --district-slots 1 \
        --district-every 5 --track-district the_archive
"""
from __future__ import annotations
import argparse
import glob
import json
import os
import random
import statistics
import sys
from collections import Counter
from typing import Dict, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.decay import compute_daily_stress, end_of_day_decay
from engine.resolver import check_endings, eligible_choices, resolve_choice
from engine import selector as selector_module
from engine.selector import (
    AMBIENT_SLOTS_PER_DAY, PROTOTYPE_DISTRICT, effective_weight, eligible_pool,
    index_library, is_ambient, select_event,
)
from engine.stats import Character, create_starter_fixer
from tests.sim_bot import DATA_DIR, load_all_events, pick_choice_by_strategy

# The content this audit exists to protect: anything a player is walking a thread
# toward. Ambient/micro filler is everything this is measured against.
ARC_TAGS = frozenset({"flagship", "arc", "npc", "betrayal", "resistance", "relationship"})

RUNS = 40

# Gate thresholds. These guard the measured baseline against regression; they are
# deliberately NOT F1's targets (< 70 never-fired, > 35% arc draw-share), which
# were written against a scratch harness and which F1 then proved unreachable by
# any pool-composition lever -- ambient+micro is only ~21% of draw weight, and the
# unreached content is flag-gated rather than out-competed. A gate that is red on
# the day it lands gets ignored, so this one is set where the deck actually is:
# 97 never-fired and 24.9% arc draw-share at n=40, seed 0.
#
# MAX_NEVER_FIRED is only meaningful at RUNS runs -- coverage compounds hard with
# sample size (209 never-fired at n=5, 97 at n=40, 69 at n=100 on the same deck),
# so quoting the number without its N says nothing. The gate refuses to assert on
# it at any other N, and the default seed is pinned so the figure is comparable
# across windows.
MAX_NEVER_FIRED = 105
MIN_ARC_SHARE = 23.0


def pack_index() -> Dict[str, str]:
    """event id -> the pack file it was authored in, for the unreached breakdown."""
    packs: Dict[str, str] = {}
    for filepath in sorted(glob.glob(os.path.join(DATA_DIR, "events", "*.json"))):
        name = os.path.basename(filepath)
        if name == "endings.json":
            continue
        with open(filepath, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            data = data.get("events", [])
        for entry in data:
            packs[entry["id"]] = name[:-5]
    return packs


def arc_share(pool, character: Character) -> Optional[float]:
    """Fraction of this draw's total weight sitting on arc content, 0..1."""
    weights = [(e, effective_weight(e, character)) for e in pool]
    total = sum(w for _, w in weights)
    if total <= 0:
        return None
    arc = sum(w for e, w in weights if ARC_TAGS.intersection(e.tags))
    return arc / total


def audit_run(strategy: str, seed: int, max_days: int = 100,
              ambient_slots: Optional[int] = AMBIENT_SLOTS_PER_DAY,
              district: Optional[str] = PROTOTYPE_DISTRICT,
              district_slots: int = 0,
              district_every: int = 1,
              chain: Optional[set] = None) -> dict:
    """One instrumented playout. RNG consumption mirrors sim_bot exactly.

    `ambient_slots` overrides the shipped quota so a window can bound the lever
    without editing engine constants: None restores pre-quota behaviour, 0 is
    the strictest the quota can be (ambient only when nothing else is eligible).

    `district` / `district_slots` / `district_every` do the same for A1's
    shelves: on every `district_every`-th day, place that day's first
    `district_slots` action slots in `district` and leave the rest unplaced.
    `district_slots=0` is the unplaced baseline and reproduces pre-A1 behaviour
    exactly, which is what makes the A/B a clean causal test rather than two
    unrelated runs.

    The cadence is here rather than in `engine.selector.district_for_slot`
    because it is not the engine's decision: in the finished A1 the player picks
    where to stand each morning. `district_every` stands in for "how often would
    someone actually go there," and it turned out to be the difference between a
    shelf that advances a chain and a shelf that is a vending machine.

    `chain` is a set of event ids to track separately. It splits "never eligible"
    from "eligible but never picked" -- the distinction F1 proved is the whole
    ballgame, and the one a bare never-fired count cannot make.
    """
    rng = random.Random(seed)
    character = create_starter_fixer()
    all_events = load_all_events()
    index_library(all_events)

    fired: List[str] = []          # every event a choice was resolved on, in order
    pool_sizes: List[int] = []     # eligible pool at each day's first draw
    shares: List[float] = []       # arc weight share, per draw
    ambient_fired = 0              # ambient picks, for the quota's own accounting
    arc_fired = 0                  # picks that landed on arc content
    chain_elig_draws = 0           # draws in which any tracked event was eligible
    chain_shares: List[float] = [] # tracked events' combined share of a draw's weight
    chain_elig_ids: set = set()    # tracked events that were eligible at least once
    chain_fired_ids: set = set()   # tracked events that actually fired

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
            budget = None if ambient_slots is None else ambient_slots - ambient_today
            visiting = character.day % district_every == 0
            placed = district if (visiting and slot < district_slots) else None
            # The pool the selector is about to sample from, measured through the
            # engine's own filter so the instrument cannot drift from the game.
            pool = eligible_pool(all_events, character, character.day, fired_today, budget, placed)
            if slot == 0:
                pool_sizes.append(len(pool))
            share = arc_share(pool, character)
            if share is not None:
                shares.append(share)
            if chain:
                tracked = [e for e in pool if e.id in chain]
                if tracked:
                    chain_elig_draws += 1
                    chain_elig_ids.update(e.id for e in tracked)
                    weights = [(e, effective_weight(e, character)) for e in pool]
                    total = sum(w for _, w in weights)
                    if total > 0:
                        chain_shares.append(
                            sum(w for e, w in weights if e.id in chain) / total
                        )

            ev = select_event(all_events, character, character.day, rng, exclude_ids=fired_today,
                              ambient_budget=budget, district=placed)
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
            fired.append(ev.id)
            if chain and ev.id in chain:
                chain_fired_ids.add(ev.id)
            if is_ambient(ev):
                ambient_today += 1
                ambient_fired += 1
            if ARC_TAGS.intersection(ev.tags):
                arc_fired += 1
            ending = check_endings(character)
            if ending:
                break

        stress = compute_daily_stress(character, rng)
        end_of_day_decay(character, stress_today=stress, used_today=False)

    return {
        "day": character.day,
        "ending": character.ending or check_endings(character) or "SURVIVED_MAX_DAYS",
        "fired": fired,
        "ambient_fired": ambient_fired,
        "arc_fired": arc_fired,
        "pool_sizes": pool_sizes,
        "shares": shares,
        "chain_elig_draws": chain_elig_draws,
        "chain_shares": chain_shares,
        "chain_elig_ids": chain_elig_ids,
        "chain_fired_ids": chain_fired_ids,
    }


def parity_check(strategy: str, seeds: List[int]) -> List[str]:
    """Prove this loop is the loop sim_bot scores: same seed -> same day and ending."""
    from tests import sim_bot

    mismatches: List[str] = []
    for seed in seeds:
        mine = audit_run(strategy, seed)
        theirs = sim_bot.run_single_simulation(strategy=strategy, seed=seed)
        if (mine["day"], mine["ending"]) != (theirs["day"], theirs["ending"]):
            mismatches.append(
                f"seed {seed}: audit {mine['ending']}@d{mine['day']} != "
                f"sim_bot {theirs['ending']}@d{theirs['day']}"
            )
    return mismatches


def run_audit(runs: int, strategy: str, seed0: int,
              ambient_slots: Optional[int] = AMBIENT_SLOTS_PER_DAY,
              district: Optional[str] = PROTOTYPE_DISTRICT,
              district_slots: int = 0,
              district_every: int = 1,
              chain: Optional[str] = None,
              track_district: Optional[str] = None) -> dict:
    all_events = load_all_events()
    deck_ids = {e.id for e in all_events}
    packs = pack_index()

    # What to report separately. A district id is the natural unit for A1 and is
    # collision-free; an id prefix is the general escape hatch, and a sharp one --
    # 'amb_' matches the 24 ambitions events AND 42 unrelated volume ambients.
    tracked_ids: Optional[set] = None
    label = None
    if track_district:
        tracked_ids = {e.id for e in all_events if e.district == track_district}
        label = f"district {track_district}"
    elif chain:
        tracked_ids = {e.id for e in all_events if e.id.startswith(chain)}
        label = f"prefix {chain!r}"

    fire_totals: Counter = Counter()
    unique_per_run: List[int] = []
    repeat_fracs: List[float] = []
    pool_sizes: List[int] = []
    shares: List[float] = []
    days: List[int] = []
    picks = 0
    ambient_picks = 0
    arc_picks = 0
    chain_ids = sorted(tracked_ids or ())
    chain_draws = 0
    chain_shares: List[float] = []
    chain_runs_elig = 0
    chain_runs_fired = 0
    chain_elig_ids: set = set()
    chain_fired_ids: set = set()
    chain_picks = 0

    for i in range(runs):
        res = audit_run(strategy, seed0 + i, ambient_slots=ambient_slots,
                        district=district, district_slots=district_slots,
                        district_every=district_every, chain=tracked_ids)
        fired = res["fired"]
        picks += len(fired)
        ambient_picks += res["ambient_fired"]
        arc_picks += res["arc_fired"]
        fire_totals.update(fired)
        unique = len(set(fired))
        unique_per_run.append(unique)
        if fired:
            repeat_fracs.append((len(fired) - unique) / len(fired))
        pool_sizes.extend(res["pool_sizes"])
        shares.extend(res["shares"])
        days.append(res["day"])
        if tracked_ids:
            chain_draws += res["chain_elig_draws"]
            chain_shares.extend(res["chain_shares"])
            chain_elig_ids |= res["chain_elig_ids"]
            chain_fired_ids |= res["chain_fired_ids"]
            chain_picks += sum(1 for eid in fired if eid in tracked_ids)
            chain_runs_elig += 1 if res["chain_elig_ids"] else 0
            chain_runs_fired += 1 if res["chain_fired_ids"] else 0

    never = sorted(deck_ids - set(fire_totals))
    by_pack: Counter = Counter(packs.get(eid, "?") for eid in never)
    pack_totals: Counter = Counter(packs.get(eid, "?") for eid in deck_ids)

    return {
        "deck": len(deck_ids),
        "packs": len(pack_totals),
        "runs": runs,
        "never": never,
        "by_pack": by_pack,
        "pack_totals": pack_totals,
        "median_days": statistics.median(days),
        "median_pool": statistics.median(pool_sizes) if pool_sizes else 0,
        "median_share": statistics.median(shares) * 100 if shares else 0.0,
        "median_unique": statistics.median(unique_per_run),
        "repeat_frac": statistics.mean(repeat_fracs) * 100 if repeat_fracs else 0.0,
        "ambient_pick_share": ambient_picks / picks * 100 if picks else 0.0,
        "arc_pick_share": arc_picks / picks * 100 if picks else 0.0,
        "chain": label,
        "chain_size": len(chain_ids),
        "chain_reached": len(chain_fired_ids),
        "chain_ever_elig": len(chain_elig_ids),
        "chain_runs_elig": chain_runs_elig,
        "chain_runs_fired": chain_runs_fired,
        "chain_draws": chain_draws,
        "chain_picks": chain_picks,
        "chain_median_share": statistics.median(chain_shares) * 100 if chain_shares else 0.0,
        "chain_fire_totals": {eid: fire_totals.get(eid, 0) for eid in chain_ids},
    }


def report(res: dict) -> None:
    deck = res["deck"]
    never = len(res["never"])
    print(f"=== coverage audit: {res['runs']} runs, {deck} events, {res['packs']} packs ===")
    print(f"  median run length            {res['median_days']:.0f} days")
    print(f"  median eligible pool / day   {res['median_pool']:.0f}")
    print(f"  median arc draw-share        {res['median_share']:.1f}%")
    print(f"  unique events per run        {res['median_unique']:.0f} "
          f"({res['median_unique'] / deck * 100:.1f}% of deck)")
    print(f"  repeat-pick fraction         {res['repeat_frac']:.1f}%")
    print(f"  ambient share of picks       {res['ambient_pick_share']:.1f}%")
    print(f"  arc share of picks           {res['arc_pick_share']:.1f}%")
    print(f"  events never fired           {never} ({never / deck * 100:.1f}%)")

    if never:
        print("\n  never fired, by pack:")
        for pack, count in sorted(res["by_pack"].items(), key=lambda kv: -kv[1]):
            print(f"    {count:3d}/{res['pack_totals'][pack]:<4d} {pack}")

    if res.get("chain"):
        n, size, runs = res["chain_reached"], res["chain_size"], res["runs"]
        print(f"\n  === chain '{res['chain']}': {size} events ===")
        print(f"    events ever eligible         {res['chain_ever_elig']}/{size}")
        print(f"    events ever fired            {n}/{size}")
        print(f"    runs where any was eligible  {res['chain_runs_elig']}/{runs}")
        print(f"    runs where any fired         {res['chain_runs_fired']}/{runs}")
        print(f"    draws it was eligible for    {res['chain_draws']}")
        print(f"    times picked                 {res['chain_picks']}")
        print(f"    median share of those draws  {res['chain_median_share']:.2f}%")
        won = res["chain_picks"] / res["chain_draws"] * 100 if res["chain_draws"] else 0.0
        print(f"    win rate on eligible draws   {won:.1f}%")
        print("\n    per-event fires:")
        for eid, count in sorted(res["chain_fire_totals"].items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"      {count:4d}  {eid}")


def run_assertions(res: dict) -> int:
    violations: List[str] = []
    never = len(res["never"])
    if res["runs"] != RUNS:
        print(f"  (skipping the never-fired gate: calibrated for n={RUNS}, "
              f"this run was n={res['runs']})")
    elif never > MAX_NEVER_FIRED:
        violations.append(
            f"{never} events never fired in {res['runs']} runs (> {MAX_NEVER_FIRED}) -- "
            f"more written content has fallen out of reach"
        )
    if res["median_share"] < MIN_ARC_SHARE:
        violations.append(
            f"Arc draw-share {res['median_share']:.1f}% (< {MIN_ARC_SHARE:.0f}%) -- "
            f"the deck is handing out even more filler than it was"
        )

    print("\n=== COVERAGE ASSERTIONS ===")
    if not violations:
        print("  All coverage gates passed.")
    for v in violations:
        print(f"  VIOLATION: {v}")
    return len(violations)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-n", "--runs", type=int, default=RUNS,
                    help=f"complete playouts to audit (default {RUNS})")
    ap.add_argument("-s", "--strategy", default="random",
                    help="choice strategy, as in sim_bot (default random)")
    ap.add_argument("--seed", type=int, default=0, help="first seed (default 0)")
    ap.add_argument("--ambient-slots", type=int,
                    default=-1 if AMBIENT_SLOTS_PER_DAY is None else AMBIENT_SLOTS_PER_DAY,
                    help="ambient slots per day; -1 disables the quota, 0 is strictest "
                         f"(default: whatever engine/selector ships, currently "
                         f"{'disabled' if AMBIENT_SLOTS_PER_DAY is None else AMBIENT_SLOTS_PER_DAY})")
    ap.add_argument("--district", default=PROTOTYPE_DISTRICT,
                    help="district to place slots in (default: whatever engine/selector "
                         f"ships, currently {PROTOTYPE_DISTRICT or 'none'})")
    ap.add_argument("--district-slots", type=int, default=0,
                    help="how many of the day's slots are placed in --district; "
                         "0 (default) is the unplaced baseline")
    ap.add_argument("--district-every", type=int, default=1,
                    help="visit --district only every Nth day (default 1, every day); "
                         "stands in for how often a player would actually go there")
    ap.add_argument("--shelf-ambient", dest="shelf_ambient", action="store_true", default=None,
                    help="force district shelves to carry neutral ambient filler")
    ap.add_argument("--no-shelf-ambient", dest="shelf_ambient", action="store_false",
                    help="force bare shelves (district content only)")
    ap.add_argument("--chain", help="event-id prefix to report eligibility/fire stats for")
    ap.add_argument("--track-district", help="report eligibility/fire stats for a district's "
                                             "own events (collision-free; prefer over --chain)")
    ap.add_argument("--assert", dest="do_assert", action="store_true",
                    help="enable the coverage gate; exit 1 on violation")
    ap.add_argument("--parity", action="store_true",
                    help="check this playout against sim_bot's on the first 3 seeds")
    args = ap.parse_args()

    if args.shelf_ambient is not None:
        selector_module.SHELF_INCLUDES_AMBIENT = args.shelf_ambient

    if args.parity:
        mismatches = parity_check(args.strategy, [args.seed + i for i in range(3)])
        print(f"parity vs sim_bot: {3 - len(mismatches)}/3 seeds identical")
        for m in mismatches:
            print(f"  MISMATCH: {m}")
        if mismatches:
            return 1

    slots = None if args.ambient_slots < 0 else args.ambient_slots
    res = run_audit(args.runs, args.strategy, args.seed, ambient_slots=slots,
                    district=args.district, district_slots=args.district_slots,
                    district_every=args.district_every,
                    chain=args.chain, track_district=args.track_district)
    print(f"ambient slots/day: {'unbudgeted' if slots is None else slots}")
    placed = args.district if args.district_slots > 0 else None
    print(f"district placement: {args.district_slots} slot(s) in "
          f"{placed or 'nowhere (unplaced baseline)'}"
          + (f" every {args.district_every} day(s)" if placed and args.district_every > 1 else "")
          + (f", shelf {'includes' if selector_module.SHELF_INCLUDES_AMBIENT else 'excludes'} ambient"
             if placed else ""))
    report(res)
    if args.do_assert:
        return 1 if run_assertions(res) else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
