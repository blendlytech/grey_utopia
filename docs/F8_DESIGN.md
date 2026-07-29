# F8 -- Open `kael_impressed` and the single-source flags behind it

**Window:** 2026-07-29. **Model:** Opus 5, in-session.
**Predecessor:** `F7_DESIGN.md` §5, which measured Kael's cautious reinforcement
count at 2.1/run and *invariant across all three of its levers*, and handed the
cause forward as a sized item rather than a mystery.

**Verdict: shipped, and the gate F7 could not meet is met.** Kael's accumulation
ratio clears 1.0 in all three deliberate strategies. Three branch edits, one new
choice, **zero new events and zero new flags**.

---

## 1. Step 0 -- the baseline reproduced to the digit

`cast_audit.py --retention` before anything was changed: Vint 0.44 / 0.36 / 0.32,
Kael **2.48 / 1.32 / 0.84**, Mara spread **37.52**, Mara 0.28 / 0.30 / 0.32.
Every figure matches F7's shipped table exactly. `--union` measured **63** of 503
unreachable (12.5%), 10 of them `npc_arcs_pack` -- one better than the 64 §6
records, a drift small enough to be a re-measurement rather than a change, and
noted rather than built on.

No re-derivation of presence, coverage or the retention curve. Nine windows have
closed those.

---

## 2. The diagnosis was right and one level too shallow

The handoff's statement -- *`kael_impressed` has one source, and cautious play
declines it 33 times in 40* -- is true. But it describes the symptom of a wider
fact, and the wider fact is what determines whether any fix can work.

The unit of the problem is the **branch**, not the event. Every choice in the
deck whose success branch is warm toward Kael (names him, or moves his bar up),
scored against how often each strategy actually picks it:

| branch | p | rel Kael | random | cautious | reckless | greedy | locked behind |
|---|---|---|---|---|---|---|---|
| `amb_clean_1_the_name/ask_kael_first` | 1.0 | +3 | 1 | **34** | 26 | 30 | an ambition |
| `volume_npc_kael_syndicate_check_in/stay_humble` | 1.0 | +2 | 5 | **33** | 0 | 1 | -- |
| `twist_kael_exit_appraisal/buy_the_exclusivity` | 1.0 | +5 | 2 | **13** | 0 | 4 | a flag + 800 Wealth |
| `volume_npc_kael_syndicate_check_in/impress_kael` | 0.55 | +10 | 7 | **0** | 28 | 32 | -- |
| *…and 40 further warm branches* | 0.4-0.75 | | | **all 0** | | | |

**In a 503-event deck, cautious play picks exactly three branches that are warm
toward Kael at all, and the only unlocked one is the branch whose own prose says
nothing happened** -- *"Kael shrugs, unbothered either way, and moves on to the
next name on his list. Nothing gained, nothing risked."*

The cause is a class fact, not an event fact. **Every warm branch of Kael's
content is a gamble.** The four exceptions at `base: 1.0` are the
nothing-happened branch above, one that is itself behind `kael_impressed`, one
locked to an ambition, and one needing a flag plus 800 Wealth. And `cautious` is
*defined* in `sim_bot.pick_choice_by_strategy` as maximising
`branch_score(failure or success)` -- it minimises worst case. `impress_kael`'s
failure scores **-6.8** against `stay_humble`'s **+1.6**, an 8.4-point gap that
no state can close.

So Kael is not gated behind a flag. **He is gated behind risk appetite**, and a
careful player is locked out of one of three starting contacts by construction.
F2 made this deck's dice honest; the unlooked-for cost was that the only door to
a character became a coin flip.

That reframing is what picks the fix: **give Kael's ledger a route that costs
instead of risks.** It is his own characterisation -- you cannot bluff a broker,
you can pay one -- and it is his own line from the prologue: *"At least you can
read a ledger."*

### 2.1 Two traps the measurement caught

