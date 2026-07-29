# F9 -- Recalibrate the relationship gates against the bonds that now exist

**Window:** 2026-07-29. **Model:** Opus 5, in-session.
**Predecessor:** `F8_DESIGN.md`, which quadrupled Kael's bar and then wrote down
in §4.1 the honest limit that made this window necessary -- his gates sit at 45
and 55 against a bond whose measured ceiling is 11.8.

**Verdict: shipped, with `pargate` red for a second consecutive window.**
Thirteen of sixteen gates were unreachable and none is now: **DEAD 8 -> 0**, LIVE
**3 -> 14** of 17. One engine capability, thirteen gate re-pricings, one new gate,
**zero new events, zero new flags and zero prose.** Every standing gate green --
`--assert` improved and its cap tightened -- except reckless terminal, which
**F9 pushed +0.5 to 35.7%** on a band F8 had already left 0.2 over. §6.1.

---

## 1. Step 0 -- the spec was wrong again, and this time about its own subject

The baseline reproduced exactly before anything was touched: Vint 0.43 / 0.34 /
0.31, Kael **0.92 / 0.93 / 0.62**, Mara 0.28 / 0.33 / 0.34, Mara spread 34.80.
Every figure matches F8's shipped table.

Then `tests/cast_audit.py`'s `CAST` dict was extended from four bonds to nine, as
the handoff instructed, and the first measurement made the item's headline number
the sixth consecutive spec to be wrong:

| the board recorded | measured |
|---|---|
| "six events read a satisfaction threshold" | **16** -- 2 event preconditions, 14 choice `requires` |
| four bonds in the audit | **nine** in the deck |
| 10 gates on 5 contacts "never measured" | correct, and **all 10 dead or unusable** |

**The audit could not see 62% of the gates it was being used to judge.** Ten of
the sixteen are on Auntie Six, Brann, Denny, Dex and the Ferryman -- bonds
`cast_audit` did not track, so nine consecutive windows reported on the cast
while three fifths of the cast's gating was invisible to the instrument.

`--retention` on all nine, and the second half of Step 0 was already decisive:

| bond | born at | S | half-life | reinf/run (deliberate) | ratio | median final |
|---|---|---|---|---|---|---|
| Auntie Six | 50 @ d8 | 6.0 | 4.2d | 0.3 - 0.5 | 5.0 - 6.7 | 0.2 - 1.3 |
| Brann | 40 @ d10 | 6.0 | 4.2d | 0.6 - 2.2 | 1.5 - 3.1 | 5.2 - 6.9 |
| Denny | 40 @ d8 | 4.0 | 2.8d | 0.6 - 1.0 | 6.6 - 12.3 | 0.1 - 3.3 |
| Dex | 45 @ d8 | 5.0 | 3.5d | 0.7 - 0.8 | 8.4 - 9.1 | 0.1 - 0.3 |
| Ferryman | 30 @ d14 | 5.0 | 3.5d | 1.3 - 1.8 | 3.1 - 3.4 | 0.0 - 1.5 |

All five **CANNOT ACCUMULATE** in every strategy, and their spread across the four
bots is **0.19 to 3.18 points** -- by the board's own rule, not systems a player
can play.

### 1.1 The instrument this window had to build first

`--retention`'s end-of-run column cannot answer the question the acceptance
criterion asks, and the handoff said so: *a gate is not reachable because its
bond's ceiling clears it -- it is reachable if the bond clears it on the day the
event can fire.* So `cast_audit.py` gained a fourth mode, **`--gates`**, which
reads every gate out of the JSON (both syntaxes, all three sites) and scores each
one against the runs:

- `open days` -- days per run the gate stood open, i.e. **the window the gating
  event has to win a draw inside**
- `ever open` -- runs where it opened at all
- `fired` / `fired w/ gate` -- runs where the gating event fired, and of those,
  runs where it fired while the gate was open. The last column is the criterion.

That last pair is what separated "mispriced by a few points" from "impossible",
and nothing already in the repo could produce it.

---

## 2. The diagnosis: the gates are not too high, they are too late

`--gates` before any change, 16 content gates:

