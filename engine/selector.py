"""selector.py -- Weighted, dynamic state-influenced storylet selection engine."""
from __future__ import annotations
from typing import Dict, List, Optional, Sequence, Set, Tuple
import random
from engine.stats import Character
from engine.events import Event

# Story momentum is scored on chain depth: how many of an event's required
# flags are things only another storylet can hand you. Depth 0 is ambient
# filler anyone can draw on any day; depth 2 is the third beat of a thread the
# player has been building for a week. Filler outnumbers arc content roughly
# 2:1 in the deck, so a flat per-flag bonus left the deep steps of a chain
# losing the draw to noise -- the arc a run was actually about would stall out
# under events it had already earned its way past. Scaling geometrically in
# depth means every earned prerequisite multiplies an event's presence in the
# deck, so the further into a thread a step sits, the harder it outbids
# whatever the city was going to hand you instead.
DEPTH_SCALE: float = 2.2
MAX_DEPTH: int = 3

# Deadlines press forward hard, independent of how deep the chain is.
DEADLINE_BONUS: float = 0.8
MAX_DEADLINE_CONDS: int = 3

# Per-day budget for the city's background noise: the 88 storylets tagged
# ambient or micro, none of which are attached to a thread.
#
# Shipped disabled (None), and that is a measured decision rather than an
# unfinished one. `tests/coverage_audit.py` was built to test the premise that
# filler was crowding arc content out of the draw, and it does not hold:
#
#   ambient+micro is only 20.8% of eligible draw weight. Arc content is 24.6%.
#   The other 55.8% is the untagged middle -- job, undercity, existential,
#   steward, vice, family, vendor -- which this tag set does not budget. So
#   suppressing ambient redistributes roughly 2.3:1 into that middle, not into
#   arc: banning ambient outright (budget 0) still tops arc draw-share out at
#   30.2%, and at one slot a day it moves 25.2% -> 25.4%.
#
# Meanwhile the events that never fire are not losing draws, they are never
# eligible: of the 54 unreached non-legacy storylets, 50 are gated behind a flag
# only another storylet can grant. Pool composition cannot reach them.
#
# The quota also cost a balance gate on the way through -- reckless terminal
# rate fell to 21.8%, under sim_bot's 25% floor -- because ambient events are the
# low-consequence content that lets a run coast, so removing them shortened the
# median random run 43 -> 36 days and cut unique events seen per run 113 -> 92.
#
# The mechanism is kept and tested because it is the right shape for budgeting a
# *shelf* (see A1's districts); the tag set it was pointed at is simply not where
# this deck's filler lives. Set to an int to re-enable, then re-run pargate.
AMBIENT_TAGS: frozenset = frozenset({"ambient", "micro"})
AMBIENT_SLOTS_PER_DAY: Optional[int] = None


def ambient_budget_for(ambient_today: int) -> Optional[int]:
    """Ambient slots left in a day that has already spent `ambient_today` of them.

    None -- the quota disabled -- when AMBIENT_SLOTS_PER_DAY is None, so callers
    thread this through unconditionally and the switch lives in exactly one place.
    """
    if AMBIENT_SLOTS_PER_DAY is None:
        return None
    return AMBIENT_SLOTS_PER_DAY - ambient_today


# --- A1: district shelves -------------------------------------------------
#
# An action slot can be *placed* in a district, and a placed slot draws from that
# district's shelf rather than from the whole deck. This is the reservation F1's
# ambient quota was the wrong end of: budgeting a tag down redistributes weight
# into the 55.8% untagged middle, but reserving a draw for a shelf takes the
# general deck out of the competition entirely.
#
# It exists because one measurement made the case unarguable. `amb_the_choosing`
# -- the fork that hands out all three ambitions, and so the root of 23 downstream
# storylets -- is gated on `day >= 6` and nothing else. At n=40 it was eligible in
# 40/40 runs, sat in the pool for 2290 draws, and won 19 of them: a 0.789% median
# share of each draw's weight. It is not hidden, it is drowned, and no weighting
# lever reaches something losing at that ratio. See docs/A1_DESIGN.md §0.
#
# Shipped disabled (PROTOTYPE_DISTRICT = None): every slot is unplaced, every
# event is district-neutral, and behaviour is identical to pre-A1. Absent-means-
# neutral is also what lets the deck migrate one pack at a time.
PROTOTYPE_DISTRICT: Optional[str] = None
DISTRICT_SLOTS_PER_DAY: int = 1

