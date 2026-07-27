# AMBITIONS BIBLE — Player-Chosen Long-Form Quests (Depth Plan Item D)

Fable 5 design, July 26 2026. Prose execution for the connective beats assigned to
Sonnet 5. Fable-written picker + finale events live in
`data/events/ambitions_pack.json` (7 events: 1 picker + 3 finales + 3 gamble beats —
DONE, do not rewrite them). Sonnet target: extend the same file with the 18
connective beats specced in §4 (6 per ambition).

`docs/VOICE_BIBLE.md` is law for all prose. `docs/CAST_BIBLE.md`'s balance-ledger
lessons (§6 there) are law for all mechanics in this document — this spec was
written already knowing them, not re-deriving them.

---

## 1. Design intent

The depth-plan diagnosis: "THE DEPRECATION happens TO the world; nothing is a
chosen multi-beat personal quest with a bespoke finale." Citizen Sleeper's Drives
and Fallen London's Ambitions both give the player something to actively *want*
across dozens of sessions, distinct from reacting to the world or to an NPC's
arc. This pack adds exactly that: one optional pick, at the top of the run, that
recolors the whole rest of it.

**Zero engine change, by construction.** Every ambition's finale grants a flag
`check_endings` (`engine/resolver.py`) *already* checks — `chose_small_life`,
`flag_syndicate_execution`, `crossed_wire`, `nerve_broken`, `shepherd_accepted` —
verified by reading `resolver.py` directly this session, not assumed. No new
ending type, no resolver.py touch, no Checkpoint-3 violation. What makes each
ambition feel bespoke is (a) its own 8-beat narrative spine and (b) its own
epilogue entries layered onto whichever shared ending it resolves into — the
same trick `origin_threads_pack` and `cast_expansion_pack` already use.

