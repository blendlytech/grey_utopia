"""selector.py -- Weighted, dynamic state-influenced storylet selection engine."""
from __future__ import annotations
from typing import List, Optional, Set
import random
from engine.stats import Character
from engine.events import Event


def effective_weight(event: Event, character: Character) -> float:
    """Calculate dynamic weight based on character state and event tags.

    Three forces shape the deck:
      1. Instability leans in -- high Heat, low Meaning, high Reliance pull
         their thematic events forward.
      2. Story momentum -- events whose required flags the player has already
         earned get boosted, so arcs continue instead of stalling.
      3. Repetition damping -- every past firing of a repeatable event
         suppresses it, keeping the deck from feeling like a slot machine.
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

    # Story momentum: satisfied required flags mark this as an earned continuation
    momentum = 0
    for cond in (event.preconditions or {}).get("all", []):
        if "flag" in cond and cond.get("value", True) and cond["flag"] in character.flags:
            momentum += 1
        if "clock" in cond:
            momentum += 1   # deadline events press forward hard
    if momentum:
        w *= 1.0 + 0.8 * min(momentum, 3)

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