- **`prologue_auditor_descent/door_kael` looks perfect and is dead.** It fires
  40/40 in all three deliberate strategies and its prose *is* `kael_impressed`
  ("You slide it back and double it. The pause that follows is the most respect
  the Row has ever paid you"). All three deliberate strategies pick `door_mara`
  **40/40**; `door_kael` is 0/40.
- **The three "40/40/40" candidates are all origin- or ambition-locked.**
  `ot_aud_1`/`ot_aud_2`/`ot_aud_3` and the prologue descents read as universal in
  the audit *only because the deliberate bots are deterministic and all four land
  on `origin_auditor`*. For a human they are 1-of-4. This is the board's own rule
  inverted: a number that doesn't move across strategies isn't a system -- and a
  number that is 40/40/40 across strategies can still be locked content.

### 2.2 What cautious would pick *behind* the gate, computed before opening it

Opening a gate is worthless if the branches behind it are cold. Cautious's rule
is nearly state-independent, so this is computable off the deck: of the 15 events
`kael_impressed` gates, cautious's forced pick is **warm in 10** (`+2` to `+10`
on his bar, including `arc_kael_the_audit/bring_it_to_him` at +10), cold in 3,
neutral in 2. The gate was worth opening before it was opened.

---

## 3. What shipped -- three doors, none of them a gamble

**No new events. No new flags.** The deck is still 503 events / 398 flags, which
is why `starved` barely moved.

1. **`volume_npc_kael_syndicate_check_in` gains a fourth choice,
   `show_him_the_book`** -- the primary, and the only universal one (its event
   gates on `Fame >= 10` and nothing else). `base: 1.0` with no failure branch,
   so it is honest under F2. It costs **300 Wealth** and grants `kael_impressed`.
   Priced off measurement, not taste: Wealth at the moment this event resolves is
   median 600 / p10 **0** for cautious, and 76% of cautious resolutions clear 300
   against 61% at 500 and 39% at 800.
   `requires: {all: [Wealth >= 300], none: [kael_impressed]}` -- the event is
   `max_fires: 0` on a 5-day cooldown, so without the `none:` guard a cautious run
   would re-buy the flag every five days. Verified: **9 picks, 9 first grants, 0
   re-buys.**
2. **`twist_kael_exit_appraisal/buy_the_exclusivity` also sets it.** Already
   `base: 1.0`, already requires 800 Wealth, already the fiction of paying Kael's
   number without arguing. Cautious 13/40.
3. **`amb_clean_1_the_name/ask_kael_first` also sets it.** Cautious 34 / reckless
   26 / greedy 30 -- the widest of the three, and ambition-locked, so it is a
   third road rather than the main one.

Both second entrances carry a prose clause so the flag is earned on screen
rather than in the data -- F7's lesson run forward. Neither changes bot branch
scoring: `kael_impressed` has no `FLAG_UTILITY` entry, so adding it to a branch
is scoring-neutral and the two entrances cannot have perturbed the balance gate
by re-ranking their own events.

The new choice's score was set deliberately against the two it competes with:
**3.36**, above `stay_humble`'s 1.6 so cautious takes it, below `impress_kael`'s
success at 5.35 so **reckless keeps its gamble** and its distribution is left
alone. Measured: reckless picks the paid door **0** times; greedy splits, 12.

---

## 4. Result

### The flag

| | random | cautious | reckless | greedy |
|---|---|---|---|---|
| runs reaching `kael_impressed` | 9/40 (22%) | **37/40 (92%)** | 33/40 (82%) | 37/40 (92%) |
| median day granted | 11 | 24 | 22 | 20 |
| via `impress_kael` | 4 | **0** | 15 | 6 |
| via `show_him_the_book` | 5 | **9** | 0 | 12 |
| via `buy_the_exclusivity` | 0 | **8** | 0 | 1 |
| via `ask_kael_first` | 0 | **20** | 18 | 18 |

Cautious reaches it by three different doors, so it is not single-threaded any
more -- which was the item.

### The content behind it

All ten `"relationship"` storylets went from **0/40 in cautious to 11-21/40
each**, and the two-tier cascade opened with them: `arc_kael_unpriced_line`
0 -> 20, `arc_kael_the_audit` 0 -> 21, `twist_kael_asset_listing` 0 -> 25,
`cx_kael_the_umbrella` 0 -> 20, and at tier 2 `arc_kael_new_owner` 0 -> 8.
**Three branch edits opened 16 events.**

