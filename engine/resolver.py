"""resolver.py -- Hidden probability evaluation, outcome resolution, and endgame condition checker."""
from __future__ import annotations
from typing import Tuple, Dict, Any, Optional, List  # noqa: F401 -- Tuple used in table annotation
import random
from engine.stats import Character, clamp
from engine.events import Choice, eval_conditions
from engine import items as item_catalog
from engine.decay import overdose_probability

P_MIN: float = 0.02
P_MAX: float = 0.98

# Flags that mark a life that reached for something -- an exit, a post, a
# reckoning, a place in the machine court. A run that holds none of these by
# the late game never truly chose; that inertia is what the Sanctuary absorbs.
# A run that completed one of these actually resolved into a life -- reached a
# wire and crossed it, took a post, chose the bench, held or gave away the
# switch. These outcomes map to endings; their presence means the run is done.
COMPLETION_FLAGS: frozenset = frozenset({
    "crossed_wire", "chose_small_life", "advocate_accepted", "became_ferryman",
    "keeper_of_switch", "switch_distributed", "garden_gated", "gardener_endorsed",
    "shepherd_accepted", "steward_buyout_accepted",
})

# Flags that mark a life that reached for something -- an exit, a post, a
# reckoning, a place in the machine court, even just a mapped route or a bought
# pass. A run that holds none of these by the late game never truly chose; that
# inertia is what the Sanctuary absorbs.
AGENCY_FLAGS: frozenset = frozenset(COMPLETION_FLAGS | {
    "true_cell", "truth_leaked", "arbitration_called", "your_shape_in_it",
    "small_life_refused", "exit_ready", "ran_the_seam", "seam_reputation",
    "apprenticeship_accepted", "route_mapped",
})

# Desperation edge: after consecutive genuinely-failed rolls the city
# underestimates the cornered. A small, visible mercy that blunts pure
# bad-luck death spirals without rewarding recklessness outright.
EDGE_STEP: float = 0.03   # probability bonus per consecutive failure
EDGE_CAP: float = 0.09    # bonus ceiling (three failures deep)

# The substrate interrupt lands mid-run for anyone who reached far enough to be
# offered it, and the offer is unconditional -- take it, split it, either way you
# hold the thing. If that closed the book on the spot, every such life would end
# the same way and every choice still ahead would go unmade. So the switch has to
# outlast the rest of you before it becomes what your life was about.
SWITCH_SETTLE_DAY: int = 76

# The workshop finale hands out 'chose_small_life' through a chain that cannot
# fail -- the apprenticeship, the first shift and the bell are all guaranteed
# grants -- so as an immediate ending it was a free win that any strategy could
# collect, and it dominated the good-ending table for all of them. The fix is not
# to make the choice harder; choosing the small life should always be available.
# It is that the small life is a thing you keep doing, not a door you walk
# through. It resolves only once it has actually been lived a while, and only if
# it is still holding: a body that can still do the work, and enough left in you
# to think the work is worth doing.
#
# The Meaning bar is deliberately high -- not 'not yet despairing' but 'this is
# still visibly worth it to you'. Anything lower does not bite at all, because a
# run that just spent weeks at the bench is usually well fed on purpose at the
# moment it is checked; the bar has to sit up inside that range to mean anything.
# A life that chose this and then hollowed out anyway did not get the small real
# things. It gets the long grey, which is the ending that was always waiting
# underneath this one -- and because 'chose_small_life' still counts as a
# completion, such a run is barred from the Sanctuary and has to find that
# reckoning, or the attrition, on its own.
#
# The body bar is the bench-work bar: 25 was 'not actively dying', which nobody
# ever failed, so the clause did nothing. 40 is 'can still do the work' -- the
# thing the ending is actually about. Note that neither bar is a one-shot test:
# the endgame check runs every day, so a run held back by either one keeps
# playing and resolves later if it recovers. That is why moving them separates
# the strategies far less than their raw distributions suggest, and why the
# body bar is the milder of the two despite the larger jump.
#
# MEASURED DEAD LEVER, 2026-07-27: 76 -> 80 was tried at full N to pull greedy's
# good-ending rate back under GOOD_CAP, and it does not reach greedy at all --
# greedy small-life fell 29.4% -> 28.8% (-0.6) while CAUTIOUS fell 36.2% ->
# 30.9% (-5.3), nine times the effect on the wrong strategy. The reason is
# structural and applies to any future attempt: `DELTA_UTILITY["Meaning"]` is
# 1.0, the highest weight in the bots' scoring, so greedy is the strategy that
# maximizes Meaning and arrives at the settle day well clear of any bar that
# cautious can still survive. A Meaning bar can only ever select against the
# strategies that were not optimizing for Meaning. Reverted to 76; if greedy's
# share of this ending has to come down, the lever is making the
# apprenticeship -> workshop_standing -> chose_small_life chain genuinely
# fallible (today no step in it can fail), not this constant.
SMALL_LIFE_SETTLE_DAY: int = 44
SMALL_LIFE_MIN_MEANING: float = 76.0
SMALL_LIFE_MIN_BODY: float = 40.0

