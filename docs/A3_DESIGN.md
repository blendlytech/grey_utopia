# A3 -- Make the Steward take a turn: design note

**Window:** 2026-07-29, Opus 5, in-session. Phase 1 (design + disabled
mechanism) and Phase 2 (content + wiring) both.
**Status:** **live.** `STEWARD_CADENCE = 7`, five filings authored, threaded
through all five day loops, notice and panel in both front ends, `pargate`
green. Phase 2's write-up is §8; §0-§7 are Phase 1 and are closed.

Reproduce everything below with:

```bash
python tests/steward_audit.py --presence     # is the Steward already on screen?
python tests/steward_audit.py --trigger      # Heat vs the file
python tests/steward_audit.py --cadence 7    # what a weekly filing costs and reaches
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

---

## 8. Phase 2 -- the filings, and what wiring them live actually cost

All five steps above were taken. What follows is what the measurements said,
including the two places they contradicted the plan.

### 8.1 How a scheduled event is expressed in this deck

The one open implementation question Phase 1 left was how a filing reads the
file, since `steward_file` is deliberately not a stat and a `stat` precondition
therefore cannot see it. Both offered options were taken, because they answer
different halves:

- **A new precondition kind, `steward_tier`** (`engine/events.py`), reading
  `steward.tier_of(character)[0]`. It is its own kind rather than a `stat` for
  exactly the reason the counter is not in `STAT_SPEC`: a stat can be written by
  any branch's `deltas`, clamped by `set`, and multiplied into
  `effective_weight`. The file is a *record*, and content is not allowed to edit
  the record. There is a unit test asserting a branch that tries is a no-op.
- **An engine-set flag, `steward_filing_due`**, armed and disarmed by
  `steward.begin_day` at the day boundary. `day` is this deck's only scheduling
  primitive, so "today is a filing day" has to become a flag before content can
  gate on it. It is named in `lint_content.ENGINE_GRANTED_FLAGS`.

The bands are `steward_tier == N`, so **exactly one filing is eligible at a
time** -- the ladder selects rather than stacks. Every branch of every filing
carries `flags_clear: ["steward_filing_due"]`, and that is not decoration: it is
the interlock. Without it, a branch that pushes the file across a tier cut makes
the *next* tier's filing eligible for the same day's next slot, and the player
gets two filings in one day. Both properties are unit-tested.

`begin_day` disarms as well as arms, so a filing that never fired does not carry
into tomorrow. The Steward files on schedule or not at all; otherwise the
countdown in `filing_notice` starts lying.

### 8.2 Five day loops, not three

The handoff said three. There are five, and `--parity` is the tripwire that says
so: `main.py`, `server.py`, `tests/sim_bot.py`, `tests/coverage_audit.py` and
`tests/steward_audit.py`. All five call `steward.begin_day` beside
`districts.clear_placements`, which is the same day-boundary slot for the same
reason -- one call site per loop, so they cannot drift on per-day state.

### 8.3 The content, and the two clocks it hooks

`data/events/steward_filings_pack.json`: five filings, `weight: 500000`,
`max_fires: 0`, 4 choices and 4-5 continuity inserts each.

They are **district-neutral, not shelved on `the_concourse`**. The review ladder
is a place you go to; a filing is a thing that finds you. Shelving five
weight-500000 events would also distort that shelf's composition and its
`district_hint` for no gain -- shelves are non-exclusive, so the filings are
drawable from an unplaced slot either way, and `auto_placement` places at most
slot 0.

Per §7.2, consequence runs through **existing** clocks with existing readers:
`wellness_review` -> `dgr_concourse_review_board` and `arrest_warrant` ->
`dgr_leveld_warrant_served`, both in `district_hazards_pack`. So a filing is a
second entrance to machinery that already terminates rather than a new orphan
flag. There is a unit test asserting every clock a filing starts has an expiry
reader somewhere in the deck.

The §7.1 `none:` grep was done and is now a **permanent test** rather than a
one-time check: `test_no_filing_flag_lands_in_a_none_group_anywhere_in_the_deck`
walks every pack's preconditions, choice `requires` and insert `when` clauses.
Two flags were deliberately *not* set as a result -- `flagged_evasive` gates
`twist_model_citizen` and `debt_collectors_move` gates `dgr_archive_sealed_pull`,
both through `none:` groups.

**Balance discipline in the content itself.** The teeth are clocks, Wealth,
standing and Meaning. No filing carries `dose` (unit-tested), because `dose`
routes straight through the overdose model and tier 3-4 filings are by
construction aimed at the runs already closest to a terminal ending. Mental_Decay
is kept small for the same reason the `INSTITUTIONAL_CAP` note gives.

### 8.4 The notice is a warning, not wallpaper

`filing_notice` shipped in Phase 1 returning a line whenever the cadence was set
-- which at cadence 7 means **every day of every run from day 0**, starting with
"your file is reviewed in 31 days". That is not foresight; it is the exact
undifferentiated-presence defect §0.3 diagnoses in the other 121 Steward events,
authored fresh. `NOTICE_LEAD_DAYS = 3` gates it, so the notice is present on 4
days in 7 rather than 7 in 7, and it appears for the first time on day 28.

Surfaces, per §2: the terminal prints it through `render_ambient` beside the
ledger line; the web front end gets `#steward-panel` in the left column,
hidden until the file has an entry, showing tier and entry count, with the
countdown row appearing only inside the notice window. Note that `state.ambient`
**is not rendered by `web/app.js` at all** -- the morning report and ledger line
have never reached the web player -- so the panel is the web surface for the
notice rather than a supplement to a line that was already there.