### The gate

| contact | strategy | reinf/run | ratio (was) | verdict |
|---|---|---|---|---|
| **Kael** | cautious | 2.1 -> **5.5** | 2.48 -> **0.92** | **grows** |
| | reckless | 4.7 -> **5.5** | 1.32 -> **0.93** | **grows** |
| | greedy | 6.2 -> **7.5** | 0.84 -> **0.62** | **grows** |
| | random | 1.1 -> 1.5 | 1.94 -> 2.00 | cannot accumulate |
| **Vint** | cautious | 10.1 -> 10.2 | 0.44 -> **0.43** | grows |
| | reckless | 12.6 -> 12.6 | 0.36 -> **0.34** | grows |
| | greedy | 13.2 -> 13.0 | 0.32 -> **0.31** | grows |
| **Mara** | cautious | 12.7 -> 12.5 | 0.28 -> 0.28 | grows |
| | reckless | 12.2 -> 11.8 | 0.30 -> 0.33 | grows |
| | greedy | 11.2 -> 10.8 | 0.32 -> 0.34 | grows |

**The number F7 could not move, moved.** Kael's cautious reinforcement count was
2.1 under all three of F7's levers -- 1.9, 1.9, 2.1, 2.1, 2.1 -- because strength
levers move the ratio's denominator and only content moves the gap in the
numerator. It is now **5.5**, and the 27.2-day gap is **10.3**.

### 4.1 What the player actually sees -- and the honest limit of this window

Median Kael satisfaction at day D, F7's shipped figures in brackets:

| strategy | d5 | d10 | d20 | d30 | d40 | final | S final | %days<30 | %days<20 |
|---|---|---|---|---|---|---|---|---|---|
| cautious | 28.0 | 19.6 | 9.6 | **5.7** | **4.8** | **6.6** [1.7] | **26.5** | 90.9% [91.5] | **80.5%** [82.8] |
| reckless | 28.0 | 19.6 | 11.0 | **10.4** | **8.8** | **9.7** [6.5] | 22.5 | 90.3% [90.7] | **70.5%** [73.3] |
| greedy | 28.0 | 19.6 | 13.2 | 8.8 | **11.8** | **11.8** [7.7] | 28.0 | 85.6% [86.0] | **61.5%** [67.1] |

**Kael's final satisfaction roughly quadrupled for a cautious player (1.7 -> 6.6)
and his memory strength nearly doubled (S final 26.5), but he still spends 80% of
a cautious run under the alienation line, and that is not a failure of the fix --
it is its arithmetic.** The d5 and d10 columns are *identical across all four
strategies* (28.0, 19.6), because that is the untouched decay curve from a
starting S of 14. Divergence begins at d20, which is exactly the median day the
flag is granted (24 cautious, 22 reckless, 20 greedy). The bond can now climb --
that is what a ratio under 1.0 means, and it is the criterion this item was set --
but it only starts climbing at the run's midpoint, against a curve that has
already taken it to 9.6.

Stated plainly so the next window does not have to rediscover it: **F8 made
Kael's bond accumulate; it did not make it arrive early.** Moving the level
rather than the slope means moving the *entrance* earlier than day 20, and the
three doors that exist are gated at `Fame >= 10`, `day >= 10` + an ambition, and
`day >= 9` + a flag + 800 Wealth. That is a separate lever from the one this
window pulled.

---

## 5. `arc_mara_the_door` -- ruled out with a number, not absorbed

A4 §7 records it at 0/160 as the sole source of four flags gating four more
events. The acceptance criterion allowed addressing it *or* ruling it out with a
number. Walking the chain link by link, n=40 per strategy:

