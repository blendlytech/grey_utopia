"""decay.py -- Decay and substance tolerance/withdrawal math for GREY UTOPIA."""
from __future__ import annotations
import math
import random
from typing import Any, Dict, Optional, Set
from engine.stats import Character, clamp

# Named mathematical constants
ALPHA_MOOD: float      = 0.30   # EMA smoothing when the mind is worsening (stress > mood)
ALPHA_MOOD_DOWN: float = 0.24   # Recovery is slower than harm: bad days scar and linger,
                                # so a long grey life ratchets Mental_Decay upward even
                                # when no single day is catastrophic (hysteresis).
K_MEANING: float    = 0.80   # Baseline Meaning degradation per idle day
K_ADAPT: float      = 4.60   # Hedonic adaptation: the Steward normalizes whatever you win
ADAPT_EXP: float    = 2.0    # Curvature of that normalization (superlinear near the ceiling)
DROUGHT_MULT: float = 1.55   # After The Last Shift, purpose evaporates faster citywide
E_MAX: float        = 100.0  # Maximum subjective drug effect
ED50: float         = 10.0   # Base dose for 50% effect at zero tolerance
K_TOL: float        = 0.15   # Tolerance increment constant per use
D0: float           = 15.0   # Dose saturation constant for tolerance escalation
LAMBDA_REC: float   = 0.05   # Tolerance decay rate per clean day
K_UP: float         = 0.40   # Substance reliance increase per dose unit
K_DOWN: float       = 0.80   # Substance reliance decrease per clean day
TAU_WD: float       = 2.0    # Withdrawal severity ramp time constant (days)
K_COOL: float       = 4.0    # Surveillance Heat decrease per quiet day
K_OD: float         = 0.045  # Overdose probability scaling constant
# Raised alongside the tenure attrition below. That attrition is superlinear in
# how much body you have left, so it barely touches a wrecked one -- meaning a
# flat regen rate that was balanced against injury alone now decides, almost by
# itself, whether a badly hurt run recovers or bleeds out. A higher floor gives
# bold play a real road back from the edge without softening the attrition on the
# intact, careful lives, which is where the late-game pressure is supposed to sit.
PHYS_REGEN: float   = 1.50   # Body recovery rate per day


def update_mood(mental_decay: float, stress_today: float, alpha: float = ALPHA_MOOD) -> float:
    """Asymmetric EMA of stress -> Mental_Decay.

    The mind takes on stress faster than it sheds it: a hard day moves the mood
    toward it at ALPHA_MOOD, but a calm day only recovers at ALPHA_MOOD_DOWN.
    The result is hysteresis -- Mental_Decay ratchets upward over a long, worn
    life even when no single day is a crisis, which is how the grey wins.
    """
    a = alpha if stress_today >= mental_decay else ALPHA_MOOD_DOWN
    return a * stress_today + (1.0 - a) * mental_decay


# Endogenous stress weights: pressure comes from the life you are living,
# not a coin flip. Steady-state Mental_Decay converges to mean daily stress.
STRESS_BASE_LO: float = 8.0
STRESS_BASE_HI: float = 22.0
W_HEAT: float       = 0.36   # Surveillance pressure
W_FRICTION: float   = 0.18   # Family conflict rumination
W_INJURY: float     = 0.28   # Pain from lost Physical_Integrity
W_WITHDRAWAL: float = 38.0   # Withdrawal severity (0..1) amplification
W_RECK: float       = 0.08   # A reckless life is a loud life; it grinds the mind
W_ANOMIE: float     = 0.55   # Meaninglessness pressure: a purposeless life is its own stressor
MEANING_FLOOR: float = 35.0  # Below this, absence-of-purpose starts feeding the grind

# Tenure: the file thickens. Every other stressor here is something you did -- a
# job that went wrong, a habit, a sister you stopped calling -- and all of them
# can be avoided by simply never reaching for anything, which left a hole: a life
# of perfect caution accrued no cost at all and could not lose. The Steward is not
# scored on your conduct. It is patient, it is always watching, and the longer it
# watches the more of you it has on file. Attention itself is the attrition, and
# it is the one pressure that cannot be played around -- only outrun, by resolving
# into something before the file closes.
#
# The mind's share is deliberately gentle. A bold life already carries injury,
# withdrawal and Heat into daily stress; pricing attention steeply on top of that
# kills every daring run twice for one mistake. This term only has to make the
# late game feel watched.
W_TENURE: float      = 0.15  # stress per day lived past the grace period
TENURE_ONSET: int    = 26    # days before the city's attention starts to compound
TENURE_CAP: float    = 14.0  # ceiling on tenure pressure

