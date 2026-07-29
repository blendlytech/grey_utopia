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
                                                      # (sweeps 5 seed bases, ~2.5 min)
    python tests/coverage_audit.py --parity           # cross-check against sim_bot
    python tests/coverage_audit.py --union            # what NO strategy reaches
    python tests/coverage_audit.py --ambient-slots 0  # A/B the ambient quota
    # A/B the A1 map: --placement control is the same run with the map switched
    # off and the same RNG draws spent, so the difference is the map alone
    python tests/coverage_audit.py --track-district the_archive
    python tests/coverage_audit.py --placement control --track-district the_archive
    python tests/coverage_audit.py --track-pack ambitions_pack
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
from engine.districts import (
    PLACEMENT_RATE, apply_placements, auto_placement, clear_placements,
    district_ids)
from engine.selector import (
    AMBIENT_SLOTS_PER_DAY, district_for_slot, effective_weight, eligible_pool,
    index_library, is_ambient, select_event,
)
from engine.stats import Character, create_starter_fixer
from tests.sim_bot import (
    DATA_DIR, STRATEGIES, load_all_events, pick_choice_by_strategy)

# How the audit stands in for a player's morning placement.
#
#   auto    -- the shipped policy (engine.districts.auto_placement), i.e. what
#              sim_bot and pargate are scoring. The default, because placement
#              is live now and an audit of a configuration nobody plays is worth
#              nothing.
#   control -- draws the same placement and throws it away. This is the honest
#              A/B partner for `auto`: placement costs two RNG draws a day, so a
#              no-placement run that skips them diverges on stream shuffle as
#              well as on the map, and the two effects cannot be told apart.
#              Note a control is only comparable within one policy -- changing
#              how many draws auto_placement spends moves this column too.
#   pre-a1  -- no placement, no draw. Reproduces the recorded pre-A1 baseline
#              exactly; use it to check the board's §6 table, not to A/B the map.
#   fixed   -- Phase 1's scripted rig (--district / --district-slots /
#              --district-every), kept because a hand-set cadence is still the
#              cleanest way to ask "what would visiting every Nth day do?".
PLACEMENT_MODES = ("auto", "control", "pre-a1", "fixed")

# The content this audit exists to protect: anything a player is walking a thread
# toward. Ambient/micro filler is everything this is measured against.
#
# The tag set is a *fallback*. It cannot answer the question on its own -- it
# scored `ambitions_pack` (three 8-link chains) and `cast_expansion_pack` (five
# character threads) at 0.0% arc, because both are tagged with theme words
# (existential/undercity/job) rather than with anything about structure. That
# blocked two windows and would have gone on getting worse: A1 shelves arc
# content, so a blind classifier makes MIN_ARC_SHARE fall as the item succeeds.
# `Event.arc` is the explicit answer, set per pack in the content; the union is
# taken so the gate can only ever see *more* arc than it used to, never less.
ARC_TAGS = frozenset({"flagship", "arc", "npc", "betrayal", "resistance", "relationship"})


def is_arc(event) -> bool:
    return event.arc or bool(ARC_TAGS.intersection(event.tags))

RUNS = 40

# The never-fired gate is asserted on the MEAN over this many seed bases, spaced
# this far apart -- so the default sweep is seeds 0, 100, 200, 300, 400, which is
# exactly the five-base measurement A1_DESIGN §9.3 and the board's §6 quote.
#
# It was a single pinned seed for three windows, and §8.7 measured what that was
# worth: the same deck, same config, n=40, scored 107 / 79 / 90 / 88 / 95 across
# those bases -- a 28-event spread on the live column and 47 on the control. Every
# content decision of Phases 2, 3 and 3b was argued against differences inside
# that band. A mean of five costs four extra audits (~2 min) and is the cheapest
# real fix available to this instrument.
ASSERT_SEED_BASES = 5
ASSERT_SEED_STRIDE = 100

