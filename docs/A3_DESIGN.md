# A3 -- Make the Steward take a turn: design note (Phase 1)

**Window:** 2026-07-29, Opus 5, in-session.
**Shape:** A1 Phase 1's -- design note, measured proof-of-concept, ship it
**disabled**, STOP before wiring live.
**Status:** mechanism built and measured. `STEWARD_CADENCE = None`. Nothing in
the shipped game behaves differently; `coverage_audit --assert` reproduces the
recorded baseline exactly, which is the proof rather than the claim.

Reproduce everything below with:

```bash
python tests/steward_audit.py --presence     # is the Steward already on screen?
python tests/steward_audit.py --trigger      # Heat vs the file
python tests/steward_audit.py --cadence 7    # what a weekly filing costs
```

---

## 0. Step 0: the item's premise is wrong in both directions

`STEAM_READINESS_BACKLOG.md` §3 says the Steward "is currently a stat modifier
with 6 events in `data/events/steward_interventions.json`", and §4 of the
handoff asked for that number to be re-verified before anything was designed
against it. It should have been: **the file holds 2 events**
(`steward_wellness_check`, `steward_buyout_offer`), and every other clause in
that sentence is also false.

### 0.1 The Steward is not absent. It is ubiquitous.

125 events in the deck are tagged `steward` -- 25% of the deck. Measured at
n=40 per strategy:

| | random | cautious | reckless | greedy |
|---|---|---|---|---|
| median run | 30 d | 62 d | 54 d | 59 d |
| Steward fires per run | 26.7 | 43.6 | 43.0 | 41.7 |
| distinct days it appears | 19.6 | 33.3 | 32.0 | 32.7 |
| **share of days it appears** | **59.7%** | **53.9%** | **56.4%** | **53.8%** |
| longest silence | 4.7 d | 6.3 d | 5.9 d | 5.9 d |

The Steward is on screen on **more than half of every run's days** and is never
quiet for a full week. "Ten atmospheric mentions" is a 40x undercount.

### 0.2 It already takes a scheduled turn, and that turn already works.

`prologue_continuity_review` -> `review_second_session` (d10) ->
`review_third_session` (d20) -> `review_final_session` (d30) is a forced
(`weight: 500000`), flag-chained, day-gated ladder in
`fable_reviews_pack.json` + `prologue_pack.json`. It is district
`the_concourse` and `arc: true`. Its terminal flags feed four endings
(`endings.json` reads `review_final_silence` / `_defiance` / `_bargain` /
`_testimony` / `_flagged` at three separate sites).

| ladder session | random | cautious | reckless | greedy |
|---|---|---|---|---|
| `prologue_continuity_review` | 40/40 | 40/40 | 40/40 | 40/40 |
| `review_second_session` (d10) | 40/40 | 40/40 | 40/40 | 40/40 |
| `review_third_session` (d20) | 31/40 | 40/40 | 40/40 | 40/40 |
| `review_final_session` (d30) | 19/40 | **40/40** | **40/40** | **40/40** |

**The mechanism A3 was going to invent is built, shipped, and completing
40/40 in every deliberate strategy.** The `weight: 500000` forced-event pattern
is proven; there is nothing to prototype about it.

### 0.3 So what is actually wrong

Two things, and neither is what the item says.

1. **121 of the 125 are interchangeable.** A survey ping on day 4 reads exactly
   like a survey ping on day 51: 50 are repeatable (`max_fires: 0`), 37 have no
   preconditions at all, and the ~45 `steward_*_ping` volume storylets are
   mechanically identical to each other. The player cannot tell escalation from
   wallpaper because there is no escalation to tell.
2. **The one chain that *does* escalate stops at day 30**, against deliberate
   runs of 54-62 days. F6's window measured that median; the review ladder was
   written against the older 30-day figure. The back half of every deliberate
   run -- 24 to 32 days, roughly *half the game* -- has no scheduled Steward
   presence at all, only the wallpaper.

**A3 should therefore add continuity and consequence to presence that already
exists, not add more presence.** Writing "six more Steward events" would make
the diagnosed problem measurably worse.

---

## 1. Q1 -- What triggers a Steward move?

**Answer: a fixed cadence decides *when*; an accumulating file decides *how
bad*. Not Heat.**

### 1.1 Heat is measured dead for half the game