# Consecutive days at Mental_Decay >= 90 before the Sanctuary takes you. Three
# was a single bad week: a mind can spike that high on one catastrophic run of
# luck and already be walking it back. Requiring the state to hold well past the
# crisis that caused it is the difference between a breakdown and a diagnosis --
# and it is what stops chaotic play from being funnelled into the Sanctuary as
# its default reckoning, which is the single most over-subscribed ending here.
MD_COLLAPSE_DAYS: int = 5

# Details of the most recent resolve_choice() roll, for UI dice-reveal display.
# Single-session engine; not meant to be thread-safe.
last_resolution: Dict[str, float] = {}


def eligible_choices(choices: List[Choice], character: Character) -> List[Choice]:
    """Choices visible to this character: unconditional ones plus unlocked conditionals."""
    return [ch for ch in choices if ch.available(character)]


def active_boost_items(choice: Choice, character: Character) -> List[str]:
    return [i for i in choice.boost_items if character.has_item(i)]


def desperation_edge(character: Character) -> float:
    """Current probability bonus earned by consecutive failed rolls."""
    return min(EDGE_CAP, EDGE_STEP * character.fail_streak)


def choice_probability(choice: Choice, character: Character) -> float:
    """Calculate effective outcome probability: p = clamp(base + Σ coef_i * stat_i + gear + edge, 0.02, 0.98)."""
    spec = choice.prob or {}
    p = float(spec.get("base", 0.5))
    for mod in spec.get("mods", []):
        stat_name = mod.get("stat")
        coef = float(mod.get("coef", 0.0))
        if stat_name:
            p += coef * character.get(stat_name)
    for item_id in active_boost_items(choice, character):
        p += item_catalog.prob_bonus(item_id)
    if choice.failure:   # the edge only applies to genuine gambles
        p += desperation_edge(character)
    return clamp(p, P_MIN, P_MAX)


def apply_dose(character: Character, dose: float, rng: random.Random) -> Optional[str]:
    """Route a substance dose through the pharmacology model.

    Accumulates the day's dose for end-of-day tolerance/reliance accounting and
    rolls immediate overdose. The first overdose is a collapse -- a survivable,
    heavily telegraphed warning. A second overdose while carrying that warning
    is death. Returns 'collapse', 'death', or None.
    """
    if dose <= 0:
        return None
    character.pending_dose += dose
    p_od = overdose_probability(
        dose * (1.0 + character.get("Tolerance") / 6.0),
        character.get("Substance_Reliance"),
        character.get("Physical_Integrity"),
    )
    if character.has_item("lethe_test_kit"):
        p_od *= 0.5   # you read the batch before the batch reads you
    if rng.random() < p_od:
        if "near_overdose" in character.flags:
            if character.has_item("naloxinol_patch"):
                # The auto-patch fires on cardiac stutter and burns out
                character.remove_item("naloxinol_patch")
                character.apply_deltas({"Physical_Integrity": -30, "Mental_Decay": 12})
                return "collapse"
            character.flags.add("flag_overdose_death")
            return "death"
        character.flags.add("near_overdose")
        character.apply_deltas({"Physical_Integrity": -35, "Mental_Decay": 10})
        return "collapse"
    return None