# The body's share is where tenure actually closes lives, because the Sanctuary
# only takes the calm -- its precondition is a quiet mind -- so stress alone can
# never end a careful run; it merely disqualifies it from the one ending that was
# reaching for it. Attrition has to land somewhere caution cannot deflect.
#
# Three properties, each load-bearing:
#
#   onset -- late, and for the same anti-double-counting reason as above. A
#   reckless life is already shedding Physical_Integrity to injury and withdrawal
#   and reaches its own reckoning around day 50. Starting earlier would just
#   charge it twice. The wear begins where the other roads have run out.
#
#   scaled by emptiness -- ANOMIE_BODY_FLOOR's idea carried into the long game: a
#   body is maintained by having a reason to maintain it. Flat wear would be a
#   cliff, since careful runs hold near-identical Physical_Integrity and would all
#   cross zero on the same day, turning the endgame into a scripted countdown.
#   Keying it to Meaning spreads that day across runs and puts the spread where it
#   belongs -- on the lives with least left to get up for.
#
#   scaled by the body still standing, superlinearly -- attrition takes a share
#   of what is there to take, and the exponent decides how sharply it stops
#   taking. This is the term that separates a careful run from a bold one: at
#   TENURE_BODY_EXP = 2 an intact body (PI 95) absorbs roughly four times the wear
#   of a wrecked one (PI 46), so the long clean life is what this closes, while
#   the ruined one keeps paying through W_INJURY and withdrawal, which already own
#   that range. Lower the exponent and bold play starts dying twice for one
#   mistake; raise it and caution becomes immortal again.
#
# TENURE_BODY_RESERVE is small but load-bearing. Without it the wear is purely
# proportional to what is left, so it self-limits: a worn body sheds less and
# less and settles at a low equilibrium instead of ever reaching zero. Runs then
# spend their last stretch at single-digit Physical_Integrity, permanently
# fragile but unkillable by attrition alone. The reserve is the part of the cost
# that does not scale down -- the share the city takes whether or not you can
# afford it -- and it is what lets a long, quiet, unresolved life actually end.
#
# It is gated on a quiet mind, and that gate is the whole reason it can exist. A
# flat reserve lands hardest on whoever has least body left, which is exactly the
# reckless run, and it turned bold play into a bloodbath every time it was tried.
# Keying it to Mental_Decay inverts that: the calm, unbothered life pays it in
# full, and the life already coming apart barely pays it at all -- because that
# life is being closed by W_INJURY, withdrawal and its own choices, and does not
# need attention to finish it. Attrition is what the city does to people nothing
# else is happening to.
K_TENURE_BODY: float     = 4.20  # physical wear per day lived past the body's grace period
TENURE_BODY_ONSET: int   = 50    # days before simply continuing starts to cost the body
TENURE_BODY_BASE: float  = 0.35  # wear floor for a life that still has a reason to keep itself
TENURE_BODY_SPAN: float  = 1.15  # additional wear scaled by how empty the life has become
TENURE_BODY_RESERVE: float = 0.16  # wear that lands regardless of condition, if the mind is quiet
TENURE_BODY_MD_REF: float  = 55.0  # Mental_Decay at which the reserve has faded to nothing
TENURE_BODY_EXP: float   = 2.0    # curvature of the condition scaling

# Physical neglect: a life emptied of purpose stops maintaining itself. Below
# ANOMIE_BODY_FLOOR, low Meaning bleeds Physical_Integrity faster than the body
# can regenerate -- the quiet body-failure road out for a player who simply
# stops choosing to live.
ANOMIE_BODY_FLOOR: float = 22.0
K_ANOMIE_BODY: float     = 0.70


def tenure_pressure(day: int) -> float:
    """Stress contributed purely by how long the Steward has been watching you."""
    return min(TENURE_CAP, W_TENURE * max(0, day - TENURE_ONSET))