Heat is the obvious trigger -- 40 events gate on it and
`selector.effective_weight` already scales every `steward`-tagged event by
`1 + Heat/40`. It does not work. n=40 per strategy, over every day of every run:

| strategy | mean Heat | peak (median) | days >= 15 | >= 25 | >= 45 |
|---|---|---|---|---|---|
| random | 17.89 | 40.5 | 43.0% | 28.9% | 13.6% |
| **cautious** | **0.86** | 12.5 | 1.5% | **0.0%** | 0.0% |
| reckless | 16.05 | 46.0 | 40.8% | 27.3% | 10.6% |
| greedy | 2.73 | 20.0 | 5.6% | 1.7% | 0.1% |

**A 20.9x spread in mean Heat, and exactly one cautious run in 40 ever crossed
Heat 25.** A Heat-gated Steward besieges the reckless player and never once
speaks to the careful one -- and the careful, hollow, unresolved life is what
this game is about. It also means that `1 + Heat/40` multiplier is a flat 1.0
for cautious play, which is a large part of why the Steward reads as wallpaper
there while reading as a siege for reckless.

The cause is in `decay.py`: `K_COOL = 4.0` sheds Heat every clean day. Heat is a
**stock**, and any careful player drains it to zero and holds it there.

### 1.2 The file is Heat's integral, and it separates properly

The fix is to count the *events that raised Heat* rather than reading the
level. That never cools, which is what `ambient.steward_ledger_line` has been
saying in prose since it was written -- *"the file does not forget."*

The deck already has the raw material: **47 events grant
`steward_biometric_dossier` (26) or `steward_civic_dossier` (21)**. They are
booleans, so grants 2..26 are no-ops -- a player who trips the biometric dossier
26 times has done the same thing 26 times and been charged for it once. Two
candidate feeds, measured per 10 days:

| feed | random | cautious | reckless | greedy | **spread** |
|---|---|---|---|---|---|
| dossier flags only | 3.18 | 3.33 | 3.55 | 3.23 | **1.12x** |
| dossier flags **+ any Heat-raising branch** | 7.29 | 4.26 | 6.84 | 5.80 | **1.71x** |

**The first row is the trap, and it is the one a design would reach for.**
Counting only the existing dossier flags produces a 1.12x spread: a tenure
clock wearing an antagonist's coat. It measures how long you lived, not how you
played, so there is nothing to play *against* -- an antagonist you can
anticipate but cannot influence is a calendar. (It is thematically impeccable
and mechanically inert, which is exactly the failure mode `decay.py`'s own
`W_TENURE` comment describes and already covers.)

The second row is the shipped feed: a 1.71x spread that still guarantees every
strategy reaches the low tiers.

### 1.3 The tiers, cut on the measured distribution

| cut | tier | random | cautious | reckless | greedy |
|---|---|---|---|---|---|
| 0 | Open | 40 | 40 | 40 | 40 |
| 8 | Under Review | 40 | 40 | 40 | 40 |
| 18 | Flagged | 25 | 39 | 40 | 38 |
| 26 | **Scheduled** | 16 | **21** | **34** | 33 |
| 40 | Closed | 5 | 1 | 19 | 16 |

Two criteria, both met: every strategy reaches every tier *sometimes* (a tier no
careful run can ever see is authored content nobody reads), and the middle of
the ladder is where careful and reckless visibly diverge -- tier 3 is 53% for
cautious against 85% for reckless. An earlier cut at 32/50 was rejected on this
same table: it put cautious at 7/40 and **0/40**.

### 1.4 On A2 / F4

**Ship independently; do not couple to Fame or Social_Capital.** F4's whole
premise is that those two stats are decorative (S5: Fame is read by 12
preconditions and zero engine sites; Social_Capital by 3) and that F4 will
re-price them. Coupling A3's cadence to a stat a later item is going to change
out from under it would make F4 a two-item balance change, which §2 of the
handoff exists to prevent.

`steward_file` is deliberately a **new counter on `Character`**, not a stat: it
is not in `STAT_SPEC`, so it cannot be written by content `deltas`, cannot be
clamped, and cannot leak into `effective_weight`. That is the same reasoning
`Event.arc` was made a field rather than a tag.

**But flag the overlap for F4 explicitly:** the file is the first counter in
this deck that a player might want to *spend against* (bribe the auditor, buy a
clean quarter). If F4 gives Social_Capital a spend, the natural sink is a
Steward filing. A3 should not build that; F4 should know it is there.

---

