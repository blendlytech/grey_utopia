# GREY UTOPIA -- Backlog Handoff Board

**Purpose:** this file is the single source of truth for which backlog item is in
flight, what was already done, and what the next window should pick up. It is a
state machine that survives across model windows.

**Companion:** `docs/STEAM_READINESS_BACKLOG.md` holds the diagnosis (S1-S9) and the
full item specs (F1-F5, A1-A5). This file holds *status and handoff*. Read both.

---

## 1. Protocol for every window

Any model picking up work here follows these five steps. No exceptions.

1. **Read** `docs/STEAM_READINESS_BACKLOG.md` (the item spec) and this file
   (status + the CURRENT TASK block below).
2. **Confirm the baseline still holds** by running the item's stated verification
   command *before* changing anything. If the numbers have drifted from what this
   file records, stop and report -- do not build on a stale baseline.
3. **Do the work**, staying inside the item's scope. If you discover an adjacent
   problem, write it into §5 Discovered Work; do not fix it in this window.
4. **Verify** against the item's acceptance criteria. Report actual numbers, not
   "passing". If a gate fails, say so with the output.
5. **Hand off**: update §3 (move the item to COMPLETED with its measured result),
   rewrite §4 CURRENT TASK for the next item, and end your final message to the
   user with a ready-to-paste **model + prompt** for the next window.

**Scope discipline is the whole point of this board.** These items were sequenced
because several of them are balance changes on a deck whose levers are documented
as non-monotonic. Two balance changes in one window cannot be attributed.

---

## 2. Standing constraints

- **Engine code never goes through `pipeline/generate_deck.py`.** That script emits
  storylet JSON only. Engine work is done directly on files. (CLAUDE.md Checkpoint 3.)
- **After any balance-affecting change**, run `python tests/pargate.py` (~9 min).
  `F1`, `F3`, `F4`, `A1`, `A2` are all balance-affecting.
- **Do not chase sub-point gate overages.** A previous session burned 25 iterations
  on a 0.2-point overage. Good enough is good enough; bank the win and move on.
- **Run `python -m unittest discover -s tests` before the balance gate**, always.
- **`python pipeline/lint_content.py` must stay clean** on any content touch.
- **`python tests/coverage_audit.py --assert` must stay green** on anything that
  touches the selector, event preconditions, or the day loop (~25s, n=40, seed 0).
  It guards reachability and draw composition, which `pargate` does not see at all
  -- the gate only scores where runs *end*, not what the player was shown getting
  there. Its thresholds are regression guards on the measured baseline, not
  aspirations; if you improve the numbers, tighten them in the same window.

---

## 3. Status board

| Item | Title | Status | Result |
|---|---|---|---|
| F1 | Per-day ambient quota | **CLOSED -- premise disproved** | Built, measured, shipped disabled. See below. |
| F2 | Kill the fake dice | **CLOSED** | 0/1468 choices now presented as certain that can still fail. See below. |
| **A1** | The Row as a map | **Phase 1 DONE -- premise confirmed** | Mechanism built, measured, shipped disabled. Chain reachability 6/24 -> 23/24 events, 19/40 -> 40/40 runs, with never-fired 103 -> 83 deck-wide. See below. |
| A3 | Make the Steward take a turn | Not started | -- |
| A4 | Put the cast on screen | Not started | -- |
| SHIP | Settings / saves / achievements / content warning / art | Not started | -- |
| F3 | Make money a decision | Not started | -- |
| F4 | Give Fame and Social_Capital a spend | Not started | -- |
| F5 | Signpost the endings in-fiction | Not started | -- |
| A2 | Preparation as an action | Not started | -- |
| A5 | Achievements you already wrote | Folded into SHIP | -- |

Order above is the recommended sequence from `STEAM_READINESS_BACKLOG.md` §6.
F5 and A2 sit late because both are cheaper to build once A1's map exists.

### Completed

**F1 -- Per-day ambient quota** *(2026-07-27, Opus 5)* -- **premise disproved; quota
built and shipped disabled.** Delivered `tests/coverage_audit.py` (the missing
instrument), the `eligible_pool` / `is_ambient` / `ambient_budget_for` mechanism in
`engine/selector.py` threaded through `main.py`, `server.py` and `sim_bot.py`, and 9
unit tests including the required empty-pool fallback guard.

