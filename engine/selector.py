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


def select_event(
    events: List[Event],
    character: Character,
    day: int,
    rng: Optional[random.Random] = None,
    exclude_ids: Optional[Set[str]] = None,
) -> Optional[Event]:
    """Select a single eligible storylet based on state-influenced weighted probability."""
    rng = rng or random.Random()
    exclude_ids = exclude_ids or set()

    if _token(events) != _index_token:
        index_library(events)

    # Filter eligible pool (never repeat a storylet within the same day)
    pool = [e for e in events if e.id not in exclude_ids and e.eligible(character, day)]
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