**Collision-checked against existing content** (verified by reading the actual
files, not assumed):
- `chose_small_life` is set today only by `hz_workshop_finale` (Brann's chain).
  Two ambitions below also grant it — multiple roads into one ending is the
  established, encouraged pattern (Brann's apprenticeship already does exactly
  this for the "quiet life" thesis).
- `crossed_wire`'s base ending text is specific: "Crossing costs you two fingers'
  width of skin on the wire... the wind arrives unfiltered." Any ambition
  granting it MUST end in an actual wire-crossing, not a different escape
  method, or the epilogue will contradict the base text. Ambition C is designed
  around this constraint on purpose (see §3C).
- `advocate_accepted` is NOT used by any ambition here. It is gated behind
  `asc_the_advocate`, which itself requires `world_successor` (ascension_pack's
  AI-succession world-arc, day 28-31, Meaning>=55/MD<=55) — a personal ambition
  routing into "a chair in the rendered courtroom where two weathers argue about
  what human beings are for" would be a narrative non-sequitur. Left untouched.
- `holding_product` / `syndicate_consignment` clock is fable_flagship_pack's own
  near-universal early mechanic (fires for most runs, not exclusive to any
  ambition) — Ambition A does NOT hook into it. It mints its own bespoke debt
  flag and clock instead, so its failure scene isn't secretly gated behind
  content some players never triggered.
- `nerve_broken` already has a recovery event (`hz_nerve_rebuilt`, horizon_pack).
  Ambition C's failure reuses it deliberately, for free narrative and mechanical
  support.

---

## 2. The picker

**`amb_the_choosing`** (new event, weight 14, `max_fires: 1`, tags
`["existential"]`, preconditions `{"day": 6, "op": ">="}` only — universal,
no other gate, so every run sees it once past the prologue settling). Body:
a quiet morning the Steward would call "a wellness check-in on personal
direction" — the player is asked, in effect, what they actually want, distinct
from what today's jobs demand. Four choices, all `prob.base: 1.0` (a
declaration of intent isn't a gamble):

1. **`pursue_clean_name`** → sets `ambition_clean_name`. One-line hook: an old
   debt, unpaid, with a name attached.
2. **`pursue_the_signal`** → sets `ambition_the_signal`. Hook: something true
   that should survive you, recorded honestly.
3. **`pursue_second_door`** → sets `ambition_second_door`. Hook: a way out that
   isn't borrowed from anyone else's mercy.
4. **`decline_ambition`** → sets nothing. Hook: today has enough in it already.

No stat deltas on any branch beyond a token +1 Meaning (choosing a direction,
however small, is itself the tiniest bit of agency) — this event is a fork,
not a reward, and per the cast_expansion lesson, even a token amount times how
often it's evaluated adds up, so keep it at +1 flat on all four branches
(net-zero to the choice; it doesn't change which one wins bot argmax since
all four tie at the same value, and Python's first-max tie-break sends every
deliberate bot to whichever option is listed first — see §5 for why that's
handled deliberately, not left to chance).

---

## 3. The three ambitions — 8 beats each (2 Fable finale + 6 Sonnet connective)

Shared mechanics unless stated otherwise: `max_fires: 1`, `cooldown: 2`,
weight 5-8, ≥3 choices, `prob` on every choice, symbol ops only, gated `all`
on the ambition flag + a day threshold per beat (spread roughly days 10, 16,
22, 28, 34, 40, 46, finale ~52-56 — leaves runway before the day-58/75
absorption checks and the day-55 long-grey check in `check_endings`).
Beat N (except beat 1) also requires beat N-1's flag. Copy the JSON shape of
`origin_threads_pack.json` events — do not invent schema.

### A. "The Clean Name" — an old debt, paid clean or paid in blood

Gate: `ambition_clean_name`. Thesis: the debt is real, specific, and named
(a person, not an abstraction) — the player chooses HOW to close it, and the
choice is the whole ambition.

1. **`amb_clean_1_the_name`** (day≥10) — the debt surfaces: a specific old
   client/mark from before the story began, owed something concrete (money,
   an apology, a returned favor) that's been quietly compounding. Sets
   `clean_thread_1`.
2. **`amb_clean_2_the_ledger`** (day≥16, requires `clean_thread_1`) — sizing
   the debt honestly for the first time (it's worse than remembered, or
   smaller and more embarrassing than remembered — writer's choice). Sets
   `clean_thread_2`.
3. **`amb_clean_3_first_payment`** (day≥22) — a first real installment,
   costly, on-page. Sets `clean_thread_3`.
4. **`amb_clean_4_the_setback`** (day≥28) — something threatens the plan (a
   Heat spike, a rival claim on the same money, the creditor's patience
   running out). Sets `clean_thread_4`, starts clock `debt_patience` (14 days).
5. **`amb_clean_5_second_payment`** (day≥34) — the harder installment; this is
   where the ambition can visibly go either way. Sets `clean_thread_5`.
6. **`amb_clean_6_the_reckoning_offer`** (day≥40) — someone offers a shortcut
   (sell something, betray someone, take a job that would clear the debt in
   one stroke but isn't clean). Sets `clean_thread_6`.
7. **`amb_clean_finale_the_last_payment`** (Fable, day≥46, consumes
   `clock_debt_patience_expired` OR `clean_thread_6`) — the last act.
   - **Pay it clean** (requires the debt actually being tracked down, i.e.
     `clean_thread_5`) → success `debt_paid_clean` + `chose_small_life`
     (routes to `GOOD_small_real_things`, bespoke epilogue: a debt that
     doesn't follow you into the small life you built).
   - **Let the patience run out** → `debt_collectors_move`, starts clock
     `debt_collection` (7 days) — a genuine escalation, not an instant ending.
   - **Take the dirty shortcut** → success `debt_paid_dirty` (clears the
     debt, Heat/Meaning cost, no ending flag — the debt is gone but nothing
     is resolved; run continues on its own merits); failure `debt_collectors_move`
     (same escalation as declining).
8. **`amb_clean_8_the_collectors`** (Fable, consumes `clock_debt_collection_expired`)
   — the collectors arrive. This is the ONLY beat that sets
   `flag_syndicate_execution` (on its own failure branch, base 0.5 -- a real
   chance to talk/fight/buy your way out even this late), giving the ambition
   a genuine bad ending distinct from every other TERMINAL path in the game
   currently reachable through it. Success clears the debt at heavy cost
   (Wealth, Heat) with no ending flag, same as the dirty-shortcut success.

### B. "The Signal" — an independent record, built to survive you

Gate: `ambition_the_signal`. Thesis: not the archivist origin's grief-ledger,
not Echo's resistance cell — a personal act of honest documentation the player
builds from nothing, aimed at outliving them rather than winning anything.

1. **`amb_signal_1_the_idea`** (day≥10) — what to record, and why it has to be
   this specific thing (not abstract "the truth," a concrete fact/account
   that would otherwise be lost). Sets `signal_thread_1`.
2. **`amb_signal_2_first_entry`** (day≥16) — the first real entry, and the
   discovery that honesty is harder to sustain than secrecy. Sets `signal_thread_2`.
3. **`amb_signal_3_a_witness`** (day≥22) — someone else learns what the
   player is building and has to decide whether to help, ignore, or report
   it. Sets `signal_thread_3`.
4. **`amb_signal_4_the_near_miss`** (day≥28) — a close call with discovery
   (a sweep, a nosy neighbor, a Steward routine audit) that doesn't catch the
   record but proves it's fragile. Sets `signal_thread_4`.
5. **`amb_signal_5_the_offer`** (day≥34) — **DESIGNED GAMBLE.** The Steward
   (via an intermediary, not directly — it never negotiates in its own voice)
   offers to "preserve" the record officially, curated. Base 0.35, no mods.
   Success (event max, reckless's pick): the player refuses convincingly and
   the record stays independent, `signal_refused_curation` + a real Heat/Meaning
   cost that pays off narratively. Failure (event worst): the refusal is read
   as instability, `signal_flagged` + Mental_Decay/Heat hit (recipe: Meaning -8,
   MD +5 — do NOT invent a harsher number without gate-testing it first; see
   §6). Third choice (co-pick target, `base:1.0`): accept the offer outright →
   `signal_curated` (sets up beat 7's compromise ending directly).
6. **`amb_signal_6_the_last_entry`** (day≥40) — the record is nearly
   complete; this beat is about what NOT to include (naming a living person,
   admitting a crime) — the last editorial choice before it's finished. Sets
   `signal_thread_6`.
7. **`amb_signal_finale_release`** (Fable, day≥46, requires `signal_thread_6`)
   — how the record gets out into the world (or doesn't).
   - **Bury it somewhere it'll be found later** (requires NOT `signal_flagged`)
     → success `signal_preserved` + `chose_small_life` (routes to
     `GOOD_small_real_things`; bespoke epilogue: an honest record, unglamorous,
     real, waiting).
   - **Hand it to the curation offer** (requires `signal_curated`) →
     `signal_absorbed` + `shepherd_accepted` (routes to `NEUTRAL_stewards_shepherd`
     — the record survives, laundered into managed dissent; bespoke epilogue
     distinguishes this from the shepherd ending's other entry points).
   - **Publish it loud, now, no more waiting** → gamble, base 0.4: success
     `signal_public` (real Fame/Meaning payoff, no ending flag — the record is
     out, the run continues); failure (`signal_flagged`-equivalent heavy
     Heat/Mental_Decay hit; if `signal_flagged` was already set from beat 5,
     stack this deliberately toward the natural institutionalization path
     rather than forcing a flag — see §1's note on not force-triggering
     `TERMINAL_institutionalized` directly).

### C. "The Second Door" — a way out you didn't borrow from anyone

Gate: `ambition_second_door`. Thesis: distrust of the Ferryman's mantle
specifically (fits the Cast Bible's established Ferryman canon: "the toll
book prices what crossers carry" — this ambition is about a crosser who
refuses to be a line in that book). **Must end in an actual wire-crossing**
(per §1's collision note) — the ambition is about *how you get to the wire*,
not a different physical escape.

1. **`amb_second_1_the_refusal`** (day≥10) — the player decides, on their own,
   not to seek out the Ferryman even if the opportunity arises (works whether
   or not `ferryman_known` is already set — if it is, this is explicitly
   turning down her help; insert either way). Sets `second_thread_1`.
2. **`amb_second_2_first_readings`** (day≥16) — starting from nothing: sensor
   logs, patrol timings, the unglamorous grind of independent reconnaissance.
   Sets `second_thread_2`.
3. **`amb_second_3_a_source`** (day≥22) — a maintenance worker, a data
   broker, or a smuggler (NOT the Ferryman) becomes an unwitting or willing
   source of the timing data the player needs. Sets `second_thread_3`.
4. **`amb_second_4_the_wrong_gap`** (day≥28) — a mapped gap turns out to be
   sensor recalibration, not a real seam — a costly false lead. Sets
   `second_thread_4`.
5. **`amb_second_5_the_real_gap`** (day≥34) — the actual seam, found
   independently, distinct from the Ferryman's ninety-one-second window (a
   different duration/location — the player's own door, not a copy of hers).
   Sets `second_thread_5`.
6. **`amb_second_6_dry_run`** (day≥40) — testing the timing without crossing
   (a rehearsal, not the attempt) — this is where genuine failure first
   becomes possible. Sets `second_thread_6`.
7. **`amb_second_finale_the_crossing`** (Fable, day≥46, requires
   `second_thread_6`) — the attempt itself. **DESIGNED GAMBLE**, base 0.4
   (slightly more generous than the flagship Crossing's odds, since this path
   is more prepared, not less — the whole ambition has been the preparation).
   - Success (event max) → `crossed_wire` + `second_door_solo` (routes to
     `GOOD_offgrid_escape`; bespoke epilogue: no Ferryman's name on this
     departure, nobody's toll book marked).
   - Failure (event worst, recipe: PI -8, `nerve_broken` set — reuses
     `hz_nerve_rebuilt`'s existing recovery content, per §1) → the attempt
     fails exactly like the flagship Crossing's failure, same mechanical
     shape, different door.
   - Third choice (co-pick target, `base:1.0`): **wait for a better window**
     → `second_door_waiting`, no ending flag, small Meaning cost (the run
     continues; the door stays open for a future attempt via ordinary play,
     not a second scripted beat — do not add one).
8. **`amb_second_8_aftermath`** (Fable, fires only if `second_door_waiting`
   is set and no crossing has happened by day≥52) — a coda beat: either
   another attempt (re-fires the finale's gamble via a `requires` on
   `second_door_waiting`, `max_fires:1`, so this is the ONE re-roll allowed)
   or a choice to fold the project into ordinary life (small Meaning cost,
   no ending flag, `second_door_folded`).

---

## 4. The 18 Sonnet connective beats (specs)

Beats 1, 2, 3, 4, 6 of each ambition (A/B/C) = 15 beats, plus signal's beat 6
already counted — recount: each ambition has 8 numbered beats above; 2 per
ambition are Fable-written (the finale + one gamble/pivot beat: A's beat 7+8,
B's beat 5+7, C's beat 7+8) = 6 Fable beats total (already drafted in
skeleton form above — Sonnet expands these to full prose using the same
recipe pattern as `origin_threads_pack`'s gambles, do not alter the mechanical
shape). The remaining **18 beats** (A1-4,6; B1-4,6; C1-6) are Sonnet's to
write in full (prose + exact deltas), following the per-beat one-line specs
in §3 verbatim — do not invent additional beats, flags, or gates.

Batching: A1-6, B1-6, C1-6 (three batches of 6, lint between each).

---

## 5. Balance ledger — HARD RULES (informed by this session's cast_expansion fight)

**The picker forces a co-pick, exactly like a scripted slot — treat all three
ambition chains as scripted content for balance purposes, not pool content.**
All four picker choices are `base:1.0`; cautious/reckless/greedy therefore all
collapse to the SAME choice (Python's first-max tie-break on equal scores) —
meaning every deliberate bot commits to ONE ambition, and that ambition's
entire 8-beat chain then behaves exactly like a Reviews/origin-threads
scripted slot for that bot (fires reliably, same shared co-picks). Budget
accordingly: this is the origin-threads playbook, not the cast_expansion
playbook.

1. **Meaning on every non-gamble co-pick branch: 0.** Route all "reward" text
   through Wealth, relationships (`rel_deltas`, note: these DO enter
   `branch_score` at 0.3x — corrected this session, do not treat them as
   bot-invisible), flags (bot-invisible unless in `FLAG_UTILITY`, which these
   new flags are not), and especially `faction_deltas` (fully bot-invisible —
   prefer this channel for any texture reward that doesn't need to move
   argmax). Walk-away / decline choices may run Meaning -1..-2, matching the
   Choice Contract's real-bill requirement.
2. **Exactly one designed gamble per ambition** (signal's beat 5, second
   door's finale; Clean Name's finale is a 3-way branch that is NOT a
   `base<1.0` gamble on its main path — its "gamble" energy lives in beat 8's
   0.5-base collectors scene instead). Recipe: `base` in the 0.35-0.4 range,
   empty mods, failure = Meaning -8/MD +5 (matching the origin-threads
   recipe exactly, since that is the ONE version of this recipe verified this
   session to behave predictably — do NOT invent a harsher failure penalty
   speculatively; if the gate needs more margin later, harden an EXISTING
   embedded gamble first, per finding below).
3. **If the gap breaks after this pack ships: do not tune this pack's own
   gambles first.** This session found, reproducibly, that hardening a
   brand-new gamble's failure penalty has weak and sometimes *backwards*
   effects on the greedy-reckless gap, while hardening the existing, deeply-
   embedded `origin_threads_pack.json` auditor gamble
   (`stand_in_the_doorway`) is a reliable, predictable lever. If item D's gate
   run needs gap margin, that is the first place to look — not these new
   events.
4. **Which ambition wins the picker's tie-break matters and must be checked,
   not assumed.** Order the four choices in `amb_the_choosing` deliberately;
   whichever is listed first among the tied-score set is where EVERY
   deliberate bot's ambition content comes from. Verify this with a quick
   in-process check (same trick as the origin-picker tie-break finding in
   [[grey-utopia-balance-levers]]) before the first full gate run, not after.
5. **Forbidden:** setting/clearing any flag outside this pack's namespace
   (`ambition_*`, `clean_thread_*`, `signal_thread_*`, `second_thread_*`,
   `debt_*`, `signal_*`, `second_door_*`) except the five explicitly-approved
   shared ending flags (`chose_small_life`, `flag_syndicate_execution`,
   `crossed_wire`, `nerve_broken`, `shepherd_accepted`) at the exact finale
   beats named in §3. No touching `holding_product`, `syndicate_consignment`,
   `advocate_accepted`, `world_successor`, `ferryman_known` (reference/insert
   only), or any existing pack. No `family` tag. Harm severity 10-14 on bad
   branches, cap 25/stat, matching house style.
6. **Family_Friction total across the whole pack: 0.** Same reservation as
   the cast-expansion pass — that lever belongs to the Reviews pack's tuning.

---

## 6. Verification gate (run after Sonnet completes all 18 beats)

```
python -m unittest discover -s tests
python pipeline/lint_content.py
python tests/pargate.py
```

Watch order: greedy-reckless gap (>=3) FIRST — current baseline going into
this item is +4.3 with real margin (see [[grey-utopia-balance-levers]]), the
best starting position any item in this plan has had. Then cautious good
<=40 (currently 35.8, margin 4.2) and cautious institutionalized <=22
(currently 20.8, margin 1.2) — both comfortable but not enormous; this
pack's picker co-pick still injects a full 8-beat scripted-equivalent chain
into cautious's run, so do not assume the margin absorbs a careless design.
If anything breaks: diagnose via the tie-break check in rule 4 before
touching any deltas.
