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
| **F2** | Kill the fake dice | **IN FLIGHT** | -- |
| A1 | The Row as a map | Not started | -- |
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

---

## 4. CURRENT TASK -- F2: Kill the fake dice

**Model:** Sonnet 5
**Why this model:** unlike F1 this is not a balance-interpretation problem. The
work is a UI conditional plus a bounded content sweep against a list the linter
can generate and re-check. Nothing here changes pool composition or ending
distributions, so the chaotic-lever reasoning that put F1 on Opus 5 does not
apply. CLAUDE.md routes bulk mechanical passes to Sonnet 5.

**Addresses:** S1 (partially), player-trust

### The problem, restated -- corrected against the code, 2026-07-27

The backlog frames this as two defects. **Only one of them is real**, and it is
worse than described. The F1 window read the code; take this section over
`STEAM_READINESS_BACKLOG.md` §F2 where they disagree.

1. ~~**498 of 1468 choices are truly guaranteed** and still animate a roll.~~
   **Already handled.** These are flagged and their roll is already suppressed.
   The job here is not to regress it.
2. **123 choices sit at `base 1.0` but DO have a failure branch**, and `P_MAX = 0.98`
   (`engine/resolver.py:11`) makes them fail 2% of the time. These are *also*
   flagged guaranteed, so the game hides the dice, presents the choice as certain,
   and then fails one time in fifty with no explanation. This is the whole item.

Why the correction: `web/app.js` is 1382 lines, so the backlog's `913-974` is
stale. The roll reveal lives at **`web/app.js:1007`** and already reads:

```js
if (typeof outcome.roll === "number" && typeof outcome.target === "number" && !outcome.guaranteed) {
```

`engine/resolver.py:198` sets that flag as `guaranteed = 1.0 if p >= P_MAX else 0.0`
-- i.e. it means "p >= 98%", **not** "cannot fail". That single definition is the
root cause of defect 2 and the reason defect 1 is already closed.

### Step 0 -- Regenerate the two lists

Neither count is produced by any committed tool. Before changing anything, emit them
from the live deck -- extend `pipeline/lint_content.py` with a `--report-dice` mode,
or add a small script. Reproduce 498 truly-guaranteed and 123 base-1.0-with-failure,
against 1468 total choices. Report any drift. Keep the list of the 123 ids; Step 2
works through it.

### Step 1 -- Make `guaranteed` mean what it says

Split the concept in two rather than widening the suppression:

- **truly guaranteed** -- no reachable failure branch. Present as a decision: no
  roll, no percentage, no success/fail framing. This is the current behaviour and
  should be preserved.
- **near-certain but fallible** -- `p >= P_MAX` with a live failure branch. This
  must NOT claim certainty. Either show the roll honestly or, better, remove the
  category entirely in Step 2 so it never arises.

The condition belongs in `engine/resolver.py` next to `last_resolution`, not in JS,
so the terminal renderer in `ui/` and `web/app.js:627/634/1007` all agree. Note
`web/app.js:599` and `627-634` also key the journal's success/failure colouring off
the same flag.

### Step 2 -- Decide the 123 by hand

For each of the 123, choose one:
- **commit to the gamble** -- drop `prob.base` below 1.0 so the failure branch is
  honestly reachable, or
- **delete the failure branch** -- if the branch exists only because the schema
  invited one.

This is a content edit across packs; keep `python pipeline/lint_content.py` clean.
Prefer deleting failure branches that merely restate the success text, and prefer
lowering base where the failure branch carries real written consequence.

### Step 3 -- Verify

```bash
python -m unittest discover -s tests     # must pass
python pipeline/lint_content.py          # must stay clean
python tests/coverage_audit.py --parity  # must still reproduce the §6 baseline
python tests/pargate.py                  # only if Step 2 changed any prob.base
```

**On `pargate`:** Step 1 is pure presentation and cannot move balance. Step 2 can --
lowering a `base` changes outcome distributions. If you touch any `prob.base`, the
full gate is required. If you only delete redundant failure branches, note that
`P_MAX` means those branches were firing 2% of the time, so deleting them is also a
(small) balance change. When in doubt, run it.

### Acceptance criteria

| Metric | Baseline | Target |
|---|---|---|
| Choices presented as certain that can still fail | 123 | **0** |
| Truly guaranteed choices rendering a roll | 0 (already suppressed) | **stays 0** |
| `unittest` + `lint_content` | passing | **still passing** |
| `coverage_audit --parity` | reproduces §6 | **still reproduces** |
| `pargate.py` | passing | **still passing** |

**Explicitly out of scope:** the ambient quota (F1 is closed -- do not re-open it
without reading its entry in §3), any weight retuning, F3's economy work, and A1.
If Step 2 turns into a large rebalancing exercise, stop and log it in §5 rather
than expanding this window.

### On completion

Update §3, rewrite §4 for **A1** (the next item in the recommended sequence, and
the one F1's findings most directly inform), append to §5, and end your message to
the user with the model + ready-to-paste prompt for the next window.

---

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
  Folded into F2's spec above -- do not re-derive it.

---

## 6. Recorded baseline

**Corrected 2026-07-27 (F1 window).** The original table came from uncommitted
scratch harnesses. `tests/coverage_audit.py` now exists and is the authority; where
the two disagreed the harness was trusted, per §4 Step 0. Reproduce with:

```bash
python tests/coverage_audit.py --parity      # n=40, seed 0, random play
```

| Metric | Value | Was recorded as |
|---|---|---|
| Events in deck | 483 (24 packs, 388 flags, lint clean) | same |
| Median eligible pool per day | 211 | 207 |
| Unique events seen per run | 103 (21.3% of deck) | ~96 |
| Events never fired **in 40 runs** | 97 (20.1%) | 100 |
| Arc draw-weight share (median) | 24.9% | 22.5% |
| Arc share of actual picks | 27.8% | not measured |
| Ambient share of actual picks | 21.2% | not measured |
| Repeat-pick fraction | 9.8% | 16.8% |
| Median run length | 40 days | 37 |
| Truly guaranteed choices | 498 / 1468 (34%) | same (not re-measured) |
| Base-1.0 choices that still fail 2% via `P_MAX` | 123 | same (not re-measured) |
| Good endings in 20 random runs | 0 | same (not re-measured) |

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