def tenure_body_wear(
    day: int,
    meaning: float,
    physical_integrity: float = 100.0,
    mental_decay: float = 0.0,
) -> float:
    """Physical cost of simply having continued.

    Scaled by how empty the life has become and by how much body is left to take,
    plus a reserve that only a still-quiet mind pays.
    """
    days = max(0, day - TENURE_BODY_ONSET)
    if not days:
        return 0.0
    emptiness = 1.0 - clamp(meaning, 0.0, 100.0) / 100.0
    proportional = (clamp(physical_integrity, 0.0, 100.0) / 100.0) ** TENURE_BODY_EXP
    quiet = max(0.0, 1.0 - clamp(mental_decay, 0.0, 100.0) / TENURE_BODY_MD_REF)
    condition = proportional + TENURE_BODY_RESERVE * quiet
    return K_TENURE_BODY * days * (TENURE_BODY_BASE + TENURE_BODY_SPAN * emptiness) * condition


def compute_daily_stress(character: Character, rng: Optional[random.Random] = None) -> float:
    """Daily stress load derived from character state plus a small random jitter.

    High Heat, family conflict, injury, and withdrawal compound into the kind of
    sustained stress that can push Mental_Decay toward the Sanctuary threshold.
    """
    rng = rng or random.Random()
    wd = withdrawal_severity(character.get("Substance_Reliance"), character.days_since_use)
    stress = (
        rng.uniform(STRESS_BASE_LO, STRESS_BASE_HI)
        + W_HEAT * character.get("Heat")
        + W_FRICTION * character.get("Family_Friction")
        + W_INJURY * (100.0 - character.get("Physical_Integrity"))
        + W_WITHDRAWAL * wd
        + W_RECK * character.get("Recklessness")
        + W_ANOMIE * max(0.0, MEANING_FLOOR - character.get("Meaning"))
        + tenure_pressure(character.day)
    )
    return clamp(stress, 0.0, 100.0)


def meaning_drift(meaning: float, drought: bool = False) -> float:
    """Daily Meaning bleed, accelerating with how much Meaning you already hold.

    A flat bleed lets a good run bank purpose to the ceiling and sit there, which
    is the one thing this city does not permit. Meaning here is not a score you
    accumulate; it is a thing the Steward sands down in proportion to how much of
    it you have. Win big and the win is normalized fast -- the parade, the fixed
    thing, the person you saved all get absorbed into 'resting comfortably' at a
    rate that scales with the height you reached. Scrape along near nothing and
    the bleed is gentle, because there is almost nothing left to take.

    The practical effect is an equilibrium rather than a ceiling: purpose has to
    be re-earned continuously, so a life stops being meaningful the moment it
    stops reaching, and the anomie floors below become live failure states
    instead of unreachable theory.
    """
    drift = K_MEANING + K_ADAPT * (max(0.0, meaning) / 100.0) ** ADAPT_EXP
    return drift * (DROUGHT_MULT if drought else 1.0)


def relationship_retention(satisfaction_base: float, days_since: int, strength: float) -> float:
    """Ebbinghaus forgetting curve: R = e^(-t/S)."""
    R = math.exp(-days_since / max(strength, 0.001))
    return satisfaction_base * R


def dose_effect(dose: float, tolerance: float) -> float:
    """Saturating Hill/Michaelis-Menten curve with rightward ED50 shift."""
    if dose <= 0:
        return 0.0
    return E_MAX * dose / (dose + ED50 * (1.0 + tolerance))


def escalate_tolerance(tolerance: float, dose: float) -> float:
    """Tolerance escalation upon drug use."""
    return tolerance + K_TOL * (1.0 - math.exp(-dose / D0))


def recover_tolerance(tolerance: float, days_clean: int) -> float:
    """Tolerance decay during abstinence."""
    return tolerance * math.exp(-LAMBDA_REC * days_clean)


def withdrawal_severity(reliance: float, days_since_use: int) -> float:
    """Withdrawal severity ramp while abstinent."""
    if reliance <= 0 or days_since_use <= 0:
        return 0.0
    return (reliance / 100.0) * (1.0 - math.exp(-days_since_use / TAU_WD))


def overdose_probability(dose: float, reliance: float, physical_integrity: float) -> float:
    """Calculate overdose death probability."""
    if dose <= 0:
        return 0.0
    p = (dose * (1.0 + reliance / 100.0)) / (physical_integrity + 1.0) * K_OD
    return clamp(p, 0.0, 0.95)