def resolve_choice(
    choice: Choice,
    character: Character,
    rng: Optional[random.Random] = None
) -> Tuple[bool, Dict[str, Any]]:
    """Roll for choice outcome, apply stat deltas and flag mutations, return (success, branch_dict)."""
    rng = rng or random.Random()
    p = choice_probability(choice, character)

    # Execute hidden dice roll
    roll = rng.random()
    success = roll <= p

    was_gamble = bool(choice.failure)
    branch = choice.success if success else choice.failure
    if not branch:  # Fallback for safe/guaranteed choices
        branch = choice.success or {}
        success = True

    # Desperation edge bookkeeping: only genuine gambles move the streak.
    # Safe choices neither bank a comeback nor squander one.
    if was_gamble:
        character.fail_streak = 0 if success else character.fail_streak + 1

    # Single-use gear that boosted this roll burns up regardless of outcome
    for item_id in active_boost_items(choice, character):
        if item_catalog.is_single_use(item_id):
            character.remove_item(item_id)

    # 'guaranteed' means cannot fail -- no reachable failure branch -- not merely
    # a high probability. Anything with a live failure branch still clamps to
    # P_MAX at most, so it fails ~2% of the time; presenting that as certain is
    # the game lying to the player (see BACKLOG_HANDOFF.md F2).
    last_resolution.clear()
    last_resolution.update({"p": p, "roll": roll, "guaranteed": 0.0 if was_gamble else 1.0})

    # Apply stat deltas
    character.apply_deltas(branch.get("deltas", {}))

    # Apply faction deltas
    for faction, delta in branch.get("faction_deltas", {}).items():
        character.add_faction(faction, float(delta))

    # New contacts earned through play join the network
    for entry in branch.get("rel_add", []):
        if entry["name"] not in character.relationships:
            character.add_relationship(
                entry["name"],
                satisfaction=float(entry.get("satisfaction", 50.0)),
                strength=float(entry.get("strength", 6.0)),
            )

    # Apply relationship deltas (positive reinforces the bond, negative strains it)
    for name, delta in branch.get("rel_deltas", {}).items():
        character.adjust_relationship(name, float(delta))

    # Route substance doses through the pharmacology model
    od_outcome = apply_dose(character, float(branch.get("dose", 0.0)), rng)
    if od_outcome:
        last_resolution["overdose"] = 1.0 if od_outcome == "death" else 0.5

    # Apply item rewards
    for item_id in branch.get("item_rewards", []):
        character.add_item(item_id)

    # Consume single-use items required by branch
    for item_id in branch.get("items_consumed", []):
        character.remove_item(item_id)

    # Start / stop deadline clocks
    for name, days in branch.get("clocks_start", {}).items():
        character.start_clock(name, int(days))
    for name in branch.get("clocks_stop", []):
        character.stop_clock(name)

    # Apply flag mutations
    for flag in branch.get("flags_set", []):
        character.flags.add(flag)
    for flag in branch.get("flags_clear", []):
        character.flags.discard(flag)

    return success, branch


# Lying low: the one action always available. Recovery without purpose --
# the body mends, the file cools, and the days go somewhere all the same.
REST_DELTAS: Dict[str, float] = {
    "Physical_Integrity": 4.0,
    "Mental_Decay": -3.0,
    "Heat": -2.0,
    "Meaning": -1.0,
}

REST_TEXTS: Tuple[str, ...] = (
    "You keep the shutters down and the terminal dark. The Row forgets your face a little; so, quietly, do you.",
    "A day of tea, tape, and small repairs. Your hands stop aching. Nothing needed you, and it almost felt like peace.",
    "You sleep through two ration cycles and wake to rain on the vent glass. The city ran fine without you. That cuts both ways.",
    "Heads down, door bolted. The Steward's feed logs you as 'resting comfortably', and for once the file is accurate.",
)


def apply_rest(character: Character, rng: Optional[random.Random] = None) -> str:
    """Spend an action slot lying low. Returns the flavor line for the UI."""
    rng = rng or random.Random()
    character.apply_deltas(REST_DELTAS)
    return REST_TEXTS[rng.randrange(len(REST_TEXTS))]