# Gate thresholds. These guard the measured baseline against regression; they are
# deliberately NOT F1's targets (< 70 never-fired, > 35% arc draw-share), which
# were written against a scratch harness and which F1 then proved unreachable by
# any pool-composition lever. Both numbers below are **regression guards re-based
# on the measured mean of the shipped 2026-07-28 (A1 Phase 3c) build**, not
# targets the deck is failing. Neither is aspirational; if a window wants an
# aspiration it should write it in the backlog, not here.
#
# They are only meaningful at RUNS runs -- coverage compounds hard with sample
# size (209 never-fired at n=5, ~97 at n=40, 69 at n=100 on the same deck), so
# quoting either without its N says nothing. The gate refuses to assert at any
# other N, and the seed bases are pinned so the figures are comparable across
# windows.
#
# --- Why the single deck-wide count was replaced by two numbers -------------
#
# `MAX_NEVER_FIRED = 85` was red for two consecutive windows (Phase 3 measured
# 91.8, Phase 3b 113.2) and no branch either window considered would have made it
# green. Splitting it says why: at Phase 3b, 76.2 of those 113.2 events **never
# passed their preconditions in any of the 40 runs**. No weight, placement or
# pool-composition lever can reach those, so two thirds of what the gate measured
# was not what the gate's own error message claimed ("more written content has
# fallen out of reach"). Raising 85 to ~118 would have been the coverage-side
# equivalent of lowering PLACEMENT_RATE to whatever ships; splitting it gives two
# numbers that each have a mechanism and a lever.
#
# **The pair is the gate. Neither half is a gate on its own**, and that is
# measured, not assumed: re-running F1's disaster config (`--ambient-slots 0`,
# the one that scored 174 never-fired and broke the balance gate) scores
# starved 153.0 and outcompeted **24.4** -- i.e. it looks like an *improvement*
# on the outcompeted number alone, because starving the pool means fewer events
# are ever offered and so fewer can lose. The converse holds too: flooding the
# deck with always-eligible repeatables (Phase 3b, §9.3) moves outcompeted up
# while leaving starvation flat. Gate one and the other is free to run away.
#
# --- Where these two numbers come from --------------------------------------
#
# Shipped build, live placement, mean of 5 seed bases at n=40:
#     never fired 101.8  =  starved 67.0  +  outcompeted 34.8
# (Phase 3b, for comparison: 113.2 = 76.2 + 37.0.)
#
# Headroom is ~10-20%, which is wider than the ~6% F1 and F2 left, and the reason
# is measured: this build's per-base spread is 23 events on outcompeted
# (25/28/47/48/26) where Phase 3b's was 4 (38/38/37/38/34). The narrow spread was
# not the metric being stable -- it was ambitions_pack losing *every* draw in
# *every* seed, which is a reliable failure. Now that the pack competes, which of
# its 24 links fire varies by seed, and an ordinary content addition can shift the
# 5-base mean several events on stream reshuffle alone. A gate tight enough to
# trip on that is a gate that gets ignored.
MAX_OUTCOMPETED = 42     # measured 34.8
MAX_STARVED = 76         # measured 67.0

# NOT tightened alongside it, deliberately, even though the measured figure went
# 24.7% -> 25.7%. This metric changed *definition* in the same window: it now
# medians over unplaced draws only, because a placed draw samples a 14-event shelf
# and folding the two together compares nothing to nothing. Worse, ARC_TAGS scores
# both shelves at 0.0% arc -- ambitions_pack is tagged existential/undercity and
# cast_expansion_pack job/undercity, so the classifier cannot see the two most
# thread-heavy packs in the deck. A gate should not be tightened onto a number
# whose definition moved under it. See §5's note on the missing arc classification.
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
    arc = sum(w for e, w in weights if is_arc(e))
    return arc / total