## 2. Q2 -- Where does the player see it coming?

**Answer: reuse two existing surfaces, add one hidden-until-relevant panel. No
new UI concept.**

1. **The morning line -- `engine/ambient.py`.** `steward_ledger_line()` already
   prints one dated Steward citation every morning in both front ends, and
   `morning_report()` already ranks 1-2 ambient pressure lines by urgency.
   `steward.filing_notice()` is written to sit beside them in the same register
   ("STEWARD NOTICE: your file is reviewed in 3 days. Status: Flagged."). This
   is A3's literal ask -- *"one line the player sees coming"* -- and it costs
   zero new UI.
2. **The countdown, in the left sidebar.** `web/index.html:119` and `:125`
   already carry `#clocks-panel` and `#threads-panel`, both `class="hidden"`
   until they have content. A `#steward-panel` following that exact pattern --
   invisible until the file opens, then showing tier and days-to-filing -- is
   the established idiom, not a new surface. It is the fourth stacked panel in
   that column, which is the real cost and is noted for A4 below.
3. **The terminal.** `ui/terminal.py`'s `render_ambient` already takes the
   ledger line; the notice rides the same call.

### On the A4 overlap the handoff asked about

**No conflict, one shared constraint.** A4 puts Mara/Vint/Kael portraits and a
"what they want from you right now" line in the **right** sidebar, which is
already a tabbed Network / Gear panel (`index.html:189-196`) whose Network tab
lists exactly those contacts with their Ebbinghaus retention -- so A4 has a
natural home that needs no new column. A3's panel goes in the **left** column
with Exit Chain / Deadlines / Threads. Different columns, different cast, no
overlap in content or code.

The shared constraint is vertical space in the left column, which would go to
four stacked panels. Check it at 900px height before adding a fifth thing.
**A3 does not want a district-shelf-like home** -- the Steward already has
`the_concourse` (47 of its 125 events), and giving it a second spatial home
would compete with the map A1 just finished.

---

## 3. Q3 -- Storylet, forced event, or passive state change?

**Answer: a forced event, using the pattern the deck already proves --
`weight: 500000`, `max_fires: 1`, day-gated, flag-chained -- with the file's
tier selecting *which* filing fires.**

Not a normal storylet: §0's founding A1 measurement (`amb_the_choosing` losing
2271 of 2290 draws at a 0.789% median weight share) is the standing proof that
a scheduled beat cannot be left to compete. Not a passive notification either:
S1 is "one verb, never varied", and a text pop-up that the player cannot answer
adds zero verbs.

The shape, mirroring the review ladder exactly:

```
day 0   prologue_continuity_review     (exists)
day 10  review_second_session          (exists)
day 20  review_third_session           (exists)
day 30  review_final_session           (exists)
day 31+ filing every N days            <- A3's content, tier-selected
```

`FILING_ONSET = 31` so filings begin **after** the review ladder rather than
colliding with it, and the handover is itself the escalation: four courteous
interviews a fortnight apart, and then the interviews stop and the filings
start. Combined, a 62-day deliberate run gets **8-9 scheduled Steward moves**,
which averages to A3's requested weekly cadence without a single collision.

---

## 4. Q4 -- Does this touch balance?

**Yes, three separate ways, and this is why the item ships disabled.**

1. **A forced filing consumes an action slot.** Pool composition is the
   documented non-monotonic lever (`grey-utopia-balance-levers`); A1 Phase 3
   moved reckless terminal 27.7% -> 19.6% purely by changing what the day was
   spent on.
2. **A filing that applies consequence on its own schedule is a new,
   unreviewed input to `sim_bot`'s strategies** -- the exact thing §4 of the
   handoff asked to be flagged rather than discovered late.
3. **The filings' *content* is danger**, and A1 Phase 3b measured that the
   danger composition of what a day gets spent on moves reckless terminal by
   8-15 points. A tier-4 filing is by construction the harshest content in the
   deck aimed at the runs already closest to a terminal ending.

**`pargate` is mandatory before this is enabled**, and it cannot be run
meaningfully today because the filings do not exist yet -- gating an empty
mechanism measures nothing. That is the STOP.

---

## 5. What a weekly cadence costs

`tests/steward_audit.py --cadence 7`, n=40. `control` computes the same filing
days and reserves nothing, so the two rows differ **only** by the reserved slot
-- the A1 Phase 2 discipline, because skipping a slot removes a `select_event`
call and reshuffles every subsequent draw.