Measured at seed 0, random play; `--ambient-slots` A/Bs the lever. Rows are n=100
except never-fired, which is quoted at its calibrated n=40:

| Metric | No quota | 1 slot/day | 0 slots/day | F1 target |
|---|---|---|---|---|
| Arc draw-share (median) | 25.2% | 25.4% | 30.2% | **> 35%** |
| Arc share of picks | 28.1% | 29.0% | 33.7% | -- |
| Unique events per run | 113 | 92 | 92 | higher |
| Never fired *(n=40)* | 97 | 96 | 174 | **< 70** |
| Median run length | 43 d | 36 d | 38 d | -- |

The quota missed every acceptance criterion and moved two of them backwards, then
cost a balance gate: **reckless terminal rate 21.8%, under sim_bot's 25.0% floor**
(a 3.2pt regression, not a sub-point overage). Two measurements explain why, and
both retire the S2/S3 diagnosis as written:

1. **`ambient`+`micro` is only 20.8% of eligible draw weight**; arc is 24.6% and the
   *unbudgeted middle* -- `job`, `undercity`, `existential`, `steward`, `vice`,
   `family`, `vendor`, 229 events -- is **55.8%**. Suppressed ambient weight
   redistributes ~2.3:1 into that middle, not into arc. Arc draw-share is
   arithmetically capped at ~30.6% even by a total ambient ban.
2. **Unreached content is not losing draws, it is never eligible.** Of the 54
   unreached non-legacy storylets, **50 are gated behind a flag only another
   storylet can grant** (56 of 72 are `day`+`flag` gated). No pool-composition
   lever can reach them.

**Verified final state** (quota disabled): `unittest` 70 passed; `lint_content` clean
(24 packs, 483 events, 388 flags); `coverage_audit --assert` green and reproducing
§6 exactly with 3/3 sim_bot parity; `pargate` **all balance gates passed** in 16.6m --
random 0.5% good / 66.9% terminal / 40.0 avg days, cautious 25.2 / 21.4, reckless
34.3 / **27.7** (back inside the 25-35 band the quota had broken at 21.8), greedy
43.0 / 14.7.

