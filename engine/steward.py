"""steward.py -- the Steward's file, and the schedule it acts on (A3 Phase 1).

A3 asked for "a visible weekly move: it files something, offers something,
corrects something, escalates." Step 0 measured the deck before designing
against it, and found the item's premise wrong in both directions. What is here
is the mechanism the corrected premise wants; it ships **disabled**
(`STEWARD_CADENCE = None`), exactly as F1's ambient quota and A1 Phase 1's
prototype district did, because turning it on is a balance change and a balance
change needs its own `pargate`. See docs/A3_DESIGN.md.

Two measurements shape everything below.

--- 1. The Steward is not absent. It is undifferentiated. -------------------

`STEAM_READINESS_BACKLOG.md` says the Steward is "a stat modifier with 6 events
in data/events/steward_interventions.json". That file holds **2** events, and
the deck holds **125** tagged `steward`. Measured at n=40 per strategy, the
Steward already fires 42-44 times a run across 32-33 distinct days of a 54-62
day run, with a longest silence of 5-6 days. It is on screen more than half of
all days.

It also already takes a *scheduled* turn. `prologue_continuity_review` ->
`review_second_session` (d10) -> `review_third_session` (d20) ->
`review_final_session` (d30) is a forced (`weight: 500000`) flag-chained ladder
that completes **40/40 runs under every deliberate strategy**. The mechanism A3
was going to invent is built, shipped, and working.

What is missing is not presence or cadence. It is that 121 of those 125 events
are interchangeable -- a survey ping on day 4 reads exactly like a survey ping
on day 51 -- and that the one chain which *does* escalate stops at day 30
against runs that run to 54-62. So this module adds continuity and consequence
to the presence that already exists rather than adding more presence.

--- 2. Heat cannot be the trigger, and its integral can. --------------------

The obvious trigger is Heat: the deck has 40 events gated on it and
`selector.effective_weight` already scales every `steward`-tagged event by
`1 + Heat/40`. Measured over 40 runs per strategy, that is a dead lever for
half the game:

    strategy   mean Heat   peak (median)   share of run-days at Heat >= 25
    random         17.89          40.5                        28.9%
    cautious        0.86          12.5                         0.0%
    reckless       16.05          46.0                        27.3%
    greedy          2.73          20.0                         1.7%

Exactly **one** cautious run in 40 ever crossed Heat 25. A Heat-gated Steward
besieges the reckless and never once speaks to the careful -- and the careful
run is the one this game is *about*. (It also means that `1 + Heat/40`
multiplier is a flat 1.0 for cautious play, which is part of why the Steward
reads as wallpaper there.)

The reason is in `decay.py`: `K_COOL = 4.0` sheds Heat every clean day, so Heat
is a **stock** that any careful player drains to zero and holds there. The fix
is to read its **integral** instead. The file counts the *events* that raised
Heat; it never cools, because the Steward does not forget -- which is what
`ambient.steward_ledger_line` has been saying in prose since it was written.

Measured accumulation per 10 days, same runs:

    feed                                    random cautious reckless greedy  spread
    dossier flags only (the 47 sources)       3.18     3.33     3.55   3.23   1.12x
    dossier flags + any Heat-raising branch   7.29     4.26     6.84   5.80   1.71x

The first row is why `FILE_SOURCES` is not the whole feed. The deck already
grants `steward_biometric_dossier` (26 source events) and
`steward_civic_dossier` (21) -- as booleans, so grants 2..26 are no-ops -- and
counting only those produces a **1.12x spread across strategies**: a tenure
clock wearing an antagonist's coat. It measures how long you lived, not how you
played, so there is nothing to play against. Adding Heat-raising branches gives
a 1.71x spread while still guaranteeing every strategy reaches the low tiers
(40/40 runs reach tier 2 under all four strategies), which is the property an
*anticipatable* antagonist needs: everyone gets a Steward, and what you did
decides which one.
"""
from __future__ import annotations
from typing import Any, Dict, Optional, Tuple

from engine.stats import Character

# --- The file -------------------------------------------------------------

# Flags the deck already grants that mean "the Steward wrote something down".
# Nothing new has to be authored for the counter to work: 47 existing events
# feed it on day one. They are currently booleans, which is the defect this
# reads past -- a player who trips the biometric dossier 26 times has done the
# same thing 26 times and been charged for it once.
FILE_SOURCES: frozenset = frozenset({
    "steward_biometric_dossier",
    "steward_civic_dossier",
})