# Whether a district's shelf also carries the district-neutral ambient storylets.
#
# Off, and that is the measurement overruling the design. The argument for On was
# that ambient filler is the city and the city is everywhere, so a shelf holding
# only a day-gated chain would be a vending machine with no texture. The vending
# machine is real -- see the cadence note below -- but mixing the *whole* neutral
# ambient pool into every placed draw is a much worse cure than the disease:
#
#   On, one placed slot a day: the shelf's 24 events drew against ~88 ambient, so
#   ambient took 45.7% of all picks (from 21.3%), the median eligible pool fell
#   209 -> 74, arc draw-share fell 24.7% -> 19.3%, and never-fired rose 103 -> 134.
#   The chain itself only reached 16/24 events in 27/40 runs.
#
#   Off, same placement: the chain reached 19/24 in 40/40 runs and never-fired
#   moved 103 -> 118 -- still a regression, but half the size, and the chain got
#   the benefit the shelf exists to give.
#
# What actually fixes the vending machine is visit *cadence*, not shelf dilution:
# at one placed slot every 5 days the chain reaches 23/24 events in 40/40 runs at
# a 10.5% win rate on eligible draws (not 100%), and the deck-wide numbers come
# out ahead of baseline rather than behind. Full A/B in BACKLOG_HANDOFF.md §3.
#
# The right texture is a district's *own* ambient, which does not exist until
# Phase 3 distributes the volume pack across shelves. Revisit this flag then, with
# proportionate filler rather than all of it.
SHELF_INCLUDES_AMBIENT: bool = False


def district_for_slot(slot_index: int) -> Optional[str]:
    """Which district the day's `slot_index`-th action slot is placed in.

    The direct analogue of ambient_budget_for: the three day loops call it
    unconditionally and the on/off switch lives in exactly one place. None means
    the slot is unplaced and draws from the district-neutral pool.

    A placeholder for player agency. The full A1 has the player placing each of
    the day's slots across 6-8 districts; until that UI exists, this hands the
    first DISTRICT_SLOTS_PER_DAY slots to the prototype district so the mechanism
    can be measured end to end.
    """
    if PROTOTYPE_DISTRICT is None:
        return None
    return PROTOTYPE_DISTRICT if slot_index < DISTRICT_SLOTS_PER_DAY else None


# Flag provenance for the currently indexed library: flag -> ids of the events
# that can grant it. Rebuilt whenever select_event is handed a different deck.
_flag_sources: Dict[str, Set[str]] = {}
_depth_cache: Dict[str, int] = {}
_index_token: Optional[Tuple] = None


def _token(events: Sequence[Event]) -> Tuple:
    """Cheap identity for a loaded deck, so the index is rebuilt only on change."""
    if not events:
        return (0,)
    return (len(events), id(events), id(events[0]), id(events[-1]))


def index_library(events: Sequence[Event]) -> None:
    """(Re)build the flag-provenance index that chain depth is measured against.

    select_event calls this automatically when handed a deck it has not seen;
    call it directly after mutating an already-indexed library in place.
    """
    global _index_token
    _flag_sources.clear()
    _depth_cache.clear()
    for ev in events:
        for choice in ev.choices:
            for branch in (choice.success, choice.failure):
                for flag in (branch or {}).get("flags_set", []):
                    _flag_sources.setdefault(flag, set()).add(ev.id)
    _index_token = _token(events)


def chain_depth(event: Event) -> int:
    """How many of this event's required flags only *other* storylets can grant.

    Origin and engine-set flags (near_overdose, expired clocks, legacy marks)
    don't count, and neither does a flag the event hands itself: none of those
    are evidence that the player walked a chain to arrive here. Capped at
    MAX_DEPTH so a heavily-gated one-shot cannot run away with the deck.
    """
    cached = _depth_cache.get(event.id)
    if cached is not None:
        return cached
    depth = 0
    for cond in (event.preconditions or {}).get("all", []):
        flag = cond.get("flag")
        if flag and cond.get("value", True) and _flag_sources.get(flag, frozenset()) - {event.id}:
            depth += 1
    depth = min(depth, MAX_DEPTH)
    _depth_cache[event.id] = depth
    return depth


