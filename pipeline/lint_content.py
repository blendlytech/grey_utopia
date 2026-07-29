"""lint_content.py -- Static content linter for GREY UTOPIA event packs.

Checks that cheap mistakes never reach players:
  ERRORS (exit 1):
    - duplicate event ids across packs
    - events that fail engine schema validation
    - unknown stats in prob mods / deltas (caught by engine loader)
    - flags required by preconditions that no event ever sets
    - item_rewards / items_consumed ids missing from items.json
    - resolver endings missing narrative text in endings.json
  WARNINGS (exit 0):
    - endings.json entries no code path can return
    - success/failure branch missing narrative text on risky choices
    - probability coefficients large enough to saturate the clamp

Run: python pipeline/lint_content.py
"""
from __future__ import annotations
import os
import sys
import json
import glob
from collections import Counter
from typing import Dict, List, Set, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine import steward
from engine.events import load_events
from engine.stats import STAT_SPEC
from engine.resolver import P_MAX

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))


def event_pack_files() -> List[str]:
    return sorted(
        f for f in glob.glob(os.path.join(DATA_DIR, "events", "*.json"))
        if os.path.basename(f) != "endings.json"
    )


def practical_stat_range(stat: str) -> float:
    """Realistic swing range for probability-mod sanity checks."""
    if stat == "Wealth":
        return 50_000.0  # nominal mid-game bankroll, not the 1e9 hard cap
    lo, hi, _ = STAT_SPEC.get(stat, (0.0, 100.0, 0.0))
    return hi - lo

RESOLVER_ENDINGS = {
    "TERMINAL_overdose_death",
    "TERMINAL_syndicate_ledger",
    "TERMINAL_institutionalized",
    "TERMINAL_synthetic_detachment",
    "GOOD_offgrid_escape",
    "GOOD_small_real_things",
    "NEUTRAL_the_open_door",
    "NEUTRAL_stewards_shepherd",
    "NEUTRAL_cashed_out_compliance",
    "NEUTRAL_alienation_empty_suite",
    "NEUTRAL_the_long_grey",
    "TERMINAL_gardeners_winter",
    "GOOD_the_advocate",
    "NEUTRAL_keeper_of_the_switch",
}

# Flags granted by engine/server mechanics rather than event branches:
# resolver.apply_dose sets the overdose pair; end_of_day_decay mints
# clock_<name>_expired flags for every clock content ever starts; steward.begin_day
# arms the filing flag at the day boundary (A3), which is how a scheduled event is
# expressed in a deck whose only scheduling primitive is `day`.
ENGINE_GRANTED_FLAGS: Set[str] = {
    "near_overdose", "flag_overdose_death", steward.FILING_DUE_FLAG,
}

# Comparison operators engine.events.compare_op actually implements.
VALID_OPS: Set[str] = {">=", "<=", ">", "<", "==", "!="}

# F9: the quantities a `{"relationship": ...}` condition may read. `strength` is
# absent on purpose and its absence is enforced -- see engine/events.py.
VALID_REL_FIELDS: Set[str] = {"satisfaction", "reinforcements"}


def _relationship_gate_sites(event: dict):
    """Yield (where, condition) for every relationship gate on one event.

    Gates live at two sites with two different keys -- events use
    `preconditions`, choices use `requires` -- and the linter's main loop only
    walks the first. Ten of the deck's sixteen satisfaction gates are at the
    second, which is part of why the board recorded the count as six.
    """
    def group(req, where):
        if not isinstance(req, dict):
            return
        for grp in ("all", "any", "none"):
            for cond in req.get(grp, []) or []:
                if isinstance(cond, dict) and "relationship" in cond:
                    yield where, cond

    for key in ("preconditions", "requires"):
        yield from group(event.get(key), "<event>")
    for ch in event.get("choices", []) or []:
        for key in ("requires", "preconditions"):
            yield from group(ch.get(key), ch.get("id", "?"))