| link | random | cautious | reckless | greedy |
|---|---|---|---|---|
| `res_truth_reckoning` | 1 | 0 | 0 | 0 |
| `res_informer_recruitment` | 5 | **14** | 0 | 0 |
| `res_shepherd_contract` | **1** | **0** | **0** | **0** |
| `twist_mara_unwatched` | 0 | 0 | 0 | 0 |
| `arc_mara_the_door` | **0** | **0** | **0** | **0** |
| its four children | 0 | 0 | 0 | 0 |

**It is not a Mara problem and not a `kael_impressed` problem.** The chain is
five links long and dies at link 2, four links upstream of the flag F8 exists to
open. `res_informer_recruitment` reaches cautious 14/40, but its only branch that
grants `shepherd_offer` is `consider_the_post`, whose downside scores **-12.4**
against `decline_commendation`'s **+1.0** -- so no deliberate strategy ever takes
it, `res_shepherd_contract` fires **1 time in 160 runs**, and that single run
picked `accept_curatorship`, one of the two branches of three that do *not* set
`mara_unwatched`.

It is the same defect class F8 just fixed -- **a thread whose only entrance is a
branch cautious is defined to refuse** -- on a different head, in a different
pack, four links deep. Fixing it means opening `shepherd_offer`, which is
`resistance_pack`'s problem and its own window. Logged to §5 of the handoff.

---

## 6. Predictions, scored

The handoff recorded two; both are scoreable and one is wrong.

1. **"Unlocking 10-17 dead events will move `outcompeted` up and may move
   `starved` down." -- backwards on both counts.** Measured: outcompeted
   **35.6 -> 33.6** (down) and starved **73.0 -> 73.4** (up). The mechanism is
   worth keeping: the events unlocked are `the_chalk_market` *shelf* content, and
   a shelf draw is a pool of ~12, not ~220. Content moved onto a shelf does not
   join the deck-wide competition it would have joined from the neutral pool, so
   unlocking it converts starvation into *firings* rather than into losses. The
   pair moved the way a healthy change moves and the caption predicted the way an
   unhealthy one would.
2. **"Opening the flag cascades two tiers, so the coverage delta will be larger
   than the number of events you edit." -- correct, and by a factor of five.**
   Three branches edited, 16 events opened across two tiers.

My own pre-measurement prediction, from the static branch scores: *cautious takes
the paid door, reckless does not, greedy splits.* **Right in direction, wrong in
magnitude for cautious** -- the paid door carried only 9 of cautious's 37 grants,
because `ask_kael_first` reaches it earlier in 20 of them. The primary entrance
turned out to be the backstop.

---

## 7. Acceptance criteria against what shipped

| criterion | result |
|---|---|
| `kael_impressed` reachable in cautious in the clear majority of runs | **MET** -- 0/40 -> **37/40 (92%)**, by three separate doors |
| its ten relationship storylets firing in cautious at all | **MET** -- 10/10 reached, 11-21/40 each, from 0 |
| Kael ratio < 1.0 in the three deliberate strategies | **MET** -- **0.92 / 0.93 / 0.62** from 2.48 / 1.32 / 0.84 |
| Vint not regressing below 0.44 / 0.36 / 0.32 | **MET** -- **0.43 / 0.34 / 0.31**, marginally better |
| Mara's spread near 37.5 | **PARTIAL** -- **34.80** against 37.52. See below. |
| `arc_mara_the_door`'s 0/160 addressed or ruled out with a number | **MET** -- ruled out, §5 |
| all standing gates green | **NOT MET** -- `pargate` red, reckless terminal **36.0%** against a 25-35% band. Every other gate green, two improved. §8.1-8.3. |

**Shipped with one gate red, as an explicit decision rather than an oversight.**
The band overage is 1.1 points, attributed to this change by a matched control,
and the only lever that recovers it (`ask_kael_first`) is 20 of cautious's 37
grants -- so recovering the band means giving back the criterion the window
exists to meet. Put to the user with the control numbers and the four options;
the call was to ship and document. **F9 inherits reckless terminal with negative
headroom and is told so in §4 of the handoff.**