def effective_weight(event: Event, character: Character) -> float:
    """Calculate dynamic weight based on character state and event tags.

    Three forces shape the deck:
      1. Instability leans in -- high Heat, low Meaning, high Reliance pull
         their thematic events forward.
      2. Story momentum -- events gated behind flags the player earned
         elsewhere get boosted by their chain depth, so arcs continue instead
         of stalling under filler.
      3. Repetition damping -- every past firing of a repeatable event
         suppresses it, keeping the deck from feeling like a slot machine.

    Scored against events that already passed Event.eligible(), which is what
    select_event feeds it: a required flag counted toward depth here is by
    definition one the character is currently holding.
    """
    w = event.weight

    # Steward surveillance events escalate with Heat
    if "steward" in event.tags:
        w *= 1.0 + (character.get("Heat") / 40.0)

    # Existential crisis events escalate when Meaning is eroding
    if "existential" in event.tags:
        w *= 1.0 + ((100.0 - character.get("Meaning")) / 50.0)

    # Vice/temptation events escalate with Substance Reliance
    if "vice" in event.tags:
        w *= 1.0 + (character.get("Substance_Reliance") / 50.0)

    # Family events become more urgent when Family Friction is high
    if "family" in event.tags:
        w *= 1.0 + (character.get("Family_Friction") / 50.0)

    # Story momentum: the deeper the chain this step sits in, the louder it is
    depth = chain_depth(event)
    if depth:
        w *= DEPTH_SCALE ** depth

    # Deadline pressure: a running clock in the preconditions presses forward
    deadlines = sum(1 for cond in (event.preconditions or {}).get("all", []) if "clock" in cond)
    if deadlines:
        w *= 1.0 + DEADLINE_BONUS * min(deadlines, MAX_DEADLINE_CONDS)

    # Repetition damping: familiar storylets fade into the city's noise
    if event.fire_count > 0:
        w /= 1.0 + 0.45 * event.fire_count

    return max(w, 0.0)


def is_ambient(event: Event) -> bool:
    """True for background filler, the content the per-day quota budgets."""
    return bool(AMBIENT_TAGS.intersection(event.tags))


def on_shelf(event: Event, district: str) -> bool:
    """True if a slot placed in `district` can draw this storylet.

    The district's own content, plus -- when SHELF_INCLUDES_AMBIENT -- the
    district-neutral ambient filler that belongs to the whole city rather than
    to any one part of it.
    """
    if event.district == district:
        return True
    return SHELF_INCLUDES_AMBIENT and event.district is None and is_ambient(event)


def eligible_pool(
    events: Sequence[Event],
    character: Character,
    day: int,
    exclude_ids: Optional[Set[str]] = None,
    ambient_budget: Optional[int] = None,
    district: Optional[str] = None,
) -> List[Event]:
    """Every storylet that could fire right now, after exclusions and the quota.

    `ambient_budget` is how many ambient slots the caller has left today; None
    disables the quota, which is what a caller that does not track days wants.
    Once the budget is spent, ambient events drop out of the draw -- unless
    removing them would empty the pool, in which case the unbudgeted pool is
    handed back. Returning nothing would silently burn the player's action slot,
    and the early game is the realistic trigger: almost everything eligible on
    day 1 is ambient.

    `district` is where the caller placed this action slot. A placed slot draws
    that district's shelf instead of the general deck: this is a reservation, not
    a nudge, and it is the only part of A1 that can move a first link losing 2271
    of 2290 draws. If the shelf comes back empty (its chain exhausted, or every
    link still day-gated), the unfiltered pool is handed back for the same reason
    the ambient quota yields -- a dead slot is worse than an off-theme one.

    None -- unplaced -- does not filter at all, so a districted event stays
    drawable from unplaced slots. Deliberately *not* the stricter reading, under
    which a district's content is invisible from outside it. Exclusivity would
    make every shelved event unreachable the moment placement is off (a live
    footgun while PROTOTYPE_DISTRICT ships as None, and during a migration where
    most of the map does not exist yet), and it would buy nothing: hiding a
    storylet from the other two slots cannot help it win the one it is reserved
    on. Revisit in Phase 3, once every event has a home and 'neutral' means
    ambient rather than unmigrated. See docs/A1_DESIGN.md §2.
    """
    exclude_ids = exclude_ids or set()
    # Never repeat a storylet within the same day.
    pool = [e for e in events if e.id not in exclude_ids and e.eligible(character, day)]
    if ambient_budget is not None and ambient_budget <= 0:
        budgeted = [e for e in pool if not is_ambient(e)]
        if budgeted:
            pool = budgeted
    if district is None:
        return pool
    shelf = [e for e in pool if on_shelf(e, district)]
    return shelf or pool


def select_event(
    events: List[Event],
    character: Character,
    day: int,
    rng: Optional[random.Random] = None,
    exclude_ids: Optional[Set[str]] = None,
    ambient_budget: Optional[int] = None,
    district: Optional[str] = None,
) -> Optional[Event]:
    """Select a single eligible storylet based on state-influenced weighted probability."""
    rng = rng or random.Random()

    if _token(events) != _index_token:
        index_library(events)

    pool = eligible_pool(events, character, day, exclude_ids, ambient_budget, district)
    if not pool:
        return None

    weights = [effective_weight(e, character) for e in pool]
    total_weight = sum(weights)

    if total_weight <= 0:
        return rng.choice(pool)

    r = rng.uniform(0.0, total_weight)
    accumulated = 0.0
    for event, w in zip(pool, weights):
        accumulated += w
        if r <= accumulated:
            return event

    return pool[-1]