### 8.5 Tier 0 fires in about 1% of bot runs, and that is the honest number

The tier cuts were measured on the file's weight at **run end**. The filings read
it at day 31. Those are different distributions, and nothing in Phase 1 checked
the second one. Median file weight at day 31, n=40 per strategy:

| | random | cautious | reckless | greedy |
|---|---|---|---|---|
| file at day 31 | 24.0 | 13.0 | 22.0 | 17.0 |
| runs alive at day 31 | 19/40 | 40/40 | 40/40 | 39/40 |
| **runs below the tier-1 cut (8)** | 0 | **1** | 0 | 0 |

So `steward_filing_open` is eligible for **1 of 138** bot runs. It is not
unreachable -- `--union` confirms no filing is -- but it is close.

It ships anyway, on an argument the board has used twice before about `random`:
**no bot plays against the file.** `sim_bot`'s four strategies score branches on
stat utility and have never heard of `steward_file`; a human who reads the panel
and plays for a cold file has a lever none of them use, and `rest` alone raises
no Heat. Tier 0 is the cold-file outcome, and measuring it with instruments that
cannot see the mechanic under-reports it by construction. Logged in the handoff
§5 all the same, with the two levers a later window could pull (lower the tier-1
cut, or an earlier onset) if it wants the rung livelier.

**What did have to be fixed** was the consequence of that rarity. Three later
choices required `filing_read_the_page`, and its only source was the tier-0
filing -- gating-shaped dead content, F1's S3 failure mode authored fresh. The
flag now has a live source in tiers 0, 1 and 2, and is required only at tier 4.

### 8.6 What a weekly filing actually costs and reaches

`tests/steward_audit.py --cadence 7`, n=10, against `off` (the schedule
disabled) rather than Phase 1's reserved-slot stand-in. The stand-in is retired:
the real filing wins the draw at `weight: 500000` and consumes the slot through
`select_event` like any other storylet, so both arms make the same number of RNG
calls per slot and the A/B needs no special mode.

| strategy | mode | med days | filing days | filings fired | slots | uniq/run | never fired |
|---|---|---|---|---|---|---|---|
| random | off | 28 | 0.0 | 0.0 | 85.9 | 80.8 | 214 |
| random | every 7 | 28 | 1.1 | 1.1 | 90.7 | 84.7 | **210** |
| cautious | off | 56 | 0.0 | 0.0 | 174.6 | 148.8 | 213 |
| cautious | every 7 | 60 | 4.7 | 4.7 | 176.3 | 151.1 | **206** |
| reckless | off | 61 | 0.0 | 0.0 | 168.0 | 148.8 | 141 |
| reckless | every 7 | 71 | 5.0 | 5.0 | 180.0 | 157.5 | **128** |
| greedy | off | 68 | 0.0 | 0.0 | 188.7 | 161.4 | 169 |
| greedy | every 7 | 76 | 6.0 | 6.0 | 198.0 | 169.6 | **149** |

**The filings are coverage-positive for every strategy**, which §5 did not
predict -- it modelled the slot cost and expected a wash. Deliberate runs see
4.7-6.0 filings and every never-fired column moves down.

