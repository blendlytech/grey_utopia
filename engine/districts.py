"""districts.py -- the A1 district registry and the morning placement step.

Phase 1 proved the shelf mechanism and shipped it inert, because the winning
configuration depended on *cadence* -- how often a slot was placed in a district
-- and cadence lived in the audit harness as a stand-in for a player deciding
where to stand. This module is that decision made real: the registry the game
reads its map from, the placement a player makes each morning, and the one
stand-in policy every automated caller shares.

Three things live here rather than being spread across the callers:

  * `load_districts` / `district_ids` -- the registry, cached, so lint, the UIs
    and the harness all read one file.
  * `apply_placements` / `clear_placements` -- the only writers of the placement
    state, so `main.py`, `server.py` and `tests/sim_bot.py` cannot drift on when
    a placement is recorded or when it expires. §5 of BACKLOG_HANDOFF already
    records those three loops drifting on what counts as a fired event; adding
    per-day state to all three is exactly the change that turns that kind of
    inconsistency into a save-compat bug.
  * `auto_placement` -- what a caller with no human attached does. Shared for the
    same reason, and additionally because `tests/coverage_audit.py` proves itself
    honest by reproducing `tests/sim_bot.py`'s runs seed for seed: a placement
    policy that consumed RNG differently in the two loops would break parity
    silently.
"""
from __future__ import annotations

import json
import os
import random
from typing import Dict, List, Optional, Sequence

from engine import paths
from engine.events import Event
from engine.stats import Character

DISTRICTS_PATH = os.path.join(paths.app_root(), "data", "districts.json")

_registry: Optional[List[dict]] = None


def load_districts() -> List[dict]:
    """The district registry, in file order, cached after the first read.

    File order is the order the placement screen offers, and the order
    `auto_placement` samples, so it is part of the measured configuration --
    adding a district changes how often each of the others is visited.
    """
    global _registry
    if _registry is None:
        if os.path.exists(DISTRICTS_PATH):
            with open(DISTRICTS_PATH, "r", encoding="utf-8") as fh:
                _registry = list(json.load(fh).get("districts", []))
        else:
            _registry = []
    return _registry


def district_ids() -> List[str]:
    return [d["id"] for d in load_districts()]


def district_by_id(district_id: Optional[str]) -> Optional[dict]:
    if not district_id:
        return None
    return next((d for d in load_districts() if d["id"] == district_id), None)


def district_name(district_id: Optional[str]) -> str:
    entry = district_by_id(district_id)
    return entry["name"] if entry else "the Row at large"


# --- placement state ------------------------------------------------------
#
# Placement is per-day and per-slot, and it is free: A1_DESIGN §4 rejects a
# travel tax because slots are already the scarcest resource in the game and are
# cut to 2 exactly when a player most needs to reach a specific chain. The cost
# of standing somewhere is the districts you are not standing in.


def clear_placements(character: Character) -> None:
    """Drop yesterday's placements. Called once per day rollover, by every loop."""
    character.placements = {}


def apply_placements(character: Character, placements: Dict[int, Optional[str]]) -> None:
    """Record the morning's placement and stamp each district's last-visited day.

    Unplaced slots are stored as absent rather than as an explicit None, so
    `district_for_slot` reads a plain `.get()` and 'unplaced' stays the default
    everywhere -- the same absent-means-neutral discipline the `district` field
    itself uses.
    """
    known = set(district_ids())
    cleaned: Dict[int, str] = {}
    for slot, district in (placements or {}).items():
        if district and district in known:
            cleaned[int(slot)] = district
    character.placements = cleaned
    for district in set(cleaned.values()):
        character.last_visited[district] = character.day


def days_since_visit(character: Character, district_id: str) -> Optional[int]:
    """Days since a slot was last placed here, or None if never."""
    last = character.last_visited.get(district_id)
    return None if last is None else character.day - last


def shelf_open_count(events: Sequence[Event], character: Character, district_id: str) -> int:
    """How many of a district's own storylets could fire there today."""
    return sum(1 for e in events
               if e.district == district_id and e.eligible(character, character.day))