| verdict | count |
|---|---|
| LIVE | **3** -- all three Mara's |
| OPEN BUT NEVER USED | 5 |
| **DEAD -- the bond never clears the threshold in any strategy** | **8** |

**Three of sixteen gates worked, and every one of the three was on the same
contact.** Mara starts at 75/S12 and is the only bond in the deck whose
satisfaction survives long enough for a threshold to mean anything.

The 35/60 pairs are not off by a tunable margin. On the day their own event fires
(n=600 runs pooled, median day **56-58**):

| finale | fires | bond's satisfaction, median (max) | against |
|---|---|---|---|
| `cx_auntie_passing_the_board` | 10/600 | **0.6** (3.6) | 35 and 60 |
| `cx_brann_the_last_season` | 10/600 | **10.9** (38.4) | 35 and 60 |
| `cx_denny_the_new_shop` | 14/600 | **0.3** (23.6) | 35 and 60 |
| `cx_dex_the_replacement` | 20/600 | **0.4** (22.5) | 35 and 60 |
| `cx_ferry_stand_the_door` | 34/600 | **2.7** (24.6) | 35 and 60 |
| `reck_syndicate_deadline` | 26/600 | **10.7** (32.3) | 45 |

**The mechanism is one sentence: each of these bonds is created on day 8-14 and
its gate is read on day 50+, with a half-life of 2.8 to 4.2 days.** The gate is
not a few points high -- it is read roughly **fourteen half-lives** after the
bond is born. No threshold above about 2 is reachable there, and a threshold of 2
is not a gate.

Kael's is the same shape with a different number: **his measured peak across 160
runs is 40.0 -- exactly his starting satisfaction.** He never rises above where
he begins in any strategy, so 45 and 55 could not pass even in principle.

### 2.1 What the deck was actually trying to ask

Read the prose and the intent is unambiguous. `cx_ferry_stand_the_door` offers
*"Stand the door yourself, exactly by her price book"* behind Ferryman >= 60, and
*"Go to her. Don't perform anything"* behind >= 35, against an ungated *"Stay
away. The seam isn't your business to tend."* That is a three-tier ladder asking
**"did you keep this person up?"**

Current satisfaction cannot express that. It is the Ebbinghaus value; it decays
every single day and it only ever means *"are you warm with them right now"*. The
question the content is asking is about a whole run's history, and the deck
already stores exactly that number.

---

## 3. What shipped

### 3.1 One engine capability: `field` on a relationship condition

`engine/events.py` -- a relationship condition may now name which of the bond's
quantities it reads. `satisfaction` is the default, so **every pre-F9 gate is
byte-identical in behaviour**, and `reinforcements` is the monotonic count of warm
contacts that `Relationship` has kept since F7.

**`strength` is deliberately not offered, and its absence is enforced by the
linter.** It looks like the same thing and is not: F7 made `Character.strain`
raise S as well, so a bond you keep crossing builds strength too, and an S gate
would read *being hated as being loved*. That is the exact trap
`Relationship.reinforcements` was added to escape -- A4's accumulation gate
inferred reinforcements from S increments and F7's own lever then broke the
inference. **The same mistake was available in the deck, one layer down, and this
window declined it.**

`pipeline/lint_content.py` gained `_relationship_gate_sites()` and
`VALID_REL_FIELDS`. The engine falls back to `satisfaction` for an unrecognised
field rather than crashing play; the linter makes reaching the deck with one a
hard error, because a silent fallback would recreate precisely the defect F9
exists to remove -- a gate reading the decaying value when its author meant the
monotonic one. It also rejects a non-integer `reinforcements` value. Both
rejection paths were verified.

Note also that the linter's main loop only ever walked event `preconditions`. Ten
of the sixteen gates live in choice `requires`, which is part of why the board
recorded the count as six.

### 3.2 Thirteen gates re-pointed, priced off the measurement

**The ten `cast_expansion_pack` gates** become a uniform two-tier ladder on
reinforcements -- tier 1 at **>= 1**, tier 2 at **>= 2** -- set against the
measured distribution at each finale's own fire day (`reinf` p10/p50/p90 was
1/1/3 Auntie, 1/3/4 Brann, 0/1/1 Denny, 1/1/2 Dex, 0/2/3 Ferryman). Uniform
rather than per-contact on purpose: those distributions rest on 10-34 fires each,
and fitting five separate pairs to samples that small is how the deck acquired
five separate dead pairs in the first place.