# Phrases that mean the transaction did NOT happen. A branch whose prose says the
# seller refused, and which still applies a 'dose', charges the player for a
# substance they never obtained -- and 'dose' is not cosmetic: resolver.apply_dose
# routes it through overdose_probability, so such a branch can kill a run over a
# purchase that fell through. Found live in
# volume_vice_pawn_for_a_hit/pawn_the_keepsake (2026-07-27), where the failure
# branch was a copy of the success branch's effects: the broker refuses, you leave
# empty-handed, and the engine doses you anyway.
NO_DEAL_MARKERS: Tuple[str, ...] = (
    "refuses", "refused", "empty-handed", "empty handed", "no sale",
    "won't sell", "will not sell", "doesn't sell", "does not sell",
    "turns you away", "turned you away", "backs out", "backed out",
    "changes his mind", "changes her mind", "nothing to buy", "nothing left to sell",
)


def lint() -> int:
    errors: List[str] = []
    warnings: List[str] = []

    id_counts: Counter = Counter()
    flags_set: Set[str] = set(ENGINE_GRANTED_FLAGS)
    flags_cleared: Set[str] = set()
    flags_required: Dict[str, List[str]] = {}
    items_referenced: Dict[str, List[str]] = {}
    clocks_started: Set[str] = set()
    rel_names_used: Dict[str, List[str]] = {}
    districts_used: Dict[str, List[str]] = {}

    pack_files = event_pack_files()

    total_events = 0
    for filepath in pack_files:
        name = os.path.basename(filepath)
        try:
            events = load_events(filepath)
        except Exception as err:
            errors.append(f"{name}: failed engine schema validation -- {err}")
            continue

        with open(filepath, "r", encoding="utf-8") as fh:
            raw = json.load(fh).get("events", [])

        total_events += len(events)
        for e in raw:
            eid = e.get("id", "?")
            id_counts[eid] += 1

            if e.get("district") is not None:
                districts_used.setdefault(e["district"], []).append(f"{name}:{eid}")

            pre = e.get("preconditions", {})
            for grp in ("all", "any", "none"):
                for cond in pre.get(grp, []):
                    if "flag" in cond and grp != "none" and cond.get("value", True):
                        flags_required.setdefault(cond["flag"], []).append(f"{name}:{eid}")
                    # compare_op raises at runtime on anything outside this set,
                    # and a non-numeric 'day' crashes float() in the selector.
                    op = cond.get("op")
                    if op is not None and op not in VALID_OPS:
                        errors.append(f"{name}:{eid}: invalid precondition op {op!r} -- engine accepts {sorted(VALID_OPS)}")
                    if "day" in cond and not isinstance(cond["day"], (int, float)):
                        errors.append(f"{name}:{eid}: 'day' precondition must be numeric, got {cond['day']!r}")

            # F9: a satisfaction gate reads `field` to pick which quantity of the
            # bond it tests, and engine.events falls back to `satisfaction` for
            # anything it does not recognise. A typo there is silent and would
            # re-create the defect F9 exists to remove -- a gate that reads a
            # decaying value when its author meant the monotonic one -- so the
            # fallback is allowed at runtime and forbidden here.
            for where, req in _relationship_gate_sites(e):
                field = req.get("field", "satisfaction")
                if field not in VALID_REL_FIELDS:
                    errors.append(
                        f"{name}:{eid}:{where}: relationship gate field {field!r} unknown "
                        f"-- engine accepts {sorted(VALID_REL_FIELDS)} (it silently reads "
                        f"satisfaction for anything else)")
                if field == "reinforcements" and not float(req.get("value", 0)).is_integer():
                    errors.append(
                        f"{name}:{eid}:{where}: reinforcements gate value "
                        f"{req.get('value')!r} is not a whole number -- the count is an int")

            # Fail-forward guarantee: an event must never render zero choices.
            # Crisis events may corner the player (1-2 visible choices is a
            # legitimate dramatic beat), but zero is a soft-lock.
            unconditional = [c for c in e.get("choices", []) if not c.get("requires")]
            if len(unconditional) == 0:
                errors.append(f"{name}:{eid}: every choice has 'requires' -- event can soft-lock with zero visible choices")

            for ch in e.get("choices", []):
                for item in ch.get("boost_items", []):
                    items_referenced.setdefault(item, []).append(f"{name}:{eid}")
                prob = ch.get("prob", {})
                for mod in prob.get("mods", []):
                    swing = abs(float(mod.get("coef", 0.0))) * practical_stat_range(mod.get("stat", ""))
                    if swing > 0.9:
                        warnings.append(
                            f"{name}:{eid}:{ch.get('id')}: coef {mod['coef']} on {mod.get('stat')} "
                            f"can swing probability by {swing * 100:.0f}pts -- likely saturates the clamp"
                        )
                base = float(prob.get("base", 1.0))
                risky = 0.0 < base < 1.0
                if base >= P_MAX and ch.get("failure"):
                    warnings.append(
                        f"{name}:{eid}:{ch.get('id')}: base {base} clamps to P_MAX ({P_MAX}) but still has "
                        f"a failure branch -- presented as certain, fails ~2% of the time anyway "
                        f"(see BACKLOG_HANDOFF.md F2: lower base below {P_MAX} or delete the failure branch)"
                    )
                for branch_name in ("success", "failure"):
                    branch = ch.get(branch_name, {})
                    if risky and branch and not branch.get("text"):
                        warnings.append(f"{name}:{eid}:{ch.get('id')}: risky choice missing {branch_name} text")

                    # A dose the player never obtained. See NO_DEAL_MARKERS: this
                    # is not a flavour mismatch -- the dose goes through the
                    # overdose model, so it can kill a run for a purchase the
                    # prose says never completed.
                    branch_text = (branch.get("text") or "").lower()
                    if float(branch.get("dose", 0.0)) > 0:
                        hit = next((m for m in NO_DEAL_MARKERS if m in branch_text), None)
                        if hit:
                            errors.append(
                                f"{name}:{eid}:{ch.get('id')}: {branch_name} branch applies dose "
                                f"{branch['dose']} but its prose says the deal fell through "
                                f"({hit!r}) -- the player is dosed with a substance they never got"
                            )
                    for fl in branch.get("flags_set", []):
                        flags_set.add(fl)
                    for fl in branch.get("flags_clear", []):
                        flags_cleared.add(fl)
                    for item in branch.get("item_rewards", []) + branch.get("items_consumed", []):
                        items_referenced.setdefault(item, []).append(f"{name}:{eid}")
                    for clock_name in branch.get("clocks_start", {}):
                        clocks_started.add(clock_name)
                        # engine mints the expiry flag when the clock runs out
                        flags_set.add(f"clock_{clock_name}_expired")
                    for rel_name in list(branch.get("rel_deltas", {})) + [
                        r.get("name", "?") for r in branch.get("rel_add", [])
                    ]:
                        rel_names_used.setdefault(rel_name, []).append(f"{name}:{eid}")

    # Duplicate ids
    for eid, count in id_counts.items():
        if count > 1:
            errors.append(f"Duplicate event id '{eid}' appears {count} times across packs")

    # Required-but-never-set flags (legacy_* flags are minted by engine/legacy.py
    # from previous runs' recorded endings, never by events)
    for flag, sites in flags_required.items():
        if flag not in flags_set and not flag.startswith("legacy_"):
            errors.append(f"Flag '{flag}' is required by {sites} but no event ever sets it")

    # Item references vs catalog
    items_path = os.path.join(DATA_DIR, "items.json")
    catalog_ids: Set[str] = set()
    if os.path.exists(items_path):
        with open(items_path, "r", encoding="utf-8") as fh:
            catalog_ids = {i["id"] for i in json.load(fh).get("items", [])}
    for item, sites in items_referenced.items():
        if item not in catalog_ids:
            errors.append(f"Item '{item}' referenced by {sites} missing from items.json")

    # Relationship names vs cast + rel_add sites
    cast_path = os.path.join(DATA_DIR, "cast.json")
    known_names: Set[str] = set()
    if os.path.exists(cast_path):
        with open(cast_path, "r", encoding="utf-8") as fh:
            known_names = {c["name"] for c in json.load(fh).get("cast", [])}
    for rel_name, sites in rel_names_used.items():
        if rel_name not in known_names:
            errors.append(f"Relationship '{rel_name}' used by {sites[:3]} not defined in cast.json")

    # District ids vs the registry. A typo here is invisible at runtime: the
    # placement screen is built from districts.json, so a shelf the registry does
    # not name is one no player can ever stand in. The event stays drawable from
    # an unplaced slot (shelves are not exclusive -- A1_DESIGN §2), so nothing
    # breaks loudly; it just silently never gets the reservation it was shelved
    # for, which is the failure mode F1 spent a window diagnosing in another form.
    # See docs/A1_DESIGN.md §1.
    districts_path = os.path.join(DATA_DIR, "districts.json")
    known_districts: Set[str] = set()
    if os.path.exists(districts_path):
        with open(districts_path, "r", encoding="utf-8") as fh:
            known_districts = {d["id"] for d in json.load(fh).get("districts", [])}
    for district, sites in districts_used.items():
        if district not in known_districts:
            errors.append(
                f"District '{district}' assigned by {sites[:3]} is not defined in districts.json "
                f"-- those events are unreachable, not just unplaced"
            )

    # Endings coverage
    endings_path = os.path.join(DATA_DIR, "events", "endings.json")
    endings_defined: Set[str] = set()
    if os.path.exists(endings_path):
        with open(endings_path, "r", encoding="utf-8") as fh:
            endings_defined = set(json.load(fh).get("endings", {}).keys())
    for ending in RESOLVER_ENDINGS - endings_defined:
        errors.append(f"Resolver ending '{ending}' has no narrative text in endings.json")
    for ending in endings_defined - RESOLVER_ENDINGS:
        warnings.append(f"endings.json defines '{ending}' but no code path returns it")

    shelved = sum(len(v) for v in districts_used.values())
    print(f"Linted {len(pack_files)} pack(s), {total_events} events, {len(flags_set)} distinct flags, "
          f"{shelved} event(s) on {len(districts_used)} district shelf/shelves.")
    for w in warnings:
        print(f"  WARN:  {w}")
    for e in errors:
        print(f"  ERROR: {e}")
    if not errors and not warnings:
        print("  Clean. No issues found.")
    elif not errors:
        print(f"  {len(warnings)} warning(s), no errors.")
    else:
        print(f"  {len(errors)} error(s), {len(warnings)} warning(s).")
    return 1 if errors else 0