def audit_run(strategy: str, seed: int, max_days: int = 100,
              ambient_slots: Optional[int] = AMBIENT_SLOTS_PER_DAY,
              placement: str = "auto",
              district: Optional[str] = None,
              district_slots: int = 0,
              district_every: int = 1,
              chain: Optional[set] = None) -> dict:
    """One instrumented playout. RNG consumption mirrors sim_bot exactly.

    `ambient_slots` overrides the shipped quota so a window can bound the lever
    without editing engine constants: None restores pre-quota behaviour, 0 is
    the strictest the quota can be (ambient only when nothing else is eligible).

    `placement` selects how the morning placement step is played; see
    PLACEMENT_MODES. `district` / `district_slots` / `district_every` only apply
    under `fixed`, where they place the day's first `district_slots` slots in
    `district` on every `district_every`-th day.

    In Phase 1 placement did not exist and the cadence lived here as a stand-in
    for a player deciding where to stand. It is a real morning step now, so the
    default mode calls the same `engine.districts.auto_placement` the game's
    auto-play and `sim_bot` call -- this loop no longer invents its own player.

    `chain` is a set of event ids to track separately. It splits "never eligible"
    from "eligible but never picked" -- the distinction F1 proved is the whole
    ballgame, and the one a bare never-fired count cannot make.
    """
    rng = random.Random(seed)
    character = create_starter_fixer()
    all_events = load_all_events()
    index_library(all_events)

    fired: List[str] = []          # every event a choice was resolved on, in order
    # Two different questions, and conflating them cost a measurement: the deck's
    # pool is what an *unplaced* slot sees, and a placed slot sees a shelf that is
    # deliberately an order of magnitude smaller. Recording "the day's first draw"
    # started reporting shelf sizes the moment auto_placement began placing slot 0.
    pool_sizes: List[int] = []     # eligible deck at each day's first unplaced draw
    shelf_sizes: List[int] = []    # eligible shelf at each placed draw
    # Arc draw-share is split the same way and for the same reason. The gate is
    # calibrated on draws against the whole deck, which is what every draw was
    # before placement existed; folding placed draws into the same median makes
    # the number incomparable with the recorded baseline, and understates it
    # besides -- ARC_TAGS cannot see that cast_expansion_pack's five character
    # threads are arc content, because they are tagged job/undercity/existential.
    shares: List[float] = []       # arc weight share, unplaced draws
    shelf_shares: List[float] = [] # arc weight share, placed draws
    ambient_fired = 0              # ambient picks, for the quota's own accounting
    arc_fired = 0                  # picks that landed on arc content
    chain_elig_draws = 0           # draws in which any tracked event was eligible
    chain_shares: List[float] = [] # tracked events' combined share of a draw's weight
    chain_elig_ids: set = set()    # tracked events that were eligible at least once
    chain_fired_ids: set = set()   # tracked events that actually fired
    # Deck-wide eligibility, which is what splits a never-fired event into one the
    # selector *could* have shown and one whose preconditions never came true. F1
    # established that distinction is the whole ballgame (50 of 54 unreached
    # non-legacy storylets were gated behind a flag only another storylet grants),
    # but it was only ever computed for a --track-* subset. It is free deck-wide:
    # an unplaced draw's pool is already every gate-passing event, and there is at
    # least one unplaced draw a day because auto_placement takes at most slot 0.
    eligible_ids: set = set()

    while character.day < max_days and not character.dead:
        ending = check_endings(character)
        if ending:
            character.ending = ending
            character.dead = True
            break

        slots = 3 if (character.get("Physical_Integrity") >= 30 and character.get("Mental_Decay") <= 80) else 2

        # The morning placement step. Every mode except pre-a1 spends the same
        # RNG draw whether or not it uses the result, so the modes stay
        # comparable seed for seed and a difference between two of them is the
        # map rather than a reshuffled stream.
        clear_placements(character)
        drawn = {} if placement == "pre-a1" else auto_placement(rng, character, slots)
        if placement == "auto":
            apply_placements(character, drawn)
        elif placement == "fixed" and district and character.day % district_every == 0:
            apply_placements(character, {s: district for s in range(district_slots)})

        fired_today: set = set()
        ambient_today = 0
        deck_pool_seen = False
        for slot in range(slots):
            budget = None if ambient_slots is None else ambient_slots - ambient_today
            placed = district_for_slot(character, slot)
            # The pool the selector is about to sample from, measured through the
            # engine's own filter so the instrument cannot drift from the game.
            pool = eligible_pool(all_events, character, character.day, fired_today, budget, placed)
            eligible_ids.update(e.id for e in pool)
            if placed is not None:
                shelf_sizes.append(len(pool))
            elif not deck_pool_seen:
                pool_sizes.append(len(pool))
                deck_pool_seen = True
            share = arc_share(pool, character)
            if share is not None:
                (shelf_shares if placed is not None else shares).append(share)
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
            if is_arc(ev):
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
        "shelf_sizes": shelf_sizes,
        "shares": shares,
        "shelf_shares": shelf_shares,
        "eligible_ids": eligible_ids,
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
              placement: str = "auto",
              district: Optional[str] = None,
              district_slots: int = 0,
              district_every: int = 1,
              chain: Optional[str] = None,
              track_district: Optional[str] = None,
              track_pack: Optional[str] = None) -> dict:
    all_events = load_all_events()
    deck_ids = {e.id for e in all_events}
    packs = pack_index()

    # What to report separately. A district id answers "is this shelf a vending
    # machine?"; a pack answers "is this chain advancing?" -- and from Phase 2 on
    # those are different questions, because a shelf holds a chain *and* the
    # texture that keeps it from being a vending machine. An id prefix is the
    # general escape hatch and a sharp one: 'amb_' matches the 24 ambitions
    # events AND 42 unrelated volume ambients.
    tracked_ids: Optional[set] = None
    label = None
    if track_district:
        tracked_ids = {e.id for e in all_events if e.district == track_district}
        label = f"district {track_district}"
    elif track_pack:
        tracked_ids = {eid for eid, pack in packs.items()
                       if pack == track_pack and eid in deck_ids}
        label = f"pack {track_pack}"
    elif chain:
        tracked_ids = {e.id for e in all_events if e.id.startswith(chain)}
        label = f"prefix {chain!r}"

    fire_totals: Counter = Counter()
    unique_per_run: List[int] = []
    repeat_fracs: List[float] = []
    pool_sizes: List[int] = []
    shelf_sizes: List[int] = []
    shares: List[float] = []
    shelf_shares: List[float] = []
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
    eligible_ids: set = set()

    for i in range(runs):
        res = audit_run(strategy, seed0 + i, ambient_slots=ambient_slots,
                        placement=placement, district=district,
                        district_slots=district_slots,
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
        shelf_sizes.extend(res["shelf_sizes"])
        shares.extend(res["shares"])
        shelf_shares.extend(res["shelf_shares"])
        eligible_ids |= res["eligible_ids"]
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
    # The two halves of never-fired, and only one of them is a selector problem.
    # `starved` never passed its preconditions in any of the `runs` playouts, so no
    # weight, placement or pool-composition lever can reach it -- the fix is always
    # authoring or a gate edit. `outcompeted` sat in a real draw and lost it, which
    # is the failure A1 exists to attack and the only half a gate can usefully bound.
    starved = [eid for eid in never if eid not in eligible_ids]
    outcompeted = [eid for eid in never if eid in eligible_ids]

    return {
        "deck": len(deck_ids),
        "packs": len(pack_totals),
        "runs": runs,
        "strategy": strategy,
        "never": never,
        "starved": starved,
        "outcompeted": outcompeted,
        "by_pack": by_pack,
        "pack_totals": pack_totals,
        "pack_of": packs,
        "median_days": statistics.median(days),
        "median_pool": statistics.median(pool_sizes) if pool_sizes else 0,
        "median_shelf": statistics.median(shelf_sizes) if shelf_sizes else 0,
        "placed_draws": len(shelf_sizes),
        "median_share": statistics.median(shares) * 100 if shares else 0.0,
        "median_shelf_share": statistics.median(shelf_shares) * 100 if shelf_shares else 0.0,
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
    print(f"  median eligible pool / day   {res['median_pool']:.0f}  (unplaced draws)")
    if res["placed_draws"]:
        print(f"  median eligible shelf        {res['median_shelf']:.0f}  "
              f"({res['placed_draws']} placed draws)")
    print(f"  median arc draw-share        {res['median_share']:.1f}%  (unplaced draws)")
    if res["placed_draws"]:
        print(f"  median arc shelf-share       {res['median_shelf_share']:.1f}%  (placed draws)")
    print(f"  unique events per run        {res['median_unique']:.0f} "
          f"({res['median_unique'] / deck * 100:.1f}% of deck)")
    print(f"  repeat-pick fraction         {res['repeat_frac']:.1f}%")
    print(f"  ambient share of picks       {res['ambient_pick_share']:.1f}%")
    print(f"  arc share of picks           {res['arc_pick_share']:.1f}%")
    print(f"  events never fired           {never} ({never / deck * 100:.1f}%)")
    print(f"    never eligible (starved)   {len(res['starved'])}  "
          f"-- preconditions never met; no selector lever reaches these")
    print(f"    eligible, never picked     {len(res['outcompeted'])}  "
          f"-- lost real draws; this is the half a gate can move")

    if never:
        print("\n  never fired, by pack:  (total = starved + outcompeted)")
        starved_by_pack: Counter = Counter(
            res["pack_of"].get(eid, "?") for eid in res["starved"])
        for pack, count in sorted(res["by_pack"].items(), key=lambda kv: -kv[1]):
            s = starved_by_pack.get(pack, 0)
            print(f"    {count:3d}/{res['pack_totals'][pack]:<4d} {pack:<24s} "
                  f"= {s} starved + {count - s} outcompeted")

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


def union_across_strategies(runs: int, seed0: int, **kwargs) -> dict:
    """Never-fired under EVERY strategy -- content no kind of player reaches.

    Every other number this file prints is single-strategy, and single-strategy
    coverage is wrong in *both* directions (measured 2026-07-29, n=40 seed 0):

        | never fired | random 105 | cautious 191 | reckless 106 | greedy 135 |
        |             | **union 61** |

    `random` picks uniformly, so it spreads across mutually-exclusive branches --
    but it dies ~25 days earlier than any deliberate strategy (median 34 vs
    55-63), so it under-reports day-gated content, and it fumbles branch-gated
    chain heads (§10.5). Deliberate bots live long enough for the day gates but
    **always make the same choice**, so they collapse every either/or in the deck:
    `ambitions_pack` reads 17/24 unreached under `random` and 8/24 under `greedy`,
    because a deliberate bot picks one ambition every run and the other two chains
    never happen.

    Neither is the player. The union is the honest floor: an event in it is
    unreachable however you play. It is what "is this content reachable?" should
    be answered with -- see BACKLOG_HANDOFF §5 (2026-07-29) for the measurement
    that retired F6 on the strength of it.
    """
    per: Dict[str, dict] = {}
    for strategy in STRATEGIES:
        per[strategy] = run_audit(runs, strategy, seed0, **kwargs)
    never = set.intersection(*(set(r["never"]) for r in per.values()))
    starved = set.intersection(*(set(r["starved"]) for r in per.values()))
    return {"per_strategy": per, "never": sorted(never), "starved": sorted(starved),
            "deck": next(iter(per.values()))["deck"],
            "pack_of": next(iter(per.values()))["pack_of"]}


def report_union(u: dict) -> None:
    deck = u["deck"]
    print(f"\n=== reachability across all {len(u['per_strategy'])} strategies ===")
    print(f"  {'strategy':<12s}{'never':>8s}{'starved':>9s}{'outcompeted':>13s}")
    for strategy, res in u["per_strategy"].items():
        print(f"  {strategy:<12s}{len(res['never']):>8d}{len(res['starved']):>9d}"
              f"{len(res['outcompeted']):>13d}")
    n = len(u["never"])
    print(f"  {'UNION':<12s}{n:>8d}{len(u['starved']):>9d}"
          f"{'':>13s}  <- unreachable however you play ({n / deck * 100:.1f}%)")
    by_pack: Counter = Counter(u["pack_of"].get(eid, "?") for eid in u["never"])
    if by_pack:
        print("\n  union-unreachable by pack:")
        for pack, count in sorted(by_pack.items(), key=lambda kv: -kv[1]):
            print(f"    {count:3d}  {pack}")


def sweep_seed_bases(runs: int, strategy: str, seed0: int, primary: dict,
                     **kwargs) -> dict:
    """Re-measure the never-fired metrics at ASSERT_SEED_BASES bases and average.

    `primary` is the already-computed audit at `seed0`, reused as base 0 so the
    sweep costs four extra audits rather than five. Everything else about the
    configuration is passed straight through, so `--assert --placement control`
    sweeps the control column and the two remain comparable.
    """
    bases = [seed0 + i * ASSERT_SEED_STRIDE for i in range(ASSERT_SEED_BASES)]
    rows = [(bases[0], primary)]
    for base in bases[1:]:
        rows.append((base, run_audit(runs, strategy, base, **kwargs)))
    return {
        "bases": bases,
        "never": [len(r["never"]) for _, r in rows],
        "starved": [len(r["starved"]) for _, r in rows],
        "outcompeted": [len(r["outcompeted"]) for _, r in rows],
    }


def report_sweep(sweep: dict) -> None:
    print(f"\n=== never-fired over {len(sweep['bases'])} seed bases "
          f"(n={RUNS} each) ===")
    header = "".join(f"{b:>8d}" for b in sweep["bases"])
    print(f"  {'seed base':<22s}{header}{'mean':>10s}")
    for key, label in (("never", "never fired"),
                       ("starved", "  never eligible"),
                       ("outcompeted", "  outcompeted")):
        cells = "".join(f"{v:>8d}" for v in sweep[key])
        print(f"  {label:<22s}{cells}{statistics.mean(sweep[key]):>10.1f}")


def run_assertions(res: dict, sweep: Optional[dict] = None) -> int:
    violations: List[str] = []
    if res["runs"] != RUNS:
        print(f"  (skipping the never-fired gate: calibrated for n={RUNS}, "
              f"this run was n={res['runs']})")
    elif sweep is None:
        print("  (skipping the never-fired gate: it asserts on a seed-base mean, "
              "which --assert computes)")
    else:
        mean = statistics.mean(sweep["outcompeted"])
        if mean > MAX_OUTCOMPETED:
            violations.append(
                f"{mean:.1f} events eligible but never fired, mean of "
                f"{len(sweep['bases'])} seed bases at n={res['runs']} "
                f"(> {MAX_OUTCOMPETED}) -- written content is losing every draw "
                f"it is offered"
            )
        starved = statistics.mean(sweep["starved"])
        if starved > MAX_STARVED:
            violations.append(
                f"{starved:.1f} events never even eligible, mean of "
                f"{len(sweep['bases'])} seed bases at n={res['runs']} "
                f"(> {MAX_STARVED}) -- a gate or flag source has gone missing"
            )
    if res["median_share"] < MIN_ARC_SHARE:
        violations.append(
            f"Arc draw-share {res['median_share']:.1f}% (< {MIN_ARC_SHARE:.0f}%) -- "
            f"the deck is handing out even more filler than it was"
        )

    print("\n=== COVERAGE ASSERTIONS ===")
    # The gate is deliberately single-strategy and stays that way: it is a fast
    # regression guard on a calibrated baseline, and running four strategies x
    # five seed bases would roughly quadruple it. But anyone reading a raw
    # never-fired count off this output is reading a number that is wrong in both
    # directions, so point at the metric that is not.
    print(f"  (these gate `{res['strategy']}` only. A raw never-fired count is a "
          f"ceiling, not a\n   reachability figure -- run --union for the events "
          f"no strategy reaches.)")
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
    ap.add_argument("--placement", choices=PLACEMENT_MODES, default="auto",
                    help="how the morning placement step is played: auto (default, "
                         "the shipped policy), control (same RNG draws, map off -- "
                         "the honest A/B partner), pre-a1 (no placement at all), "
                         "fixed (scripted, see --district*)")
    ap.add_argument("--district", default=None,
                    help="district to place slots in under --placement fixed")
    ap.add_argument("--district-slots", type=int, default=0,
                    help="how many of the day's slots --placement fixed places")
    ap.add_argument("--district-every", type=int, default=1,
                    help="under --placement fixed, visit only every Nth day (default 1)")
    ap.add_argument("--shelf-ambient", dest="shelf_ambient", action="store_true", default=None,
                    help="force district shelves to carry neutral ambient filler")
    ap.add_argument("--no-shelf-ambient", dest="shelf_ambient", action="store_false",
                    help="force bare shelves (district content only)")
    ap.add_argument("--chain", help="event-id prefix to report eligibility/fire stats for")
    ap.add_argument("--track-district", help="report eligibility/fire stats for a district's "
                                             "own events (collision-free; prefer over --chain)")
    ap.add_argument("--track-pack", help="report eligibility/fire stats for one pack file's "
                                         "events, e.g. ambitions_pack")
    ap.add_argument("--union", action="store_true",
                    help="re-run every strategy and report the events none of them "
                         "reach -- the honest answer to 'is this content reachable?', "
                         "since single-strategy coverage misleads both ways")
    ap.add_argument("--assert", dest="do_assert", action="store_true",
                    help="enable the coverage gate; exit 1 on violation")
    ap.add_argument("--parity", action="store_true",
                    help="check this playout against sim_bot's on the first 3 seeds")
    args = ap.parse_args()

    if args.shelf_ambient is not None:
        selector_module.SHELF_INCLUDES_AMBIENT = args.shelf_ambient

    if args.placement == "fixed" and not (args.district and args.district_slots > 0):
        ap.error("--placement fixed needs --district and --district-slots > 0")

    if args.parity:
        mismatches = parity_check(args.strategy, [args.seed + i for i in range(3)])
        print(f"parity vs sim_bot: {3 - len(mismatches)}/3 seeds identical")
        for m in mismatches:
            print(f"  MISMATCH: {m}")
        if mismatches:
            return 1

    slots = None if args.ambient_slots < 0 else args.ambient_slots
    res = run_audit(args.runs, args.strategy, args.seed, ambient_slots=slots,
                    placement=args.placement, district=args.district,
                    district_slots=args.district_slots,
                    district_every=args.district_every,
                    chain=args.chain, track_district=args.track_district,
                    track_pack=args.track_pack)
    print(f"ambient slots/day: {'unbudgeted' if slots is None else slots}")
    if args.placement == "fixed":
        where = (f"scripted -- {args.district_slots} slot(s) in {args.district}"
                 + (f" every {args.district_every} day(s)" if args.district_every > 1 else ""))
    elif args.placement == "auto":
        n = len(district_ids())
        odds = PLACEMENT_RATE if n else 0.0
        # Derived, not quoted from a constant: this line used to print the
        # *intended* cadence rather than the one the policy actually produces,
        # and so read "every ~5 days" on a seven-district map visiting each
        # district every twelfth day.
        every = n / PLACEMENT_RATE if n and PLACEMENT_RATE else 0.0
        where = (f"auto -- one slot on {odds * 100:.0f}% of days, uniform over {n} district(s); "
                 f"each visited every ~{every:.0f} days")
    else:
        where = f"{args.placement} -- every slot unplaced"
    print(f"placement: {where}"
          + (f", shelf {'includes' if selector_module.SHELF_INCLUDES_AMBIENT else 'excludes'}"
             f" neutral ambient" if args.placement != "pre-a1" else ""))
    report(res)
    if args.union:
        report_union(union_across_strategies(
            args.runs, args.seed, ambient_slots=slots, placement=args.placement,
            district=args.district, district_slots=args.district_slots,
            district_every=args.district_every))
    if args.do_assert:
        sweep = None
        if args.runs == RUNS:
            sweep = sweep_seed_bases(
                args.runs, args.strategy, args.seed, res, ambient_slots=slots,
                placement=args.placement, district=args.district,
                district_slots=args.district_slots,
                district_every=args.district_every)
            report_sweep(sweep)
        return 1 if run_assertions(res, sweep) else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