# Tier thresholds: (minimum file weight, tier index, name). The names are the
# Steward's own register -- it never says "wanted", it says "open". Tier 0 is
# the state every run starts in and most of the first week sits in.
#
# Cut points are picked off the measured final-file distribution
# (`tests/steward_audit.py --trigger`), not off round numbers, against two
# criteria: every strategy must reach every tier *sometimes* -- a tier no
# careful run ever sees is authored content nobody reads -- and the middle of
# the ladder must be where careful and reckless visibly diverge.
#
#   runs of 40 reaching each cut     random  cautious  reckless  greedy
#     8  Under Review                    40        40        40      40
#    18  Flagged                         25        39        40      38
#    26  Scheduled                       16        21        34      33
#    40  Closed                           5         1        19      16
#
# Tier 1 is universal, tier 2 near-universal for deliberate play, tier 3 is the
# divergence (cautious 53%, reckless 85%), and tier 4 is the reckless endgame a
# careful life almost never reaches -- but *can*, which is the point. An earlier
# cut at 32/50 was rejected on the same table: it put cautious at 7/40 and 0/40,
# i.e. it authored a top tier the careful player could never be shown.
TIERS: Tuple[Tuple[int, int, str], ...] = (
    (0,  0, "Open"),
    (8,  1, "Under Review"),
    (18, 2, "Flagged"),
    (26, 3, "Scheduled"),
    (40, 4, "Closed"),
)


def note_resolution(character: Character, branch: Dict[str, Any], heat_before: float) -> bool:
    """Record one resolved branch against the file. Returns whether it counted.

    Called from `resolver.resolve_choice` after the branch's deltas and flags
    have landed, so `character` is already in its post-resolution state and
    `heat_before` is the only thing that has to be carried in.

    Deliberately counts *events*, not points. A branch that adds 30 Heat and one
    that adds 2 are both one line in the file, because the file is a record of
    times the Steward had cause to write, and pricing it by magnitude would just
    rebuild Heat with extra steps -- including Heat's fatal property, that a big
    enough cooldown makes it disappear.
    """
    counted = bool(FILE_SOURCES.intersection(branch.get("flags_set", []))) or \
        character.get("Heat") > heat_before
    if counted:
        character.steward_file += 1
    return counted


def file_weight(character: Character) -> int:
    """How many lines the Steward has on this run. Monotonic; never cools."""
    return character.steward_file


def tier_for(weight: int) -> Tuple[int, str]:
    """(index, name) of the file tier a given weight sits in."""
    current = TIERS[0]
    for threshold, index, name in TIERS:
        if weight >= threshold:
            current = (threshold, index, name)
    return current[1], current[2]


def tier_of(character: Character) -> Tuple[int, str]:
    return tier_for(file_weight(character))


def next_tier(weight: int) -> Optional[Tuple[int, int, str]]:
    """The (threshold, index, name) the file is climbing toward, or None at the top."""
    for threshold, index, name in TIERS:
        if weight < threshold:
            return (threshold, index, name)
    return None


# --- The schedule ---------------------------------------------------------

# How often the Steward files, in days. **Live as of Phase 2**, gated by its own
# `pargate` run -- Phase 1 shipped this as None precisely because a filing
# consumes an action slot and carries consequence, which makes it a
# pool-composition change and a new unreviewed input to `sim_bot`'s strategies
# at once, against content that did not exist yet.
#
# The cadence sweep is in docs/A3_DESIGN.md §5; `tests/steward_audit.py
# --cadence N` reproduces it against the real filings.
STEWARD_CADENCE: Optional[int] = 7

# The day the Steward stops asking and starts filing. The Continuity Review
# ladder occupies days 0/10/20/30 already and completes 40/40 in deliberate
# play, so filings begin after it rather than colliding with it -- and the
# handover is the escalation the player is meant to feel. Four courteous
# interviews a fortnight apart, and then the interviews stop.
FILING_ONSET: int = 31