**On Mara.** Her ratios are unchanged (0.28 / 0.33 / 0.34 against 0.28 / 0.30 /
0.32) and her ceiling rose (51.34 -> 51.90); the spread narrowed because her
*floor* rose 13.83 -> 17.11. She is not flattened -- nothing pushed her down, the
worst way to play her simply got slightly less bad, which is what a deck with
more reachable relationship content does to every bond's floor. Reported as
partial rather than met because the number moved 7%, and this window is not
allowed to explain away its own gate.

---

## 8. Gates

- `unittest` -- **124 pass**.
- `lint_content` -- **clean**; 26 packs, **503 events, 398 flags**, 332 on 7
  shelves. Unchanged, because nothing new was written.
- `coverage_audit --assert` -- **GREEN**. starved **73.4** <= 76 (was 73.0),
  outcompeted **33.6** <= 42 (was 35.6), mean never-fired **107.0** (was 108.6).
  Not tightened: `starved` rose, and the successor window wants the headroom.
- `coverage_audit --parity` -- **3/3 seeds identical**.
- `coverage_audit --union` -- **58 of 503 unreachable (11.5%)**, from 63 (12.5%).
  Cautious's own never-fired fell 192 -> 174, starved 179 -> 168. The
  union-unreachable residual is 18 `legacy_pack` (by design), 16 `betrayal_pack`,
  10 `npc_arcs_pack`, 5 `ambitions_pack` (mutual exclusivity, working as
  intended), 5 `reckoning_pack`, 4 elsewhere.

### 8.1 `pargate` -- RED by 0.2 points, and not chased

**`VIOLATION: Reckless terminal rate 35.2% outside 25-35% band.`** 4000
playouts, 13.0m. Every other assertion passed.

| strategy | avg days | good | terminal | band |
|---|---|---|---|---|
| random | 35.8 | 0.5% | 71.3% | -- |
| cautious | 62.2 | 14.7% | 13.9% | -- |
| **reckless** | 60.1 | 26.9% | **35.2%** | **25-35 ❌** |
| greedy | 58.9 | 41.5% | 13.0% | 12-25, `GOOD_CAP` 45 |

**The overage is 0.2 points on a band F7 shipped at 34.2%, having flagged in its
own handoff that reckless terminal "sits 0.8 under the top of its band."** F8
consumed that 0.8 and 0.2 more. The mechanism is not mysterious and is the item
working as designed: reckless's `kael_impressed` rate went from ~70% to 82%, and
the content behind that flag includes `kael_transferred_debt`,
`kael_late_on_payment` and `kael_the_insurance` -- debt machinery that terminates.

**It was not tuned, deliberately.** The board's §2 says not to chase sub-point
overages, and records a previous session burning 25 iterations on an overage of
exactly this size. The available levers all cost the item: the entrance reckless
gains is `ask_kael_first`, which is also **20 of cautious's 37 grants** -- pulling
it to recover 1.0 point of reckless terminal would trade away the criterion this
window exists to meet.

### 8.2 The noise hypothesis was tested and is false

`pargate` is deterministic (seeds 0..999), so re-running cannot change the
figure. The reasonable first hypothesis was that a 0.2-point crossing is inside
the estimate's noise -- at n=1000 a 35% rate carries a standard error of ~1.5
points, making 0.2 a **0.13σ** crossing. So the deck was **not** tuned; instead
the sample was doubled, which is a measurement rather than a tuning iteration.

**It came back worse, and that settles it against the convenient answer:**

| sample | reckless terminal | vs band top |
|---|---|---|
| n=1000 (the standing gate) | 35.2% | +0.2 |
| **n=2000 (8000 playouts, 25.5m)** | **36.0%** | **+1.0** |

Doubling the data moved the point estimate *away* from the band, not toward it.
**The 0.2 was not noise, and this is not a sub-point overage** -- at the better
estimate it is a full point, which is the scale F1 treated as a real regression
(3.2pt) rather than the scale §2 says not to chase. **Reported as a real
regression, not explained away.**

The remaining question the numbers could not answer on their own is *attribution*
-- F7's recorded 34.2% is an n=1000 figure, and comparing it to an n=2000 figure
is not like-for-like. §8.3 measures the counterfactual instead of assuming it.

