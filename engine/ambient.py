"""ambient.py -- State-aware ambient prose layer for GREY UTOPIA.

Composes short, non-mechanical flavor lines from character state: a 1-2 line
morning report surfacing whichever pressures are most acute right now, and a
one-line "Steward ledger" citation of a concrete fact from the day before.
Both functions are pure presentation -- neither mutates character state.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

from engine.stats import Character
from engine.decay import withdrawal_severity, MEANING_FLOOR, ANOMIE_BODY_FLOOR

MARA_NAME = "Mara (Sister)"
MAX_MORNING_LINES = 2

# Days since last reinforcement before the silence itself becomes notable.
MARA_SILENCE_ONSET = 10

STAT_DISPLAY: Dict[str, str] = {
    "Wealth": "your balance",
    "Fame": "your visibility",
    "Recklessness": "your recklessness",
    "Mental_Decay": "your state of mind",
    "Family_Friction": "friction with family",
    "Substance_Reliance": "your reliance",
    "Heat": "surveillance heat",
    "Physical_Integrity": "your body",
    "Social_Capital": "your standing",
    "Meaning": "your sense of purpose",
    "Tolerance": "your tolerance",
}

# (urgency, line) -- higher urgency wins the top MAX_MORNING_LINES slots; ties
# keep the order signals are listed in morning_report (survival pressures
# before social ones).
_Signal = Tuple[int, str]


def _withdrawal_signal(character: Character) -> Optional[_Signal]:
    wd = withdrawal_severity(character.get("Substance_Reliance"), character.days_since_use)
    if wd <= 0.0:
        return None
    if wd < 0.2:
        return (1, "A low ache under the skin. Nothing you can't work through yet.")
    if wd < 0.5:
        return (3, "The shakes are back, gnawing at the edge of every thought.")
    return (5, "Your body is screaming for the one thing you don't have. Focus is a luxury today.")


def _physical_signal(character: Character) -> Optional[_Signal]:
    pi = character.get("Physical_Integrity")
    if pi >= 80.0:
        return None
    if pi >= 50.0:
        return (1, "Your body aches in the usual places. Manageable.")
    # 30.0 is where the engine itself starts cutting your action slots -- the
    # prose should start warning you before the mechanics do.
    if pi >= 30.0:
        return (3, "You're running on a battered frame. Every set of stairs is a negotiation.")
    return (5, "Your body is failing you. Something gives soon if this doesn't change.")


def _heat_signal(character: Character) -> Optional[_Signal]:
    heat = character.get("Heat")
    if heat < 15.0:
        return None
    if heat < 40.0:
        return (1, "Someone's paying attention to you. Not urgent. Yet.")
    if heat < 70.0:
        return (3, "The Steward's eye lingers a beat too long on your file today.")
    return (5, "You are burning. Every camera on the Row seems to know your face.")


def _meaning_signal(character: Character) -> Optional[_Signal]:
    meaning = character.get("Meaning")
    if meaning >= MEANING_FLOOR:
        return None
    if meaning >= ANOMIE_BODY_FLOOR:
        return (3, "The day ahead feels like just another day.")
    return (5, "Nothing you could do today would matter. You get up anyway.")


def _mara_signal(character: Character) -> Optional[_Signal]:
    rel = character.relationships.get(MARA_NAME)
    if not rel:
        return None
    days = character.day - rel.last_reinforced_day
    if days < MARA_SILENCE_ONSET:
        return None
    if days < 20:
        return (1, f"It's been {days} days since you last called Mara.")
    if days < 35:
        return (3, f"It's been {days} days since you called Mara. She's stopped asking why.")
    return (5, f"It's been {days} days since you spoke to Mara. You're starting to forget the sound of her voice.")


def morning_report(character: Character) -> List[str]:
    """Compose 1-2 ambient lines from whichever pressures are most acute this morning."""
    signals = [
        _withdrawal_signal(character),
        _physical_signal(character),
        _heat_signal(character),
        _meaning_signal(character),
        _mara_signal(character),
    ]
    active = [s for s in signals if s is not None]
    active.sort(key=lambda s: s[0], reverse=True)
    return [line for _, line in active[:MAX_MORNING_LINES]]


def steward_ledger_line(character: Character, yesterday_summary: Optional[Dict[str, Any]],
                        day_number: Optional[int] = None) -> str:
    """One concrete citation from yesterday's day report, phrased as a dated Steward ledger entry.

    yesterday_summary is the day_report-shaped dict produced by a day
    transition (see engine.decay.build_day_report): overnight stat deltas,
    expired clocks, withdrawal flag, and the day's stress figure. character
    supplies the day number the entry is dated to -- a ledger without dates
    isn't much of a ledger.

    `day_number` overrides that date, and exists because the two front ends
    number days differently: the terminal prints the engine's `character.day`
    directly, while the web HUD has always shown `day + 1`. The engine frame is
    the default, so the terminal is unaffected; `server.py` passes the web's
    frame so that a dated ledger entry agrees with the day counter three inches
    above it. This only became visible when A4 started rendering the line in the
    browser at all -- see docs/A4_DESIGN.md §5.
    """
    summary = yesterday_summary or {}
    if not summary:
        return "STEWARD LEDGER: no prior entry on file. Today opens a new page."

    dated = character.day - 1 if day_number is None else day_number
    tag = f"STEWARD LEDGER (Day {dated})"

    expired = summary.get("clocks_expired") or []
    if expired:
        name = expired[0].replace("_", " ")
        return f"{tag}: the {name} deadline closed overnight. Your file has been updated accordingly."

    overnight = summary.get("overnight") or {}
    if overnight:
        stat, delta = max(overnight.items(), key=lambda kv: abs(kv[1]))
        direction = "up" if delta > 0 else "down"
        label = STAT_DISPLAY.get(stat, stat)
        return f"{tag}: {label} moved {direction} {abs(delta):.1f} points overnight. Noted, as always."

    if summary.get("withdrawal"):
        return f"{tag}: your body flagged a dependency event overnight. The file does not forget."

    stress = summary.get("stress")
    if stress is not None:
        return f"{tag}: yesterday cost you {stress:.1f} points of quiet you will not get back."

    return f"{tag}: filed and closed. Nothing further to report."