Shipped state: `AMBIENT_SLOTS_PER_DAY = None`. Engine behaviour is byte-identical to
`d3de304` -- the audit reproduces the pre-change baseline exactly and parity vs
sim_bot is 3/3. The mechanism was kept, not reverted, because it is the right shape
for budgeting a *shelf* (A1's districts); the tag set it was aimed at is simply not
where this deck's filler lives.

**F2 -- Kill the fake dice** *(2026-07-27, Sonnet 5)* -- **closed, both sub-defects
confirmed and fixed.** Step 0 reproduced the baseline with zero drift: 498 truly
guaranteed / 123 near-certain-but-fallible / 1468 total, via the new
`python pipeline/lint_content.py --report-dice [--verbose]` mode (`event_pack_files()`
extracted as a shared helper).

Step 1 redefined `guaranteed` in `engine/resolver.py:197-201` from `p >= P_MAX`
(a probability threshold) to `0.0 if was_gamble else 1.0` (`was_gamble =
bool(choice.failure)`, already computed for the desperation-edge streak) --
"cannot fail" instead of "almost never fails." `web/app.js`'s roll-reveal
(`:1007`) and journal colouring (`:599/627/634`) both read this one flag from
`server.py`'s `last_resolution`, so no JS changes were needed; the terminal
renderer (`ui/terminal.py`) never had a post-resolution roll display to begin
with.

Step 2 went through all 123 by hand. Every one turned out to be
`sonnet_5_volume_pack.json` (122) or `sonnet_volume_pack_2.json` (1) -- this
specific defect is entirely contained to two Sonnet-5-authored volume packs, not
present anywhere in the Opus-authored flagship/arc/npc packs. Classification was
mechanical, not judgment-call: **101 had a failure branch whose text was either
byte-identical to the success branch or entirely absent** -- pure schema
boilerplate, no distinct consequence ever written -- so the branch was deleted
outright (including one, `volume_vice_market_loan_shark:take_the_loan`, whose
failure branch had **no text at all** and started a debt clock with no payout --
an authoring bug lint never caught because the "risky choice missing branch
text" check only fires when `0 < base < 1`). **The other 22 had a genuinely
distinct, differently-consequenced failure branch** -- these were committed to as
real gambles: `prob.base` lowered to 0.90 (delta magnitude <= 2), 0.85 (3-5), or
0.80 (>= 6), tiered by the size of the failure branch's stat swing. Three of the
101 deletions (`rel_vint_debug_session` x2, `fam_mara_shared_secret`) were a
notable sub-pattern: identical success/failure text but the failure branch
silently dropped a relationship-milestone flag (`vint_established`,
`mara_established`) -- a chain-progression flag that failed to grant 2% of the
time with zero narrative signal that anything had gone wrong.

Closed the loop against recurrence: `pipeline/lint_content.py`'s `lint()` now
WARNs whenever `base >= P_MAX` coexists with a non-empty failure branch, so this
exact defect re-entering through a future volume-generation batch (Sonnet 5 or
Gemini 3.1 Pro) surfaces on the next `lint_content.py` run instead of requiring
another archaeological audit.

**Verified final state:** `unittest` 70 passed; `lint_content` clean (24 packs,
483 events, 388 flags, 0 warnings including the new check); `--report-dice` now
reports **599 truly guaranteed / 0 near-certain-fallible / 869 genuine gambles**;
`coverage_audit --assert` green (103 never-fired < 105, 24.7% arc share > 23.0%);
`coverage_audit --parity` 3/3. `pargate` required because 22 `prob.base` values
changed -- **all balance gates passed** in 10.3m: random 0.7% good / 65.9%
terminal / 39.7 avg days (was 0.5 / 66.9 / 40.0), cautious 24.3 / 22.2 (was 25.2 /
21.4), reckless 33.4 / 27.1 (was 34.3 / 27.7, inside the 25-35 band), greedy 44.4
/ 16.1 (was 43.0 / 14.7, inside the 12-25 band and just under the 45.0 GOOD_CAP).
All deltas are within this deck's documented non-monotonic noise band; no gate
moved from pass to fail or vice versa.

**Discovered, not fixed here** (see §5): the pre-choice risk-tier badge in
`web/app.js`'s `riskTier()` labels anything `>= 95%` as flat "SAFE" without
consulting the `gamble` field `server.py:230` already computes and sends per
choice -- a real (if now honestly-rare) gamble at e.g. 90% still shows the same
"SAFE" badge as a truly guaranteed choice, pre-choice. `main.py`'s terminal
renderer has the analogous issue one layer deeper: it always prints a live
`{p}%` from `choice_probability()`, so a truly guaranteed choice with no failure
branch still displays "98% success" instead of "guaranteed," because the
percentage is computed straight from the clamped probability with no reference
to whether a failure branch exists at all.

**A1 Phase 1 -- The Row as a map: design + proof-of-concept** *(2026-07-27, Opus 5)*
-- **premise confirmed; mechanism built, measured, and shipped disabled.** Delivered
`docs/A1_DESIGN.md` (all five Step-1 questions answered), the optional `district`
field on `Event`, the `data/districts.json` registry, `on_shelf` /
`district_for_slot` / the `district` filter dimension in `eligible_pool` threaded
through `main.py`, `server.py` and `sim_bot.py`, a lint check for unregistered
district ids, three new `coverage_audit` knobs, and 11 unit tests.

**Step 0 found the recorded baseline stale and the handoff's pack recommendation
wrong**, and both corrections changed what got built:

- §6's table was never updated after F2. Re-measured: median run 34 d (recorded
  40), unique events/run 88 (103), never-fired 103 (97). The two figures F2 *did*
  record -- 103 never-fired, 24.7% arc share -- reproduced exactly, so the baseline
  held; §6 is now corrected.
- §4 recommended migrating `betrayal_pack` first. Splitting "never eligible" from
  "eligible but never picked" shows why that would have failed: **16 of its 30
  events were never eligible in any of 40 runs**, and the 3 broadly-eligible ones
  already fire in 23-39/40. It is a *gating* problem, and F1 already proved shelves
  cannot touch those. `ambitions_pack` is the opposite and is the honest test.

**The case for the prototype, measured before anything was built.**
`amb_the_choosing` -- the `max_fires: 1` fork that hands out all three ambitions,
and therefore the root of 23 downstream storylets -- is gated on `day >= 6` and
nothing else:

| `amb_the_choosing`, n=40 seed 0 | Value |
|---|---|
| Runs where it was eligible | 40/40 |
| Runs where it fired | **19/40** |
| Draws it sat in the pool and lost | **2290** of 4244 |
| Median share of a draw's weight | **0.789%** |

It is not hidden. It is drowned -- and every choice on every downstream link grants
the next thread flag unconditionally, so winning draws is the *only* thing between
the player and 23 more events.

**Result.** One district, `the_archive`, holding the 24 `ambitions_pack` events;
one of the day's three slots placed there. n=40, seed 0, random play:

| the_archive shelf (24 events) | Baseline | 1 slot/day | +all ambient | every 3d | **every 5d** |
|---|---|---|---|---|---|
| Events ever fired | 6/24 | 19/24 | 16/24 | 23/24 | **23/24** |
| Runs where any fired | 19/40 | 40/40 | 27/40 | 40/40 | **40/40** |
| Times picked | 26 | 155 | 61 | 177 | **173** |
| Win rate on eligible draws | 0.8% | **100.0%** | 2.7% | 19.5% | **10.5%** |
| *Deck-wide:* never fired | 103 | 118 | 134 | 93 | **83** |
| *Deck-wide:* median pool | 209 | 207 | **74** | 209 | **208** |
| *Deck-wide:* arc draw-share | 24.7% | 24.4% | 19.3% | 24.4% | **24.5%** |
| *Deck-wide:* ambient picks | 21.3% | 20.2% | **45.7%** | 20.3% | **19.6%** |
| *Deck-wide:* unique/run | 88 | 82 | 69 | 88 | **98** |
| *Deck-wide:* median run | 34 d | 31 d | 26 d | 34 d | **38 d** |

Four findings, two of which overturned the design as drafted:

1. **The mechanism is causal and large.** Same seeds, same deck, same weights;
   only the reservation changed. 6/24 events -> 23/24, 19/40 runs -> 40/40.
2. **Every-day placement is a vending machine.** A 100.0% win rate on eligible
   draws is not a game, and it costs 15 events elsewhere.
3. **`SHELF_INCLUDES_AMBIENT` was drafted On and is wrong.** Mixing all ~88 neutral
   ambient events into each placed draw halves the chain's benefit *and* triples
   the deck-wide damage -- median pool 209 -> 74, ambient 21.3% -> 45.7% of picks,
   never-fired 103 -> 134. Ships Off. The right texture is a district's *own*
   ambient, which does not exist until the volume pack is distributed.
4. **Cadence is the real lever, and at every-5 the deck gets better, not worse.**
   Never-fired **103 -> 83** (~17 of it the chain, the rest from runs lasting 34 ->
   38 days), arc share flat, ambient picks down. **This is the first lever in three
   windows to move never-fired downward at all** -- F1's quota moved it the wrong
   way and F2 was coverage-neutral.

**Shipped state: `PROTOTYPE_DISTRICT = None`** -- the shipped game is byte-identical
to pre-A1. Two independent disqualifiers for shipping it enabled: the every-5
cadence lives in the *audit harness* because it stands in for a player choosing
where to stand (shipping it would mean the engine picking a district on a timer,
which is the measurement rig, not the design); and the +4 median days is a balance
change needing its own `pargate`, which cannot be run against a config that does
not exist yet.

One design decision was reversed mid-build for a footgun rather than a measurement:
`eligible_pool(district=None)` does **not** filter. Exclusive shelves -- district
content invisible from outside -- read better and are what "the Row as a map"
sounds like, but with `PROTOTYPE_DISTRICT = None` shipped they would make all 24
shelved events *silently unreachable*, and the same hazard runs for the length of
the migration. Revisit in Phase 3 when "neutral" means ambient rather than
unmigrated.

**Verified final state:** `unittest` **81 passed** (70 + 11 new); `lint_content`
clean (24 packs, 483 events, 388 flags, 24 events on 1 shelf, 0 warnings);
`coverage_audit --assert` green, reproducing 103 never-fired / 24.7% arc-share
exactly; `--parity` 3/3 vs sim_bot; `pargate` **all balance gates passed** in 9.7m
-- random 0.7% good / 65.9% terminal / 39.7 avg days, cautious 24.3 / 22.2,
reckless 33.4 / 27.1, greedy 44.4 / 16.1. Every figure is **identical** to F2's,
which is the point: with `PROTOTYPE_DISTRICT = None` the district filter is
unreachable, so a moved number would have meant a bug.

---

## 4. CURRENT TASK -- A1 Phase 2: placement as a player choice

**Model:** Opus 5
**Why this model:** Phase 1 confirmed the mechanism and handed Phase 2 a *design*
problem, not a migration one. The measured result was that **cadence -- how often
a player goes somewhere -- is the lever**, not shelf composition, and cadence is
currently faked by a test harness. Turning it into a real mechanic means deciding
what a placement screen is, what the player knows when they choose, and how the
existing 3-slot day loop in three different files becomes a placement loop. That
is the same interpretive weight that put F1 and Phase 1 on Opus 5. It is also
still balance-affecting, and this time genuinely so: the every-5 config moved
median run length 34 -> 38 days.

**Read first:** `docs/A1_DESIGN.md` in full (it answers the five schema/selector/
Heat/travel/phasing questions and records the two design reversals), then §3's A1
entry above for the numbers. **Do not re-derive the proof-of-concept.**

### What Phase 1 left you

Working and shipped, but inert (`PROTOTYPE_DISTRICT = None`):

- `Event.district` (optional, absent = neutral = pre-A1 behaviour), read by
  `load_events`, validated against `data/districts.json` by `lint_content.py`.
- `engine/selector.py`: `on_shelf()`, `district_for_slot()`, and the `district`
  filter dimension in `eligible_pool()` / `select_event()`, threaded through
  `main.py`, `server.py`, `tests/sim_bot.py`.
- `tests/coverage_audit.py`: `--district`, `--district-slots`, `--district-every`,
  `--track-district`, `--shelf-ambient` / `--no-shelf-ambient`.
- 24 events already shelved on `the_archive` (the whole `ambitions_pack`).
- 11 unit tests in `TestDistrictShelves`.

### Step 1 -- Make placement a choice the player makes

The cadence knob is a harness stand-in for a player deciding where to stand. Build
the real thing:

- A morning placement step: before the day's slots resolve, the player assigns
  each of them to a district (or leaves them unassigned). `district_for_slot`
  becomes a read of that assignment rather than a constant.
- **The three day loops must not drift.** §5 already records that `main.py` and
  `server.py` count a "fired" event differently; adding placement state to both is
  exactly the change that turns a harmless inconsistency into a save-compat bug.
  `server.py` also has to persist placement in `save_state`/`load_state`.
- The player needs to know *something* about a district before choosing it, or the
  placement is a blind menu. A one-line hint per district (how long since you were
  there, whether anything is waiting) is probably enough; the Exit Chain panel is
  the existing pattern.

### Step 2 -- Give the shelf texture before adding more chains

Phase 1's measurement was unambiguous that a shelf holding only a day-gated chain
is a vending machine (100.0% win rate on eligible draws), and that diluting it
with *all* neutral ambient is worse than the disease. The fix is a district's own
texture. **Distribute a slice of `sonnet_5_volume_pack` (185 events, 7 unreached
-- the healthiest pack in the deck) onto `the_archive`** and re-measure the win
rate. Target the 10-20% band that every-5 cadence produced, not 100%.

This inverts the migration order §4 previously recommended, and `A1_DESIGN.md` §5
explains why: texture must exist before more chains land on shelves.

### Step 3 -- Only then, the second district

With placement real and one shelf textured, add a second district and migrate
`npc_arcs_pack` (12/17 unreached, competition-shaped). Two districts is the first
configuration where "where do I go today?" is an actual decision, and the first
that can test whether travel needs a cost after all (`A1_DESIGN.md` §4 says no,
on reasoning, not measurement).

### Acceptance criteria for this window

| Metric | Target |
|---|---|
| Placement is a player choice in both `main.py` and `server.py` | built, and persisted across save/load in `server.py` |
| `the_archive` shelf win rate on eligible draws | **10-25%** (Phase 1: 0.8% unplaced, 100% bare-shelf-every-day) |
| Ambitions chain events ever fired | **>= 20/24** at n=40 (Phase 1 baseline 6/24) |
| Deck-wide never-fired | **<= 95** at n=40 seed 0 (Phase 1 baseline 103; every-5 measured 83) |
| `coverage_audit --assert` | passing, **with `MAX_NEVER_FIRED` tightened** if the number improves -- §2 requires it |
| `unittest` + `lint_content` | passing |
| `pargate.py` | passing, **and genuinely exercised** -- unlike Phase 1, placement is live, so this gate is real |

**Explicitly out of scope:** spatial Heat (`A1_DESIGN.md` §3 sequences it to Phase
4, deliberately not in the same window as a selector change), travel cost, F3/F4/A2,
districts 3-8, `betrayal_pack` (measured gating-shaped -- shelves will not help it).

### On completion

Update §3, append findings to §5, correct §6 if the baseline moves, and end with
the model + ready-to-paste prompt for Phase 3.


## 5. Discovered work (append-only)

Adjacent problems found mid-task that were deliberately *not* fixed in that window.
Triage these into the status board when they earn their place.

- *(2026-07-27, audit)* `tests/coverage_audit.py` did not exist; F1's acceptance
  criteria were unverifiable. Folded into F1 as Step 0. **Now built and committed.**

- *(2026-07-27, F1)* **S2 is misdiagnosed and should be rewritten.** "Two of every
  three storylets are filler" is true, but `ambient`+`micro` is not where that
  filler lives -- it is 20.8% of draw weight against the untagged middle's 55.8%
  (`job` 82 events, `undercity` 136, `existential` 121, `steward` 120, `vice` 86,
  `family` 53, `vendor` 41). Any future "surface more arc content" lever must
  target that middle or it is working on a fifth of the problem. Note the tags
  overlap heavily, so this is not 229 disjoint buckets -- a real fix needs a
  filler/arc classification the deck does not currently carry.

- *(2026-07-27, F1)* **S3 is an eligibility problem, not a selection problem.** 50
  of the 54 unreached non-legacy storylets are gated behind a flag only another
  storylet can grant; 56 of 72 unreached are `day`+`flag` gated. They never enter
  the pool at all, so no weighting or budgeting change can reach them. The levers
  that would are: shortening chains, granting first-link flags earlier, or giving
  chains a home that does not compete with the general deck (**this is a direct
  argument for A1's district shelves**). Worth re-checking whether the `day` gates
  are calibrated for the *corrected* median run length of 40 days -- the same
  smell as the open "The Rounding is day-55 gated, median run ends day 58" thread.

- *(2026-07-27, F1)* **Ambient content is load-bearing for run length.** Budgeting
  it down shortened the median random run 43 -> 36 days and cut unique events seen
  per run 113 -> 92, because ambient events are the low-consequence content a run
  coasts on. Anything that trims filler must expect runs to get shorter and harsher,
  and should re-check `sim_bot`'s terminal bands. This is what broke the gate in F1.

- *(2026-07-27, F1)* **`main.py` and `server.py` count a "fired" event
  differently.** `main.py:158` adds an event to `fired_today` when all its choices
  are locked (so it is excluded from the day but never shown), while `server.py`
  tracks those in a local `skip` set inside `advance_event`'s retry loop and only
  adds to `fired_today` on an actual resolve. Harmless today, but the two loops are
  drifting and any future per-day budgeting will inherit the inconsistency.

- *(2026-07-27, F1)* **`guaranteed` is a lie for 123 choices, and F2's spec was
  written without checking the code.** `engine/resolver.py:198` defines the flag as
  `p >= P_MAX` (0.98), not "cannot fail", and `web/app.js:1007` already hides the
  roll for everything so flagged. The 498 truly-guaranteed choices are therefore
  already handled; the 123 fallible ones are actively misrepresented as certain.
  Folded into F2's spec above -- do not re-derive it. **Resolved 2026-07-27 in F2.**

- *(2026-07-27, F2)* **The entire 123-choice defect lived in exactly two packs.**
  All 123 near-certain-but-fallible choices were in `sonnet_5_volume_pack.json`
  (122) or `sonnet_volume_pack_2.json` (1) -- zero in any Opus-authored
  flagship/arc/npc/betrayal/ambitions pack. Reads as a Sonnet-5 volume-generation
  habit (always emit a failure branch even when there is nothing distinct to say
  in it) rather than a spread-out authoring problem. Worth a one-line addition to
  a future volume-generation prompt/checklist if Sonnet 5 or Gemini 3.1 Pro
  writes another volume batch: only write a failure branch when it says
  something the success branch doesn't.

- *(2026-07-27, F2)* **Pre-choice risk display doesn't use the `gamble` field
  that already exists.** `server.py:230` computes and sends `"gamble":
  bool(ch.failure)` per visible choice, but `web/app.js`'s `renderChoices` never
  reads it -- `riskTier()` (`app.js:913`) buckets purely off the numeric `prob`,
  so anything `>= 95%` shows a flat "SAFE" badge whether or not a failure branch
  exists. Post-F2 this is much less severe (the near-certain-but-fallible
  category is gone, and any choice we committed to a real gamble in Step 2 now
  sits at 80-90%, below the 95% "SAFE" cutoff, so the tier label already shifts
  correctly for those). But a future genuine gamble authored at >= 95% would hit
  the same "SAFE"-badge blind spot pre-choice that F2 fixed post-choice. Small,
  not urgent: wire `riskTier`/the badge to `ch.gamble` when someone is next in
  `web/app.js` for other reasons.

- *(2026-07-27, A1 Phase 1)* **Never-fired counts cannot distinguish the two
  failure modes, and the backlog's pack priorities were set from them.** "18/24
  unreached" and "19/30 unreached" look like the same problem and are not:
  `ambitions_pack` is 9/24 ever-eligible (**competition**), `betrayal_pack` is
  14/30 ever-eligible (**gating**). Only the first is reachable by any selector
  lever. `coverage_audit.py` now reports the split via `--track-district` /
  `--chain`; **any future "this pack is unreachable" claim should quote
  ever-eligible alongside ever-fired**, or it cannot be acted on. This is the
  measurement F1's S3 correction implied but did not provide.

- *(2026-07-27, A1 Phase 1)* **The day gates on `ambitions_pack` are calibrated
  for a run length the game no longer has.** The three chains gate their links at
  days 10/16/22/28/34/40/46 and their finales at 46-52, against a **median random
  run of 34 days**. Even with a district shelf firing the chain at 40/40 runs and
  a 10.5% win rate, `amb_clean_6`, `amb_clean_8`, `amb_clean_finale`,
  `amb_second_6`, `amb_second_8`, `amb_second_finale`, `amb_signal_6` and
  `amb_signal_finale` still fired **0 times in 40 runs** -- the day gate, not the
  draw, is what stops them. This is the same open thread as "The Rounding is
  day-55 gated but the median run ends day 58," and it now has a second
  independent instance. **No amount of A1 fixes it**; it wants a separate item
  that re-scales every chain's day gates against the measured median. Worth
  checking `npc_arcs_pack` and `reckoning_pack` for the same shape before Phase 3.

- *(2026-07-27, A1 Phase 1)* **`--chain amb_` is a trap and cost a measurement.**
  The prefix matches the 24 `ambitions_pack` events *and* 42 unrelated
  `amb_*`-named volume ambients, which quietly reported a 66-event "chain" with
  healthy-looking numbers. Caught only because the totals did not match the
  hand-probe. `--track-district` exists because of this and should be preferred;
  the `--chain` prefix mode is kept for un-districted content but is sharp.

- *(2026-07-27, A1 Phase 1)* **`§6`'s baseline table was not updated by the F2
  window** and had drifted on four of nine rows (median run 40 -> 34, unique
  events/run 103 -> 88, never-fired 97 -> 103, median pool 211 -> 209). The two
  numbers F2 *did* record in §3 reproduced exactly, so nothing was built on bad
  data, but the drift went unnoticed for a window. §6 is corrected below.
  Enforcing §1 step 5's "update §3" should extend to §6 whenever the audit moves.

- *(2026-07-27, F2)* **The terminal renderer has a milder, un-fixed version of
  the same defect.** `ui/terminal.py:84-85`'s `render_choices` always prints a
  live `f"{p*100:.0f}% success"` from `choice_probability()`, with no concept of
  `guaranteed` at all (the terminal has no post-resolution roll reveal, so F2's
  acceptance criteria didn't reach it). A truly-guaranteed choice (no failure
  branch) still displays "98% success" instead of "guaranteed" or "100%",
  because the percentage comes straight from the clamped probability with no
  reference to whether a failure branch exists. Cosmetic, terminal-only, and
  out of F2's scope as written -- worth a follow-up if the terminal UI gets
  another pass.

---

## 6. Recorded baseline

**Re-measured 2026-07-27 (A1 Phase 1 window).** The F1 column below was correct
when written; **F2 changed the deck and did not update this table**, so four rows
had drifted for a window (see §5). `tests/coverage_audit.py` is the authority.
Reproduce with:

```bash
python tests/coverage_audit.py --parity      # n=40, seed 0, random play
```

| Metric | Value | F1 recorded | Pre-F1 scratch |
|---|---|---|---|
| Events in deck | 483 (24 packs, 388 flags, lint clean) | same | same |
| Median eligible pool per day | **209** | 211 | 207 |
| Unique events seen per run | **88** (18.1% of deck) | 103 | ~96 |
| Events never fired **in 40 runs** | **103** (21.3%) | 97 | 100 |
| Arc draw-weight share (median) | **24.7%** | 24.9% | 22.5% |
| Arc share of actual picks | **27.7%** | 27.8% | not measured |
| Ambient share of actual picks | **21.3%** | 21.2% | not measured |
| Repeat-pick fraction | **9.1%** | 9.8% | 16.8% |
| Median run length | **34 days** | 40 | 37 |
| Truly guaranteed choices | **599** / 1468 (41%) | 498 | same |
| Base-1.0 choices that still fail 2% via `P_MAX` | **0** | 123 | same |
| Genuine gambles | **869** / 1468 | not measured | not measured |
| Good endings in 20 random runs | 0 | same (not re-measured) | same |

The F1 -> now movement is all F2's doing and is expected: deleting 101 boilerplate
failure branches and lowering 22 `prob.base` values makes runs resolve faster
(median 40 -> 34 days), which mechanically lowers unique-events-per-run and raises
never-fired. The dice rows are F2's own reported result, folded in here so there is
one table rather than two.

Balance gate at this baseline (`python tests/pargate.py`, 4000 playouts, 9.7m,
**all gates passed**): random 0.7% good / 65.9% terminal / 39.7 avg days, cautious
24.3 / 22.2, reckless 33.4 / 27.1, greedy 44.4 / 16.1.

Notes on the corrections:

- **Never-fired is meaningless without its N.** Same deck, same seed base: 209 at
  n=5, 97 at n=40, 69 at n=100. Always quote the run count. `coverage_audit.py`
  refuses to assert the never-fired gate at any N other than its calibrated 40.
- Never-fired at n=40 also swings with the seed base -- 97 (seed 0), 91 (seed 100),
  111 (seed 500). The old 100 was inside that noise; the metric needs a fixed seed
  to be compared across windows, which the harness now provides.
- Arc draw-share (24.9% vs 22.5%) and repeat-pick fraction (9.8% vs 16.8%) sit
  outside seed noise, so the scratch harness must have defined them differently.
  The committed definitions are: arc draw-share = median over draws of
  (arc weight / total pool weight); repeat-pick = mean over runs of
  (picks - distinct picks) / picks.

Per-pack unreached counts print with every audit run.

**Anyone changing these numbers must update this table in the same window**, with
the command that produced the new figures.