def district_hint(events: Sequence[Event], character: Character, district_id: str) -> str:
    """The one line a player gets about a district before committing a slot to it.

    Deliberately coarse. A hint precise enough to say "the next link of your
    ambition is available today" would hand back the vending machine Phase 1
    measured and rejected -- a player with perfect information places on exactly
    the days a gate opens and wins 100% of those draws. Open/quiet plus how long
    it has been is enough to make the choice a decision without making it a
    solved one.
    """
    since = days_since_visit(character, district_id)
    if since is None:
        recency = "You have not set foot in it this cycle."
    elif since == 0:
        recency = "You worked it this morning."
    elif since == 1:
        recency = "You were here yesterday."
    else:
        recency = f"{since} days since you last walked it."

    open_now = shelf_open_count(events, character, district_id)
    if open_now == 0:
        state = "Nothing here has your name on it today."
    elif open_now <= 2:
        state = "Something is open."
    else:
        state = "There is more here than you can get to."
    return f"{state} {recency}"


# --- the stand-in for a player who is not there ---------------------------


# How often the automated stand-in commits one of the day's slots to standing
# somewhere, as a fraction of days. **Not a function of how many districts exist.**
#
# Phase 2 computed this as `min(1.0, len(districts) / 5)`, meaning to hold each
# district's visit cadence at Phase 1's measured every-5 as the map grew. That
# formula saturates at five districts and then fails in three ways at once, all
# of which Phase 3 hit on the way to a seven-district map:
#
#   * it reserves a slot *every single day*, so "stay in the Row at large" stops
#     being reachable at all -- an invariant tests/test_engine.py encodes, and
#     one a human player obviously keeps;
#   * per-district cadence collapses anyway (1 slot spread over 7 districts is
#     one visit each per 7 days, not per 5), so it does not even buy the thing
#     it gives up the Row for; and
#   * it contradicts its own stated principle, that how many places exist should
#     not change how often someone commits their day to one of them.
#
# The reserved fraction is the balance-critical quantity, not the map's size:
# a placed slot draws a district's own thread content, and thread content is
# where this deck keeps its *wins* while the untagged middle keeps its deaths.
# Reserving a third of every day for shelves took reckless terminal endings to
# 3.5% against a 25-35% band and good endings to 53.5% against a 45% cap. See
# docs/A1_DESIGN.md §7.8.
#
# So this is a flat rate, set where the balance gate is green, and per-district
# cadence is whatever falls out of it: one visit every `len(districts) / rate`
# days -- currently about one visit per district per 12 days.
PLACEMENT_RATE: float = 0.40


def auto_placement(rng: random.Random, character: Character, slots: int) -> Dict[int, str]:
    """The placement an automated caller makes: at most one slot, one district.

    Two separate decisions, and collapsing them was a modelling bug worth
    spelling out. The first cut of this drew uniformly over `districts + [stay in
    the Row]`, which made the chance of committing a slot **rise with the size of
    the map** -- 50% at one district, 67% at two, 87% at eight -- for no reason
    except that there were more entries in the list. How many places exist should
    not change how often someone commits their day to one of them.

    Phase 2's fix stated that principle and then broke it a second way, by
    deriving the rate from the map size anyway (`min(1, n/5)`). Phase 3 makes it
    what it always should have been: *whether* to go is the flat
    `PLACEMENT_RATE`, and *where* is uniform over the map. Per-district cadence
    is then whatever that buys -- `len(districts) / PLACEMENT_RATE` days between
    visits -- and adding a district genuinely does spread the same commitment
    wider instead of demanding more of it.

    **One slot, never the whole day.** Phase 1 measured a single placed slot; a
    bot that commits its entire day to one shelf is the vending machine, not a
    player. The game does not stop a human from doing it -- and §7.7 of the
    design note records what that costs.

    Consumes exactly two RNG draws per day whenever the registry is non-empty,
    independent of `slots` and of the outcome, so `coverage_audit`'s parity check
    against `sim_bot` stays seed-for-seed exact.
    """
    ids = district_ids()
    if not ids:
        return {}
    go = rng.random()
    which = rng.randrange(len(ids))
    if slots <= 0 or go >= PLACEMENT_RATE:
        return {}
    return {0: ids[which]}