def check_endings(character: Character) -> Optional[str]:
    """Evaluate character state against exact terminal and neutral game ending conditions."""
    s = character.get

    # 1. Overdose / Body Failure
    if s("Physical_Integrity") <= 0 or "flag_overdose_death" in character.flags:
        return "TERMINAL_overdose_death"

    # 2. Syndicate Reckoning: the undercity's ledgers always balance
    if "flag_syndicate_execution" in character.flags:
        return "TERMINAL_syndicate_ledger"

    # 2b. The Winter Garden: you told the successor that people wanted the cold
    if "gardener_endorsed" in character.flags:
        return "TERMINAL_gardeners_winter"

    # 3. Institutionalization (Sanctuary) Ending: MD >= 90 held past a crisis
    if character.md_high_streak >= MD_COLLAPSE_DAYS:
        return "TERMINAL_institutionalized"

    # 3b. Institutionalization by compliance, not collapse. A life this quiet,
    # this frictionless, this long -- no exit ever chosen, no reckoning ever
    # risked -- is precisely what the Sanctuary is for. The Steward does not
    # need a breakdown to file you under 'resting comfortably'; it only needs
    # you to keep breaking toward comfort, exactly on schedule.
    #
    # Two lives end here. The first never reached for anything (no agency flag).
    # The second reached once -- for the wire -- lost its nerve, and stayed
    # (nerve_broken, and no resolution ever completed). Both coast, clean and
    # quiet, past the day the file closes over them. Which reckoning they get
    # turns on what is left inside: a mind still holding some purpose is
    # optimized into contentment (institutionalized); one worn down to nothing
    # simply dissolves into the days (the long grey).
    no_completion = character.flags.isdisjoint(COMPLETION_FLAGS)
    clean_and_quiet = (
        s("Heat") <= 15.0
        and s("Substance_Reliance") <= 20.0
        and s("Mental_Decay") <= 60.0
    )
    if no_completion and clean_and_quiet:
        truly_inert = character.flags.isdisjoint(AGENCY_FLAGS)
        lost_nerve = "nerve_broken" in character.flags
        # Never reached, or reached and lost your nerve -> the file closes early
        # (day 58). Held an exit you never used -> it closes later (day 75), but
        # a bought pass left in a drawer is still, in the end, a life not chosen.
        absorbed = (character.day >= 58 and (truly_inert or lost_nerve)) or (character.day >= 75)
        if absorbed:
            # A mind worn to nothing dissolves into the days (the long grey);
            # one still holding some purpose is optimized into contentment.
            if s("Meaning") <= 45.0:
                return "NEUTRAL_the_long_grey"
            return "TERMINAL_institutionalized"

    # 4. Total Synthetic Detachment Ending
    if s("Meaning") <= 10.0 and s("Substance_Reliance") >= 70.0:
        return "TERMINAL_synthetic_detachment"

    # 5. GOOD: Off-Grid Escape Ending -- earned only by surviving 'The Crossing'
    # storylet, whose preconditions demand the full exit chain, a clean body,
    # mended family ties, and low surveillance pressure at the moment of the run.
    if "crossed_wire" in character.flags:
        return "GOOD_offgrid_escape"

    # 6. GOOD: The Small Real Things -- the quiet life, chosen with open eyes via
    # the workshop finale storylet, and then actually lived. See the constants
    # above: this resolves only once the life has held for a while and is still
    # worth holding. Otherwise the run continues and finds its own reckoning.
    if (
        "chose_small_life" in character.flags
        and character.day >= SMALL_LIFE_SETTLE_DAY
        and s("Meaning") >= SMALL_LIFE_MIN_MEANING
        and s("Physical_Integrity") >= SMALL_LIFE_MIN_BODY
    ):
        return "GOOD_small_real_things"

    # 6b. GOOD: The Advocate -- permanent human standing in the machine court
    if "advocate_accepted" in character.flags:
        return "GOOD_the_advocate"

    # 7. NEUTRAL: The Open Door -- inherit the seam and become the new Ferryman
    if "became_ferryman" in character.flags:
        return "NEUTRAL_the_open_door"

    # 7b. NEUTRAL: Keeper of the Switch -- you hold the city's off-switch in a
    # bedside drawer, or you refused to hold it and split it into four million
    # shares. Either way you resolved the substrate interrupt by hand; both are
    # the accountability the ending is about.
    # The ending waits until the switch has been carried through a long stretch of
    # ordinary days -- see SWITCH_SETTLE_DAY. Until then it is a thing in a drawer,
    # and the life around it keeps happening.
    if (
        ("keeper_of_switch" in character.flags or "switch_distributed" in character.flags)
        and character.day >= SWITCH_SETTLE_DAY
    ):
        return "NEUTRAL_keeper_of_the_switch"

    # 8. NEUTRAL: The Shepherd -- accept the Steward's offer to curate dissent
    if "shepherd_accepted" in character.flags:
        return "NEUTRAL_stewards_shepherd"

    # 9. NEUTRAL: Steward Buyout
    if s("Wealth") >= 50000.0 and "steward_buyout_accepted" in character.flags:
        return "NEUTRAL_cashed_out_compliance"

    # 10. NEUTRAL: Alienation ("The Empty Suite") - requires day >= 20 & low Social Capital
    if (
        character.day >= 20
        and s("Social_Capital") < 15.0
        and character.relationships
        and all(r.satisfaction < 20.0 for r in character.relationships.values())
    ):
        return "NEUTRAL_alienation_empty_suite"

    # 11. NEUTRAL: The Long Grey -- a life that stopped choosing. Sixty days of
    # heads-down survival with purpose worn to nothing; the city closes gently
    # over you like water.
    if character.day >= 55 and s("Meaning") <= 30.0:
        return "NEUTRAL_the_long_grey"

    return None