def end_of_day_decay(
    character: Character,
    stress_today: float,
    used_today: bool = False,
    dose: float = 0.0,
    meaningful_act: bool = False
) -> None:
    """Apply one full day of statistical decay and time progression to a Character.

    Substance doses taken during the day's storylets accumulate on
    character.pending_dose (via resolver.apply_dose) and are consumed here, so
    the tolerance/withdrawal pharmacology reacts to what was actually lived.
    """
    # 0. Collect the day's accumulated dose from resolved storylets
    dose = dose + character.pending_dose
    character.pending_dose = 0.0
    used_today = used_today or dose > 0

    # 1. Update Mood (EMA)
    character.set("Mental_Decay", update_mood(character.get("Mental_Decay"), stress_today))

    # 2. Meaning drift -- after The Last Shift, when no one is needed for
    # anything, purpose evaporates twice as fast citywide.
    if not meaningful_act:
        drift = meaning_drift(
            character.get("Meaning"),
            drought="world_purpose_drought" in character.flags,
        )
        character.add("Meaning", -drift)

    # 3. Physical body slow regeneration, against the accumulated wear of simply
    # having been here -- past TENURE_ONSET the second term outgrows the first.
    character.add("Physical_Integrity", PHYS_REGEN)
    character.add("Physical_Integrity",
                  -tenure_body_wear(character.day, character.get("Meaning"),
                                    character.get("Physical_Integrity"),
                                    character.get("Mental_Decay")))

    # 3b. Anomie neglect: a life gutted of meaning stops tending the body. Below
    # the floor, the deficit outpaces regeneration and the body quietly fails.
    meaning_now = character.get("Meaning")
    if meaning_now < ANOMIE_BODY_FLOOR:
        character.add("Physical_Integrity", -K_ANOMIE_BODY * (ANOMIE_BODY_FLOOR - meaning_now))

    # 4. Substance usage vs abstinence accounting
    if used_today and dose > 0:
        character.days_since_use = 0
        character.set("Tolerance", escalate_tolerance(character.get("Tolerance"), dose))
        character.add("Substance_Reliance", K_UP * dose)
    else:
        character.days_since_use += 1
        character.set("Tolerance", recover_tolerance(character.get("Tolerance"), character.days_since_use))
        character.add("Substance_Reliance", -K_DOWN)
        character.add("Heat", -K_COOL)

        # Withdrawal penalties feed into stress and physical wear
        wd = withdrawal_severity(character.get("Substance_Reliance"), character.days_since_use)
        character.add("Mental_Decay", 15.0 * wd)
        character.add("Physical_Integrity", -6.0 * wd)

    # 5. Relationship decay (Ebbinghaus forgetting curve, one day's retention per day)
    for r in character.relationships.values():
        r.satisfaction = relationship_retention(r.satisfaction, 1, r.strength)

    # 6. Institutionalization tracking streak
    if character.get("Mental_Decay") >= 90.0:
        character.md_high_streak += 1
    else:
        character.md_high_streak = 0

    # 7. Deadline clocks tick toward their reckonings
    for name in list(character.clocks.keys()):
        character.clocks[name] -= 1
        if character.clocks[name] <= 0:
            del character.clocks[name]
            character.flags.add(f"clock_{name}_expired")

    character.day += 1


def build_day_report(
    character: Character,
    stress: float,
    stats_before: Dict[str, float],
    clocks_before: Set[str],
) -> Dict[str, Any]:
    """Snapshot a day transition into the shape the night ledger and
    ambient.steward_ledger_line consume.

    Call with a stats/clocks snapshot taken immediately before
    end_of_day_decay, and the stress value that same call was passed --
    both main.py and server.py build this the same way so the two front
    ends never drift on what "yesterday" means.
    """
    overnight = {
        k: round(character.stats[k] - v, 1)
        for k, v in stats_before.items()
        if abs(character.stats[k] - v) >= 0.1
    }
    return {
        "new_day": character.day,
        "stress": round(stress, 1),
        "withdrawal": character.days_since_use > 0 and character.get("Substance_Reliance") > 20.0,
        "md_streak": character.md_high_streak,
        "clocks": dict(character.clocks),
        "overnight": overnight,
        "clocks_expired": sorted(clocks_before - set(character.clocks)),
    }