**Kael's two.** `reck_syndicate_deadline/beg_kael_intercede` 45 -> **reinforcements
>= 4**, the measured median at its fire day. `arc_mara_the_door/break_her_out` 55
-> **reinforcements >= 6**; it is one of three alternatives in an `any` group, and
it is re-pointed rather than deleted so the deck runs one mechanism instead of
two -- but see §5, the event fires **0/600** and F8 already proved that dies four
links upstream. The gate is now reachable by the bond it reads; the event is not
reachable at all, and that is `shepherd_offer`'s window, not this one.

### 3.3 Vint reads a gate, and the measurement chose the number

`cx_vint_archive_night` gains an event precondition of **Vint >= 20**... and then
did not, because the instrument overruled it. The event is the right site -- it
fires 130/160, it is in the same pack that runs this pattern for five other
contacts, and its body is literally about being let in ("the one file he says
he'll never sell ... he'll be unbearable about having let you see it").

**20 is the alienation line the UI and `check_endings` already use, so it was the
number this window wanted.** At 20, `cx_vint_archive_night` fell 25/40 -> **2/40**
in `random` and took `vint_weather_heard`'s three dependents with it:
`coverage_audit --assert` came back **starved 76.6, RED**.

The threshold was then chosen off the only window that matters -- **days on or
after the event's own `day >= 12` gate on which Vint clears the threshold**, since
days before that cannot be spent:

| threshold | random | cautious | reckless | greedy |
|---|---|---|---|---|
| >= 15 | **6** (38/40 runs) | 26 | 38 | 38 |
| >= 20 | 0 (17/40) | 9 | 30 | 32 |
| >= 25 | 0 (8/40) | 2 | 16 | 19 |

At **15** the gate keeps 38/40 of random's runs while still spreading window width
**6 against 38** -- 6.3x, live in all four strategies. At 20 it locks 23/40 of
random's runs out entirely, which is where the starvation came from.

**Shipped at 15. The pretty constant lost to the measurement**, which is the whole
protocol of this board working in the direction it is less fun to work in.

Vint is also the one contact for whom current satisfaction is the *right* field:
F7 made his bar the most responsive of the three, and his is the only satisfaction
threshold in the deck that measurement shows is both reachable and
strategy-discriminating.

---

## 4. Result

### The gates

| | before | after |
|---|---|---|
| content gates | 16 | **17** (Vint's is new) |
| LIVE | 3 | **14** |
| OPEN BUT NEVER USED | 5 | **3** |
| **DEAD** | **8** | **0** |

The three survivors are `arc_mara_the_door/break_her_out`,
`res_shepherd_contract/negotiate_for_mara` and
`cx_auntie_passing_the_board/find_an_apprentice`. **All three gates are now
reachable by the bond they read**, measured on the shipped build:

| gate | opens in | its event fires |
|---|---|---|
| `arc_mara_the_door/break_her_out` (Kael reinf >= 6) | **17 / 20 / 26** of 40 deliberate | **0/160** |
| `res_shepherd_contract/negotiate_for_mara` (Mara >= 30) | **40/40** every strategy, 50-58 days per run | **0/160** |
| `cx_auntie_passing_the_board/find_an_apprentice` (Auntie reinf >= 2) | 1 / 4 / 1 of 40 | 4/160 |

The first two events fire zero times for reasons documented four links upstream
(§5) and the third fires four times (§7). **The criterion is about the gate; event
reachability is a separate, logged defect** -- and for the first two it is F8's
already-ruled-out `shepherd_offer` chain, which the handoff explicitly told this
window not to enter.

**Auntie's tier 2 is the honest edge of this window.** It read LIVE on the Vint-20
build and UNUSED on the shipped Vint-15 one, on an event that fires **3-5 times in
160 runs** -- the verdict for that one gate is decided by one or two runs and
should not be read as a state of the world. It is the same n=10-34 fragility §7
records, showing up inside this window's own headline number.

Vint's new gate at the shipped threshold of 15:

| strategy | open days | ever open | fired | fired w/ gate |
|---|---|---|---|---|
| random | 18 | 40/40 | 9/40 | 9/40 |
| cautious | 40 | 40/40 | 25/40 | 23/40 |
| reckless | 54 | 40/40 | 29/40 | 28/40 |
| greedy | 46 | 40/40 | 26/40 | 26/40 |

Against the ungated deck's 25/37/34/34 fires, the gate costs `random` 25 -> 9 and
`cautious` 37 -> 25 while leaving reckless and greedy near where they were -- which
is the shape wanted: it reads the bar, and the strategies that keep Vint warm
barely notice.

### Two contacts became playable as a side effect

Opening the tier-1 and tier-2 choices means their `rel_deltas` (+4, +5) can land
for the first time. Spread of median final satisfaction across strategies:

| bond | before | after |
|---|---|---|
| **Brann** | 1.69 | **8.34** |
| **Auntie Six** | 1.04 | **5.04** |
| Ferryman | 1.49 | 1.82 |
| Dex | 0.19 | 0.46 |
| Denny | 3.18 | 1.86 |
| Mara | 34.80 | **35.72** (F7's 37.52 partially recovered) |
| Vint | 16.64 | 16.60 |
| Kael | 6.69 | **7.48** |

Brann and Auntie Six move from "does not respond to play at all" to a 5-8 point
spread. Denny and Dex remain flat, and that is honest rather than fixed: their
ladders reinforce them 0.7-1.1 times a run, so tier 2 is reachable but rare.
**Not claimed as solved** -- see §7.

### The three ratios, and why the n=40 reading is not the verdict

At **n=40**, the sample F8's recorded figures are in, Kael's cautious ratio read
**1.14 against F8's 0.92** -- a crossing back above 1.0, which would have failed
this window's own criterion. The board's rule (and
`grey-utopia-borderline-gates`) is that a borderline reading gets **a larger
sample and a matched control at the same n**, not a re-run. Both arms, identical
seeds, three times the sample, the three data packs reverted for the control so
the deck is the only changed variable:

| bond | strategy | **control (pre-F9)** | **F9** |
|---|---|---|---|
| Mara | cautious / reckless / greedy | 0.30 / 0.31 / 0.33 | **0.29 / 0.31 / 0.33** |
| Vint | cautious / reckless / greedy | 0.45 / 0.34 / 0.33 | **0.45 / 0.35 / 0.33** |
| **Kael** | **cautious** | **0.89** | **0.89** |
| Kael | reckless / greedy | 0.98 / 0.63 | **0.92 / 0.64** |

**Kael's cautious ratio is 0.89 in both arms -- identical.** The n=40 difference
was estimator noise on a statistic whose n=40 spread is about +/-0.2, not a
regression: Kael's cautious reinforcement gap is ~11 days against a ~58-day run,
so the count divides by a small number and the ratio inherits all of its
variance. Reckless improved 0.98 -> 0.92; nothing regressed.

**Reported both ways rather than only the flattering one.** The consequence for
the next window is a real finding: **the ratio figures this board has been
quoting since F7 are n=40 and carry about +/-0.2 of noise on Kael**, so a future
window must not read a 0.1-0.2 move on them as signal. Logged to §5 of the
handoff.

Vint's `random` ratio crosses 0.90 -> 1.01. That is the new gate biting the
strategy with the coldest Vint, which is what a gate is for, and `random` is not
one of the three the criterion names.

---

## 5. Acceptance criteria against what shipped

| criterion | result |
|---|---|
| every satisfaction gate reachable by the bond it reads, or retired with the number | **MET** -- **DEAD 8 -> 0**. All 17 gates now clear their own bond; the 3 unused are event-reachability defects logged upstream, with numbers |
| **Vint reads at least one gate** | **MET** -- `cx_vint_archive_night` on Vint >= 15, LIVE in all four strategies, 18 vs 54 days of window |
| ratios do not regress (Mara 0.28/0.33/0.34, Vint 0.43/0.34/0.31, Kael 0.92/0.93/0.62) | **MET on the n=120 matched control** -- Kael cautious 0.89 in both arms. **At n=40 it reads 1.14 and that is stated, not buried.** §4 |
| all standing gates green, and `pargate` brought back inside the band or plainly stated | **NOT MET -- stated.** `pargate` red, reckless terminal **35.7%** at n=1000 against F8's 35.2% on the same seeds. Every other assertion passed. §6.1 |

---

## 6. Gates

- `unittest` -- **125 pass** (was 124; one added for the `field` semantics,
  including that 90 days of decay erases satisfaction and leaves the count alone,
  and that `strain` does not increment it).
- `lint_content` -- **clean**; 26 packs, **503 events, 398 flags**. Unchanged,
  because nothing was written.
- `coverage_audit --assert` -- **GREEN**. starved **72.4** (was 73.4),
  outcompeted **36.4** (was 33.6), mean never-fired 108.8 (was 107.0).
  **`MAX_STARVED` tightened 76 -> 75** in the same window, per the board's rule
  that an improved number tightens its guard; `MAX_OUTCOMPETED` left at 42
  because that half got worse.
  Starvation *falling* on a change that adds a gate is the interesting part:
  opening ten previously-invisible choices gave four `cast_expansion_pack` flags
  live sources for the first time. Content moved from "never eligible" into
  "offered and lost a draw" -- the same trade F8 §6 documented, in the healthy
  direction.
- `coverage_audit --parity` -- **3/3 seeds identical**.
- `coverage_audit --union` -- **55 of 503 unreachable (10.9%)**, from 58 (11.5%).
  `cast_expansion_pack` leaves the union-unreachable list entirely. Residual: 18
  `legacy_pack` (by design), 16 `betrayal_pack`, 10 `npc_arcs_pack`, 4
  `ambitions_pack` (mutual exclusivity, intended), 4 `reckoning_pack`, 3
  elsewhere.

### 6.1 `pargate` -- inherited red, still red, and F9 owns +0.5 of it

**`VIOLATION: Reckless terminal rate 35.7% outside 25-35% band.`** 4000 playouts,
21.4m. **Every other assertion passed.**

| strategy | avg days | good | terminal | band |
|---|---|---|---|---|
| random | 35.8 | 0.5% | 71.7% | -- |
| cautious | 62.2 | 14.6% | 13.7% | -- |
| **reckless** | 59.8 | 28.0% | **35.7%** | **25-35 ❌** |
| greedy | 59.0 | 40.4% | 13.8% | 12-25, `GOOD_CAP` 45 |

**The attribution needs no new control, and that is worth being explicit about.**
`pargate` is deterministic on seeds 0..999, `git diff` confirmed the three data
packs were at their committed state when this window opened, and Step 0 reproduced
F8's ratios to the digit -- so **the deck I inherited is F8's shipped deck, whose
recorded n=1000 figure is 35.2%.** That figure *is* the matched control for this
run: same seeds, same instrument, one changed variable.

**So F9 owns +0.5 points, on a band that was already 0.2 over before this window
started.** Red before, red after, now by 0.7.

**Two things this is not.** It is not a transition from passing to failing -- F8
already spent that, and the question a control exists to answer ("did my change
break this gate?") was answered before F9 began. And it is **not** comparable to
F8's 36.0%: that is an n=2000 figure and quoting it against 35.7% at n=1000 is
exactly the error §5 of the handoff warns about. §6.2 measures the like-for-like
number instead of asserting it.

**The mechanism, as a hypothesis rather than a measurement.** The one gate F9
opened on terminal-adjacent content is `reck_syndicate_deadline/beg_kael_intercede`,
which went from never-available (Kael >= 45, unreachable) to open in 27-33 of 40
deliberate runs. Its *success* buys five days against Kael's own standing and its
*failure* sets `syndicate_final_notice` -- so the branch is a survival route whose
downside feeds the terminal machinery, and it is genuinely unclear from first
principles which direction it should push. Isolating it costs a 21-minute gate run
per candidate, and §2 of the board exists to stop that search.

**Not tuned, and the reason is the same as F8's.** The levers available all cost
the item: the only way to take `beg_kael_intercede` back off the table is to
restore a Kael threshold nothing can reach, which is the defect this window exists
to remove. **That trade is the user's to make, not this window's**, and it is
handed forward rather than taken silently.

### 6.2 The like-for-like n=2000 figure -- and the delta is stable

F8 measured its own deck at **36.0%** on 2000 seeds, so one run of the F9 deck at
the same sample gives a directly comparable number without needing a second
control arm. 8000 playouts, 33.1m:

| n=2000, 8000 playouts | reckless good | reckless terminal | verdict |
|---|---|---|---|
| pre-F8 deck (F8's control) | 28.4% | 34.9% | all balance gates passed |
| F8 deck (inherited) | 27.4% | **36.0%** | VIOLATION |
| **F9 deck** | **27.4%** | **36.5%** | **VIOLATION** (band 25-35) |

**F9 owns +0.5 points, and it is +0.5 at both sample sizes** -- 35.2 -> 35.7 at
n=1000 and 36.0 -> 36.5 at n=2000. That stability is the useful part: F8's
equivalent number *grew* from 0.2 to 1.0 when its sample doubled, which is why F8
could not call its own overage noise. F9's does not move, so **+0.5 is the effect,
not an artefact of the sample** -- and by the same token there is no larger figure
hiding behind it.

Reckless `good` is **27.4% in both the F8 and F9 decks** -- unchanged to the
decimal. So F9 did not re-weight reckless's ending mix; it moved runs from
non-terminal endings into terminal ones, or ended them sooner. That is consistent
with the `beg_kael_intercede` hypothesis in §6.1 and inconsistent with a broad
difficulty shift.

**Total inherited-plus-F9 overage against the band top: 1.5 points.**

### 6.3 The structural finding stands, and is now two windows old

F8 §8.3 recorded that reckless terminal "has now sat within one point of its
ceiling across two consecutive content windows" and that it is **the binding
constraint on all further content work**. F9 makes it three, and F9 is not even a
content window -- it added no events, no flags and no prose. **A pure gating
change moved it half a point.** That is the clearest evidence yet for F8's own
conclusion: either the band is re-argued against what the deck now is, or every
window from here budgets against it explicitly. F9 does not resolve that
unilaterally either.

---

## 7. Discovered, not fixed here

- **The `cast_expansion_pack` finales fire 10-34 times in 600 runs.** Every one
  of them is `weight` 5-6, `max_fires: 1`, gated at `day >= 50` behind a
  four-rung flag ladder. F9 fixed their *gates*; the *events* are close to
  unreachable on their own terms, and that is a weight/day-ladder question rather
  than a gating one. It is also why every per-finale number in this document
  rests on n=10-34 and is quoted as a distribution rather than a point.
- **Auntie Six's ladder never reinforces her more than twice.** Her `S final` is
  **6.0 in all four strategies** -- the value she is created with, meaning zero
  reinforcements in the median run. Her tier-2 gate is reachable (1/4/1 of 40
  deliberate) but thin, and the fix is content on the ladder, not a lower
  threshold: a threshold below 2 would collapse her two tiers into one.
- **`Denny` and `Dex` still have a strategy spread under 0.5 points.** Their
  gates are live; their bars are not yet systems. Same cause as above.
- **The endings file carries a second, uncensused layer of 13 satisfaction
  thresholds** in `epilogues[].when`, now reported by `--gates`. Two are in the
  same dead shape the content gates were: `TERMINAL_syndicate_ledger`'s Kael >= 45
  fires **0-1 of 40** in every strategy, and `NEUTRAL_stewards_shepherd`'s Vint
  >= 40 fires 0/0/5/4. They select the last paragraph a player ever reads. Not
  touched: an ending epilogue is a different risk surface from a choice gate, and
  it deserves its own decision rather than a corner of this window.
- **`echo_brother_known` was not absorbed**, as instructed. Echo's ratios remain
  7.21 / -- / 3.08 / 2.89 and cautious never has him in the network at all. A
  static census done while a gate run was in flight says the board's diagnosis is
  one link too deep, though: **`echo_contact`, the flag that puts Echo in the
  network at all and is read by 18 events, has three sources and all three are
  gambles** (`base` 0.55 / 0.70 / 0.50). Cautious is defined to refuse all three,
  which explains the `--` better than `echo_brother_known` does. Handed to F10 as
  its Step 0 rather than assumed.
- **`data/cast.json` still duplicates `engine.stats.create_starter_fixer`.**
  Logged by F7 §9 and F8 §9, still live.