| strategy | mode | med days | filings | slots kept | reserved | never fired |
|---|---|---|---|---|---|---|
| random | control | 30 | 1.3 | 94.9 | 0.0 | 105 |
| random | live | 30 | 1.5 | 97.0 | 1.5 | 99 |
| cautious | control | 62 | 4.8 | 180.1 | 0.0 | 191 |
| cautious | live | 60 | 4.8 | 176.2 | 4.8 | 191 |
| reckless | control | 54 | 4.1 | 162.1 | 0.0 | 106 |
| reckless | live | 60 | 5.0 | 171.2 | 5.0 | 104 |
| greedy | control | 59 | 4.8 | 176.8 | 0.0 | 135 |
| greedy | live | 55 | 4.0 | 160.3 | 4.0 | 145 |

**The cost is affordable: ~1 slot per filing, 4-5 filings, against 160-180
slots in a deliberate run -- about 2.7%.** Every deck-wide coverage delta in
that table (-6 to +10) is inside the noise band §5 of the handoff put at ~15
events, and the reckless row moving the *wrong* way (control 54 days / 4.1
filings vs live 60 / 5.0) is a plain demonstration of it: reserving slots
cannot lengthen a run, so that pair is stream shuffle, not effect.

**One honest limitation.** `random`'s median run is 30 days against
`FILING_ONSET = 31`, so it sees 1.3-1.5 filings and this content is nearly
invisible to it. That is acceptable on the board's own twice-used argument --
`random` is the chaos baseline nobody plays, which is why `INSTITUTIONAL_CAP`
was split and why F6 was closed unbuilt -- but it means **`coverage_audit`,
which plays `random`, will systematically under-report the filings' reach.**
Quote `steward_audit` or `--union` for this content, not the coverage gate.

---

## 6. What was built, and what deliberately was not

**Built** (all inert while `STEWARD_CADENCE is None`):

- `engine/steward.py` -- the file (`FILE_SOURCES`, `note_resolution`,
  `file_weight`, `TIERS`, `tier_for` / `tier_of` / `next_tier`) and the
  schedule (`STEWARD_CADENCE`, `FILING_ONSET`, `is_filing_day`,
  `next_filing_day`, `days_until_filing`, `filing_notice`).
- `Character.steward_file`, with `to_json` / `from_dict` round-tripping and a
  pre-A3 save loading as an empty file.
- One hook in `resolver.resolve_choice`, last in the function so it sees the
  fully-applied branch. It consumes no RNG and gates nothing.
- `tests/steward_audit.py` -- `--presence`, `--trigger`, `--cadence N`, the
  three measurements above.
- 14 unit tests (94 -> 108).

**Deliberately not built** -- this is the "wiring it live" the window stops
before:

- No filing storylets. No `data/events/steward_filings_pack.json`.
- No day-loop integration in `main.py`, `server.py` or `sim_bot.py`.
- No UI. No `#steward-panel`, no `filing_notice()` call site.
- No `pargate` run, because there is nothing enabled to gate.

**One thing was decided and is worth not re-litigating.** The counter counts
*events*, not points -- a branch adding 30 Heat and one adding 2 are both one
line. Pricing by magnitude rebuilds Heat with extra steps, including Heat's
fatal property that a large enough cooldown makes it vanish.

---

## 7. Phase 2, if the board takes it

1. Author `steward_filings_pack.json`: one filing per tier (5), each
   `weight: 500000`, `max_fires: 0`, gated on `day >= FILING_ONSET` plus the
   tier band. **Before shipping any of them, grep every flag they set against
   `none:` groups** -- A1 Phase 3b's `dgr_works_fronted_crate` lesson, where a
   new flag source silently made a flagship unreachable.
2. Prefer *existing* clocks (`wellness_review`, `arrest_warrant`) over new
   flags, so each filing is a second entrance to machinery that already
   terminates rather than a new orphan. Same reasoning as `district_hazards_pack`.
3. Set `STEWARD_CADENCE = 7`, thread `is_filing_day` through the three day
   loops, add the notice and the panel.
4. **Run `pargate`.** Expect reckless/greedy terminal to move: tier 3-4 filings
   are aimed at exactly the runs closest to a terminal ending. Do not chase a
   sub-point overage (§2).
5. Re-measure `--cadence` against the real content; the §5 table models the
   slot cost only, not the consequence.