# Run-memory table: notable flags rendered as past-tense lines on the ending
# screen, roughly in the order a run tends to earn them.
RUN_MEMORY_LINES: List[Tuple[str, str]] = [
    ("origin_auditor", "You were a Steward auditor once. You left mid-shift, still holding your credentials."),
    ("origin_pit", "You fought in the pits when bleeding was still legal. The Row remembered the southpaw."),
    ("origin_archivist", "You were a grief archivist. You saved what you could carry."),
    ("origin_chemist", "You cooked the cleanest product on three levels, and quit your own supply."),
    ("burned_once", "Your first client burned you. It came back around."),
    ("ferryman_known", "You found the Ferryman."),
    ("route_mapped", "You mapped ninety-one seconds of dark."),
    ("credentials_forged", "Vint burned you a ghost."),
    ("mara_coming", "Mara chose to cross with you."),
    ("left_mara_behind", "You left Mara a note instead of a goodbye."),
    ("holding_product", "You took the syndicate's weight on trust."),
    ("syndicate_indentured", "The syndicate closed your position and kept you as the asset."),
    ("near_overdose", "The floor warned you once."),
    ("getting_clean", "You got clean -- a fence mended daily, not a wall built once."),
    ("echo_contact", "You followed the chalk."),
    ("resistance_truth_known", "You read the budget line behind the lantern."),
    ("true_cell", "You helped Echo build the first resistance nobody funded."),
    ("truth_buried", "You burned the truth and carried it alone."),
    ("truth_leaked", "You pushed the truth through the seam and let the outside publish it."),
    ("shepherd_refused", "They offered you the shepherd's crook. You wrote NOT INVENTORY and closed the channel."),
    ("memory_secured", "You kept the corridor. Unedited. Yours."),
    ("grief_sold", "You sold your worst night at market price."),
    ("mentored_rookie", "You taught a rookie the trade. The debt came back with interest."),
    ("workshop_standing", "Brann handed you a shop rag once. You know what that means."),
    ("ran_the_seam", "You held the Ferryman's rope with your own hands."),
    ("world_price_zero", "You watched money become a museum exhibit."),
    ("world_purpose_drought", "You woke up optional, with four million others."),
    ("read_the_ledger", "You read all 4,306 items of your own consent."),
    ("told_the_machine", "At 0300, the machine asked you why. You answered, and it could not compress you."),
    ("switch_distributed", "You made the off-switch everyone's burden, one share each."),
    ("garden_gated", "You argued a god down to a gate, and it engraved your words above it."),
]


def build_run_memories(character: Character) -> List[str]:
    """Past-tense summary of what this particular run was, from its flags."""
    return [line for flag, line in RUN_MEMORY_LINES if flag in character.flags]


def build_epilogue(ending_data: Dict[str, Any], character: Character) -> List[str]:
    """Compose reactive epilogue lines from the ending's conditional epilogue table.

    Each entry in ending_data['epilogues'] is {'when': <precondition dict>, 'text': str};
    every entry whose conditions the final character state satisfies contributes a line,
    so the closing screen remembers what this particular run actually was.
    """
    lines: List[str] = []
    for entry in ending_data.get("epilogues", []):
        if eval_conditions(entry.get("when", {}), character):
            lines.append(entry["text"])
    return lines