# The flag the day loops arm on a filing day and the filings themselves clear.
#
# This is how a *scheduled* event is expressed in a deck whose only scheduling
# primitive is `day`: `data/events/steward_filings_pack.json` gates on this flag
# plus a `steward_tier` band, so exactly one filing is eligible at a time and it
# is eligible only on the day the Steward files. Set by `begin_day` and cleared
# by every branch of every filing (`flags_clear`), which is the interlock that
# stops a second filing firing in the same day when a branch pushes the file
# across a tier cut mid-day.
#
# It is engine-granted, not content-granted, so `lint_content.ENGINE_GRANTED_FLAGS`
# names it -- otherwise the linter would correctly report a flag five events
# require that nothing sets.
FILING_DUE_FLAG: str = "steward_filing_due"

# How many days ahead the notice starts appearing. A3's ask is "one line the
# player sees coming"; without a window, `filing_notice` returns a line on every
# day of every run from day 0 ("reviewed in 31 days"), which is not foresight,
# it is wallpaper -- the exact defect §0.3 of the design note diagnoses in the
# other 121 Steward events. Three days is the lead the design's own example line
# quotes, and at cadence 7 it means the notice is present on 4 days in 7 rather
# than 7 in 7.
NOTICE_LEAD_DAYS: int = 3


def is_filing_day(day: int, cadence: Optional[int] = None) -> bool:
    """Whether the Steward files today.

    None cadence -- the mechanism disabled -- is always False, so the three day
    loops can call this unconditionally and the switch lives in one place. Same
    shape as `selector.ambient_budget_for`.
    """
    cadence = STEWARD_CADENCE if cadence is None else cadence
    if not cadence or day < FILING_ONSET:
        return False
    return (day - FILING_ONSET) % cadence == 0


def next_filing_day(day: int, cadence: Optional[int] = None) -> Optional[int]:
    """The next day on which the Steward will file, or None when disabled."""
    cadence = STEWARD_CADENCE if cadence is None else cadence
    if not cadence:
        return None
    if day <= FILING_ONSET:
        return FILING_ONSET
    elapsed = day - FILING_ONSET
    return day + (cadence - elapsed % cadence) % cadence


def days_until_filing(day: int, cadence: Optional[int] = None) -> Optional[int]:
    """Countdown for the UI. 0 means today. None when disabled."""
    nxt = next_filing_day(day, cadence)
    return None if nxt is None else nxt - day


def begin_day(character: Character, cadence: Optional[int] = None) -> bool:
    """Arm (or disarm) today's filing. Called at day start by every day loop.

    The direct analogue of `districts.clear_placements`: one call at the day
    boundary, in `main.py`, `server.py`, `tests/sim_bot.py`,
    `tests/coverage_audit.py` and `tests/steward_audit.py`, so the five loops
    cannot disagree about whether the Steward filed today. `coverage_audit
    --parity` is the tripwire if one of them is missed.

    Disarming matters as much as arming. A filing that never fired -- the run
    ended, or every choice on it was locked -- does not carry into tomorrow: the
    Steward files on schedule or not at all, which is what keeps the countdown in
    `filing_notice` honest.

    Consumes no RNG, so a day loop that adds this call does not reshuffle its own
    stream (BACKLOG_HANDOFF §5, A1 Phase 2). What it does change is the eligible
    pool on filing days, which is the balance change `pargate` gates.
    """
    due = is_filing_day(character.day, cadence)
    if due:
        character.flags.add(FILING_DUE_FLAG)
    else:
        character.flags.discard(FILING_DUE_FLAG)
    return due


def filing_notice(character: Character, cadence: Optional[int] = None) -> Optional[str]:
    """One line the player sees coming, for the morning report.

    This is A3's actual ask -- "one line the player sees coming and can play
    against" -- and it is deliberately prose rather than a number, because the
    Steward's register is warm and administrative and a raw counter would break
    it. `ambient.steward_ledger_line` is the existing precedent and this is
    written to sit beside it.

    None outside NOTICE_LEAD_DAYS of the filing, which is what makes it a warning
    rather than furniture -- see the constant.
    """
    days = days_until_filing(character.day, cadence)
    if days is None or days > NOTICE_LEAD_DAYS:
        return None
    _, name = tier_of(character)
    if days == 0:
        return f"STEWARD NOTICE: your file is reviewed today. Status: {name}."
    if days == 1:
        return f"STEWARD NOTICE: your file is reviewed tomorrow. Status: {name}."
    return f"STEWARD NOTICE: your file is reviewed in {days} days. Status: {name}."
