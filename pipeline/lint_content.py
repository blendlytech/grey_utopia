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
from typing import Dict, List, Set

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.events import load_events
from engine.stats import STAT_SPEC

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))


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
# clock_<name>_expired flags for every clock content ever starts.
ENGINE_GRANTED_FLAGS: Set[str] = {"near_overdose", "flag_overdose_death"}

# Comparison operators engine.events.compare_op actually implements.
VALID_OPS: Set[str] = {">=", "<=", ">", "<", "==", "!="}


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

    pack_files = sorted(
        f for f in glob.glob(os.path.join(DATA_DIR, "events", "*.json"))
        if os.path.basename(f) != "endings.json"
    )

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
                risky = 0.0 < float(prob.get("base", 1.0)) < 1.0
                for branch_name in ("success", "failure"):
                    branch = ch.get(branch_name, {})
                    if risky and branch and not branch.get("text"):
                        warnings.append(f"{name}:{eid}:{ch.get('id')}: risky choice missing {branch_name} text")
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

    print(f"Linted {len(pack_files)} pack(s), {total_events} events, {len(flags_set)} distinct flags.")
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


if __name__ == "__main__":
    sys.exit(lint())