And the ladder discriminates, which is the whole point of cutting the tiers on a
measured distribution. Filings fired by tier at the moment of filing, n=10:

| tier | random | cautious | reckless | greedy |
|---|---|---|---|---|
| 0 Open | 0 | 0 | 0 | 0 |
| 1 Under Review | 0 | **14** | 1 | 6 |
| 2 Flagged | 3 | **22** | 13 | 17 |
| 3 Scheduled | 7 | 11 | 19 | **28** |
| 4 Closed | 1 | **0** | **17** | 9 |

The careful player's Steward lives at tiers 1-2 and never once closes their
file; the reckless player's lives at 3-4. Same schedule, same five events,
different antagonist -- which is what §1.2 chose the file feed for.

### 8.7 The coverage gate went red, and the red was real

`--assert` came back at **starved 76.8 against a cap of 76**. An 0.8 overage on
a metric whose per-seed spread is 39 events looks exactly like the noise §2 says
not to chase, and the control run the handoff demands appeared to confirm it.
Mean of 5 seed bases, n=40, `random`:

| | starved | outcompeted | never fired |
|---|---|---|---|
| pre-A3 baseline (498 events) | 66.2 | 35.0 | 101.2 |
| filings in deck, schedule **off** (503) | **71.2** | **35.0** | 106.2 |
| filings live, first cut | 76.8 | 34.6 | 111.4 |
| **filings live, shipped** | **73.6** | **35.8** | **109.4** |

Row 2 is the cleanest control this instrument has ever produced: five
unreachable events cost **exactly five** starved and move outcompeted **not at
all**. On that reading `starved` is an absolute count against a growing deck, it
goes red on content addition by arithmetic, and the cap should be re-based to
the control plus the headroom it already carried -- 81. **That was done, and
then reverted**, because row 4 says the diagnosis was wrong.

Row 4 is the same build after §8.5's `filing_read_the_page` defect was fixed --
on its own merits, as a reachability bug, before its effect on the gate was
known. Three later choices were gated behind a flag whose only source fires in
~1% of runs. Making them live moved starved 76.8 -> **73.6, under the unchanged
cap**. So there was nothing to re-base: the gate was reporting a real content
defect, in the pack that had just been added, and it caught it. `MAX_STARVED`
stays at 76 and `MAX_OUTCOMPETED` at 42 (35.8 is not an improvement to tighten
onto).

**The honest lesson is not the one the control suggested.** "Absolute count
against a growing deck" is still true and will trip a future window that adds a
pack -- headroom is now 2.4 -- but it was not what happened here, and re-basing
on it would have banked a real defect as permitted drift. Logged in the handoff
§5 with the two fixes available when it does bite.

`--union` is the reachability check and it is clean: **64 of 503 (12.7%)
unreachable however you play**, against a recorded 61 of 498 (12.2%), and
`steward_filings_pack` does not appear in the union-unreachable table at all.

### 8.8 `pargate`: green, first run, nothing chased

§4 predicted reckless and greedy terminal would move, since tier 3-4 filings are
aimed at the runs already closest to a terminal ending. They moved, and stayed
inside their bands. 4000 playouts, 13.7m:

| strategy | good | terminal | avg days | recorded (Phase 3c / SHIP) |
|---|---|---|---|---|
| random | 0.6% | 71.9% | 41.3 | 0.7 / 65.5 / 39.6 |
| cautious | 17.6% | 12.6% | 63.0 | -- / 17.8 / -- |
| **reckless** | 30.2% | **34.2%** | 59.8 | 30.9-33.3, band 25-35 |
| **greedy** | 39.2% | **15.4%** | 58.7 | 41.1 / 16.7, band 12-25, cap 45 |

`TERMINAL_institutionalized`: random 22.8% (cap 26.0), cautious 7.5%, reckless
15.6%, greedy 13.9% (cap 22.0). All pass.

Two things to watch rather than act on. **Reckless terminal 34.2% sits 0.8
under the top of its band** -- the filings did push it, as predicted, and there
is now very little room above it; a future window adding danger should expect to
have to give some back. And **cautious now reaches exactly 5 distinct endings,
which is `MIN_CAUTIOUS_ENDINGS` exactly** -- the assertion passes with zero
margin, and cautious's table is 52.7% long grey, so the next thing that trims
its tail trips it.