### 8.3 The control: is this F8's regression, or the band's?

The three edited packs were reverted to their committed state and `pargate
--iterations 2000` re-run on the identical sample, so the deck is the only
changed variable. This is the control the board requires before a red gate is
attributed to a change -- *"a control that explains a red gate is not one that
exonerates the change."*

| n=2000, 8000 playouts | reckless good | reckless terminal | verdict |
|---|---|---|---|
| **pre-F8 deck (control)** | 28.4% | **34.9%** | **All balance gates passed** |
| **F8 deck** | 27.4% | **36.0%** | **VIOLATION** (band 25-35) |

**The control does not exonerate the change. F8 owns +1.1 points of reckless
terminal, and that is what takes the band from passing to failing.** The
pre-F8 deck passes every assertion at the identical sample; the hypothesis that
the band was already failing and F8 merely revealed it is false.

Greedy moved the same direction and stayed inside: terminal 13.8 -> 14.4, good
39.6 -> 40.2. Reckless good fell 28.4 -> 27.4 as its terminal rose, which is the
signature of runs ending earlier rather than of the ending mix being re-weighted.

**Attribution to the mechanism, stated as a hypothesis and not as a measurement:**
reckless's `kael_impressed` rate went 28/40 -> 33/40, and the content behind the
flag includes the debt machinery (`kael_transferred_debt`, `kael_late_on_payment`,
`kael_the_insurance`) plus `twist_kael_asset_listing`, whose reckless-preferred
branch `go_unlisted` carries a **-10.0** downside at `base: 0.4`. That was not
isolated to a single event, because doing so costs a 22-minute gate run per
candidate and the board's §2 exists to stop exactly that search.

**What was deliberately not done.** The band constant was **not** widened, and the
obvious content lever was **not** pulled: the entrance reckless gains is
`ask_kael_first`, which is simultaneously **20 of cautious's 37 grants**. Removing
it to recover ~1 point of reckless terminal would drop cautious to ~17/40 (43%),
failing the "clear majority" criterion and almost certainly pushing Kael's
cautious ratio back above 1.0 -- i.e. trading away the entire item to satisfy a
one-point band. **That trade is the user's to make, not this window's**, and it is
handed forward explicitly rather than taken silently in either direction.

**The structural finding, which matters more than the point itself.** Reckless
terminal has now sat within one point of its ceiling across two consecutive
content windows. It is no longer a guard with room in it -- **it is the binding
constraint on all further content work**, and the next window that adds anything
syndicate- or dose-adjacent will trip it too. Either the band is re-argued
against what the deck now is, or content windows start budgeting against it
explicitly. That decision is not this window's to make unilaterally, and is
handed forward rather than resolved by quietly widening a constant.

---

## 9. Discovered, not fixed here

- **`clock_mara_dark_expired` has zero sources in the deck**, not one as A4 §7
  records. It is synthesised by `engine/decay.py:317` when the `mara_dark` clock
  set by `twist_mara_unwatched` expires. A4's table counted it as a
  content-granted flag; it is engine-granted, which is why grepping the packs for
  its source returns nothing. The rest of §7's table is accurate.
- **`echo_brother_known` is the same shape as `kael_impressed` was, one tier
  down.** One source, `res_why_you_fix/turn_the_question`, at `base: 0.5` -- a
  gamble again -- gating three events. Echo's ratios are 7.36 / -- / 3.20 / 3.75
  and cautious never has him in the network at all. He is the next instance of
  this exact defect.
- **The `ot_aud_*` trio remains the largest unwired Kael surface**, unchanged
  from F7 §9: 40/40 in every deliberate strategy, names Kael, touches nothing,
  and `ot_aud_1`/`ot_aud_2` are `gate_critical`. It was not needed as a fallback.
  Note for whoever does reach for it: **`ot_aud_3_successor` is not tagged
  `gate_critical`** and fires 37/33/34, so it is the cheap one of the three.
- **`data/cast.json` still duplicates `engine.stats.create_starter_fixer`.**
  Logged by F7 §9 and still live.
