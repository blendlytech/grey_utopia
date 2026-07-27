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

---

## 3. Status board

| Item | Title | Status | Result |
|---|---|---|---|
| **F1** | Per-day ambient quota | **IN FLIGHT** | -- |
| F2 | Kill the fake dice | Not started | -- |
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

*(nothing yet -- append here as items land, newest last, with measured results)*

---

## 4. CURRENT TASK -- F1: Per-day ambient quota

**Model:** Opus 5
**Why this model:** the code change is ~40 lines, but the risk is entirely in
balance interpretation. `grey-utopia-balance-levers` records that pool composition
"collapses bots like scripted slots too" -- F1 changes pool composition directly,
on a lever documented as chaotic and non-monotonic. CLAUDE.md assigns probability
and balance audits to Opus 5.

**Addresses:** S2 (two of three storylets are filler), S3 (~20% of content unreachable)

### The problem, restated

Median eligible pool is 207 events/day. Only 22.5% of daily draw weight reaches
arc/NPC/relationship content. 100 of 483 events never fire across 40 complete runs.
`DEPTH_SCALE ** depth` in `engine/selector.py:115` boosts chain *continuations* but
cannot help a chain's **first link**, which competes flat against ~150
always-eligible ambient events.

Median weights are not the problem (ambient 4.0, arc 8.0). Volume and eligibility
are.

### Step 0 -- Build the missing measuring instrument (do this first)

**There is currently no checked-in way to verify this item's acceptance criteria.**
The numbers above came from scratch harnesses that were not committed. Step 0 is to
build one.

Create `tests/coverage_audit.py`:

- Drives N complete runs (default 40) through
  `select_event -> eligible_choices -> resolve_choice -> end_of_day_decay`,
  picking choices at random, exactly as `tests/sim_bot.py` does. Reuse sim_bot's
  playout structure where practical rather than duplicating it.
- `load_all_events()` per run (it resets per-event fire state on entry).
- Reports:
  - total events never fired, and the same broken down by source pack
  - median eligible pool size per day
  - median share of daily draw *weight* going to arc content
    (tags: `flagship`, `arc`, `npc`, `betrayal`, `resistance`, `relationship`)
  - unique events seen per run, and repeat-pick fraction
- Supports `--assert` with thresholds so it can become a standing gate, and
  `-n` for a smaller run count, matching `pargate.py`'s CLI conventions.
- Deterministic under a seed, like sim_bot.

Run it and confirm it reproduces the baseline in §6 below. **If it does not
reproduce, trust the new harness and correct §6** -- but say so explicitly in your
report, because it means the recorded baseline was wrong.

### Step 1 -- Implement the quota

Cap ambient-flavored events at **1 of the 3 daily slots**.

- The tag set to budget is `ambient` and `micro` (88 events, median weight 4.0).
  Verify this set against the deck before committing to it -- `job` is a large tag
  (82 events) that is *mostly* filler but also carries real arc entries, so it is
  deliberately excluded. Report if you disagree after looking.
- Thread an optional budget parameter into `select_event`
  (`engine/selector.py:129`). The pool filter belongs next to the existing
  `exclude_ids` filter at line 144.
- Callers maintain the per-day counter:
  - `main.py:148-186` -- the `fired_today` slot loop.
  - `server.py:120-163` -- `advance_event`. Note this method retries up to 8 times
    to skip events whose choices are all locked; the budget must be consulted
    inside that loop, and the counter must reset alongside `self.fired_today` at
    line 138 and in `reset()` at line 165.

**Failure mode to guard explicitly:** if the quota is spent and the remaining
eligible pool is empty, `select_event` must fall back to the unbudgeted pool rather
than return `None`. Returning `None` would silently burn the player's action slot.
Early game is the realistic trigger -- most always-eligible content is ambient. Add
a unit test for exactly this case.

### Step 2 -- Verify

In this order:

```bash
python -m unittest discover -s tests     # must pass, including new quota tests
python pipeline/lint_content.py          # must stay clean
python tests/coverage_audit.py           # compare against §6 baseline
python tests/pargate.py                  # ~9 min; balance gates must still hold
```

### Acceptance criteria

| Metric | Baseline | Target |
|---|---|---|
| Events never fired in 40 runs | 100 | **< 70** |
| Arc draw-share (median) | 22.5% | **> 35%** |
| Unique events per run | ~96 | higher, no target |
| `pargate.py` | passing | **still passing** |
| `unittest` + `lint_content` | passing | **still passing** |

If `pargate.py` breaks, the quota is the tuning knob -- try budgeting 2 of 3 slots
before abandoning the approach. Report which value you landed on and why.

**Explicitly out of scope for this window:** F2's fake-dice work, any weight
retuning on individual events, any content edits. If the quota alone cannot hit the
targets, report that finding rather than reaching for a second lever.

### On completion

Update §3, rewrite §4 for **F2**, append to §5 anything you found and deferred, and
end your message to the user with the model + ready-to-paste prompt for F2.

---

## 5. Discovered work (append-only)

Adjacent problems found mid-task that were deliberately *not* fixed in that window.
Triage these into the status board when they earn their place.

- *(2026-07-27, audit)* `tests/coverage_audit.py` did not exist; F1's acceptance
  criteria were unverifiable. Folded into F1 as Step 0.

---

## 6. Recorded baseline

Measured 2026-07-27 on branch `content-audit-and-lint` @ `d3de304`, random-choice
play, `load_all_events()` per run.

| Metric | Value |
|---|---|
| Events in deck | 483 (24 packs, 388 flags, lint clean) |
| Median eligible pool per day | 207 |
| Unique events seen per run | ~96 (19.8% of deck) |
| Events never fired in 40 runs | 100 (20.7%) |
| Arc draw-weight share (median) | 22.5% |
| Repeat-pick fraction | 16.8% |
| Median run length | 37 days |
| Truly guaranteed choices | 498 / 1468 (34%) |
| Base-1.0 choices that still fail 2% via `P_MAX` | 123 |
| Good endings in 20 random runs | 0 |

Per-pack unreached counts are in `STEAM_READINESS_BACKLOG.md` §1 / S3.

**Anyone changing these numbers must update this table in the same window**, with
the command that produced the new figures.