def report_dice(verbose: bool = False) -> int:
    """Partition every choice in the deck by how certain it actually is.

    'truly guaranteed' = no reachable failure branch: resolve_choice falls back
    to the success branch whenever `choice.failure` is empty, so these cannot
    fail regardless of prob.base or stat mods. 'near-certain but fallible' = a
    failure branch DOES exist, and prob.base alone (no mods) already clamps to
    P_MAX -- i.e. it still fails ~2% of the time via the P_MAX ceiling in
    engine/resolver.py, yet the OLD `guaranteed = p >= P_MAX` flag mislabeled it
    as certain. Everything else is a genuine gamble. See BACKLOG_HANDOFF.md §4.
    """
    total = 0
    truly_guaranteed: List[str] = []
    near_certain_fallible: List[str] = []
    gambles = 0

    for filepath in event_pack_files():
        name = os.path.basename(filepath)
        for ev in load_events(filepath):
            for ch in ev.choices:
                total += 1
                base = float((ch.prob or {}).get("base", 0.5))
                if not ch.failure:
                    truly_guaranteed.append(f"{name}:{ev.id}:{ch.id}")
                elif base >= P_MAX:
                    near_certain_fallible.append(f"{name}:{ev.id}:{ch.id}")
                else:
                    gambles += 1

    print(f"=== dice report: {total} total choices ===")
    print(f"  truly guaranteed (no failure branch):        {len(truly_guaranteed)}")
    print(f"  near-certain but fallible (base >= {P_MAX}):   {len(near_certain_fallible)}")
    print(f"  genuine gambles:                             {gambles}")
    print(f"\n  BACKLOG_HANDOFF.md baseline: 498 truly guaranteed / 123 near-certain / 1468 total")
    print(f"  drift vs baseline: truly_guaranteed {len(truly_guaranteed) - 498:+d}, "
          f"near_certain {len(near_certain_fallible) - 123:+d}, total {total - 1468:+d}")

    if verbose:
        print("\n  near-certain-but-fallible ids (pack:event:choice):")
        for tag in near_certain_fallible:
            print(f"    {tag}")

    return 0


if __name__ == "__main__":
    if "--report-dice" in sys.argv:
        sys.exit(report_dice(verbose="--verbose" in sys.argv))
    sys.exit(lint())
