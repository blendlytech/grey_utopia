# F7 -- Make the relationship bars playable

**Window:** 2026-07-29. **Model:** Opus 5, in-session.
**Predecessor:** `A4_DESIGN.md` §4, which measured the defect and handed over the
gate (`tests/cast_audit.py --retention`, the "CAN THE BOND ACCUMULATE?" table).

**Verdict: shipped, and half the gate is met.** Vint clears in all four
strategies. Kael clears in one of three deliberate strategies and is blocked in
the other two by a cause this window is not allowed to touch -- with the
measurement that proves it is that cause and not the levers.

---

## 1. Step 0 -- the baseline reproduced exactly

A4's table, re-run before anything was changed: Vint 5.77 / 2.43 / 2.30, Kael
5.13 / 4.75 / 3.87, Mara 0.32-0.36 and a 37.50 spread. No re-measurement of
presence or coverage; seven windows have closed those.

---

## 2. The instrument had to be fixed before it could grade the change

A4 counted reinforcements by counting increments of `strength`, and said so:
*"`reinforce` adds +1.5 to S and is the only thing that ever raises it, so
counting S increments counts reinforcements exactly."* That was true when it was
written. **Lever 2 makes it false**, because lever 2 is precisely "let `strain`
raise S too" -- after which an inferred count scores every adversarial contact as
a reinforcement, shrinking the measured gap and lengthening the half-life at the
same time. The gate would have graded its own change, in the favourable
direction, twice.

So `Relationship.reinforcements` is now an explicit counter that only
`Character.reinforce` increments, `steward_audit.playout` records it per day, and
`cast_audit` reads it. Re-running the baseline through the corrected instrument
reproduced A4's Vint and Kael rows to the digit.

The one number that moved is Mara's, 12.1 -> 12.8 reinforcements and 0.32 -> 0.29:
the old test counted *days on which S rose*, so a second reinforcement on a day
that already had one was invisible. Mara is the only contact with enough contact
for that to ever happen, which is itself a small confirmation of A4's thesis.

---

## 3. The deficit is touches, not routing

`adjust_relationship` was logged for every application across the same seeded
sweep. Means over 40 runs:

| contact | strategy | touches | positive | negative | sum+ | sum- |
|---|---|---|---|---|---|---|
| **Mara** | cautious | 13.7 | 12.9 | 0.8 | +143.2 | -2.4 |
| | reckless | 14.0 | 12.2 | 1.8 | +143.2 | -10.5 |
| | greedy | 12.1 | 11.0 | 1.1 | +131.1 | -5.0 |
| **Vint** | cautious | 4.7 | 2.0 | 2.8 | +9.2 | -10.9 |
| | reckless | 5.2 | 4.2 | 1.1 | +20.2 | -3.7 |
| | greedy | 5.0 | 4.4 | 0.6 | +21.8 | -2.1 |
| **Kael** | cautious | **2.0** | **2.0** | **0.0** | +5.3 | 0.0 |
| | reckless | 3.5 | 2.3 | 1.2 | +14.6 | -4.9 |
| | greedy | 3.6 | 2.4 | 1.2 | +14.8 | -4.7 |

Nothing is mis-routed. A cautious player simply interacts with Kael **twice in a
~58-day run**, against Mara's fourteen. Kael's cautious row also settles lever 2
on its own before it is tried: **he takes zero adversarial touches in cautious
play**, so growing S on strain cannot move him there by construction.

### 3.1 The deck already puts them on screen; it just never wrote it down

Splitting the deck by A4's own attribution -- events that *name* a contact in
prose the player reads, versus events that *move their bar*:

| contact | names him | moves his bar | names him **silently** | silent firings / deliberate run |
|---|---|---|---|---|
| Vint | 68 | 25 | 44 | **17.03** |
| Kael | 64 | 32 | 33 | **10.38** |

And the sharpest form of it: **Vint has nineteen storylets tagged
`"relationship"`, and not one of them touched his bar.** Their prose is doing
nothing but moving the bond --

> "Vint doesn't say thank you so much as go quiet with it -- the kind of quiet
> that means he'll remember this longer than you will."
> "Something between you now costs exactly what you charged for it."
> "Morning brings a curt message: 'Fixed it myself. Thanks for nothing.'"
> "He nods stiffly and leaves the part on the table, the warmth gone from his face."

-- against an engine that recorded none of it. This is A4's lesson in a second
costume: *check whether the thing you are about to write already exists and is
merely unwired.* A4 found prose the engine composed and never rendered; F7 found
prose the player reads and the engine never scores.

---

## 4. The three levers, A/B'd separately

Each arm measured alone against the same seeds, because this deck's levers are
documented non-monotonic.

- **A -- reinforcement frequency (content).** 175 `rel_deltas` written onto
  branches of storylets that already fire and already name the contact. Every
  value is read off the branch text it attaches to; the warm branch spends
  something of yours, the cold branch turns the bond into a transaction or
  refuses it. Vint's register is friendship, Kael's is a ledger. **No new events,
  no new choices, no gate changes** -- the deck is still 503 events / 398 flags,
  which is why `starved` did not move.
- **B -- memory strength on adversarial contact (engine).** `strain` now raises S
  by `K_STRAIN = 1.0`, against `reinforce`'s 1.5. S is memorability, not
  affection; a broker you keep crossing remembers you vividly. It builds slower
  than warmth so that burning a contact is not a way to make them durable.
- **C -- starting strength.** Vint 6 -> 10, Kael 8 -> **14**. Kael's defining trait
  is that he remembers ("he doesn't say anything -- he just remembers"; the book
  you are not allowed to read) and Vint is an archivist who never throws a drive
  away. Both were forgetting the player faster than the sister does, which
  inverted all three characterizations at once.

**Accumulation ratio, deliberate strategies only (cautious / reckless / greedy):**

| arm | Vint | Kael | Mara spread |
|---|---|---|---|
| baseline | 5.77 / 2.43 / 2.30 | 5.13 / 4.75 / 3.87 | 37.50 |
| **B alone** | 4.95 / 2.40 / 2.30 | **5.13** / 4.29 / 3.50 | 38.77 |
| **A alone** | 0.67 / 0.47 / 0.40 | 4.06 / 1.92 / 1.39 | 36.72 |
| A + B | 0.55 / 0.45 / 0.40 | 3.98 / 2.03 / 1.25 | 37.52 |
| **A + B + C (shipped)** | **0.44 / 0.36 / 0.32** | 2.48 / 1.32 / **0.84** | **37.52** |

B alone left Kael's cautious ratio at 5.13, unchanged to the digit, exactly as
his zero-strain row predicted. A is the dominant term by a factor of about
twenty, which is what A4 said it would be.

---

## 5. Kael's cautious gate is blocked on `kael_impressed`, and here is the proof

Kael's reinforcement count in cautious play, by arm: **1.9, 1.9, 2.1, 2.1, 2.1.**
It is invariant. B and C move `strength`, and `strength` is the denominator; the
numerator is the *gap between reinforcements*, and only content moves that. At a
27.2-day cautious gap, clearing 1.0 would need a half-life of 27.2 days, i.e.
**S ≈ 39 against a hard cap of 40** -- unreachable, and meaningless if reached.

The cause is structural and was measured, not assumed. Kael has ten storylets
tagged `"relationship"`. **All ten are gated on `kael_impressed`, and all ten fire
zero times in forty cautious runs.** That flag has exactly one source -- the
`impress_kael` branch of `volume_npc_kael_syndicate_check_in` -- and cautious
play picks that event's `stay_humble` branch 33 times out of 40.

So every warm Kael storylet in the deck is behind a door a cautious player almost
never opens. What cautious can reach was wired this window and is the whole list:
`amb_clean_1_the_name/ask_kael_first`, the check-in's `stay_humble`, and
`twist_kael_exit_appraisal/buy_the_exclusivity` (13/40). Two reinforcements a run,
which is what the audit reports.

**`kael_impressed` is named in `A4_DESIGN.md` §7's single-source table, so opening
it is the adjacent window's fix and was deliberately not done here** -- doing it
alongside 175 delta edits would make both unattributable. Kael's remaining gap is
therefore handed forward as a sized, specific item rather than a mystery: he
needs a second source for `kael_impressed`, or ungated warm Kael content, and
nothing else will do it.

---

## 6. Predictions, scored

Recorded before measuring, per the board's protocol.

1. **"Empty Suite's `at end` for random drops sharply from 29/40; the ending
   itself moves by at most 1/40." -- half wrong.** The ending held at 1/40 as
   predicted, but random's `at end` barely moved: 29 -> 29 -> 27 -> 26. The reason
   is a real one and worth keeping: random play picks branches uniformly, so the
   new warm branches and the new cold branches cancel, and its Vint/Kael
   reinforcement counts rose only 1.6 -> 4.0 and 0.8 -> 1.1. **The wiring made the
   bonds playable without making them free**, which is the correct outcome and
   not the one predicted. Deliberate play moved instead: 0/1/1 -> 2/0/0.
2. **"Vint clears on wiring alone." -- correct.** 0.67 / 0.47 / 0.40 from arm A.
3. **"Kael cautious is the one at risk, because his warm content is gated behind
   `kael_impressed`." -- correct**, and §5 is the proof.

---

## 7. Acceptance criteria against what shipped

| criterion | result |
|---|---|
| ratio < 1.0 for **Vint**, three deliberate strategies | **MET** -- 0.44 / 0.36 / 0.32, and random clears too at 0.94 |
| ratio < 1.0 for **Kael**, three deliberate strategies | **NOT MET** -- 2.48 / 1.32 / 0.84. Greedy clears; cautious and reckless are blocked on §5. Improved from 5.13 / 4.75 / 3.87. |
| cross-strategy spread on the order of Mara's 37.5 | **PARTIAL** -- Vint 3.89 -> **15.34**, Kael 1.30 -> **6.03**. Both are 4-5x the baseline and both are now bonds a player can lose by playing one way and keep by playing another, but neither is Mara's 37.5. |
| **Mara must not be flattened** | **MET** -- 0.28 / 0.30 / 0.32 against a 0.32 / 0.34 / 0.36 baseline, spread **37.52 against 37.50**. She is untouched. |
| all standing gates green | **MET** -- see §8 |

The honest one-line summary: **Vint went from a dead readout to a live system;
Kael went from a dead readout to a system that is live for a player who pushes
and still dead for a player who does not, because the content that would reward
the careful player is behind a flag this window was walled off from.**

---

## 8. What the player actually sees

Median satisfaction at day D, with the share of run-days each bond spends below
the UI's own thresholds -- the same table as `A4_DESIGN.md` §4, re-run on what
shipped. A4's figures in brackets.

| contact | strategy | d10 | d20 | d40 | final | %days<30 | %days<20 |
|---|---|---|---|---|---|---|---|
| **Vint** | cautious | 24.0 [9.4] | 15.2 [1.2] | 13.2 [0.5] | **13.4** [0.0] | 83.7% [93.3] | **58.7%** [89.8] |
| | reckless | 28.1 [9.4] | 21.6 [3.5] | 22.1 [1.8] | **24.0** [3.5] | 64.0% [93.0] | **34.3%** [89.2] |
| | greedy | 24.1 [9.4] | 20.2 [3.9] | 21.7 [2.4] | **23.5** [3.9] | 65.8% [92.7] | **29.3%** [88.7] |
| **Kael** | cautious | 19.6 [11.5] | 9.6 [3.3] | 2.3 [1.2] | 1.7 [0.7] | 91.5% [95.0] | 82.8% [89.8] |
| | reckless | 19.6 [11.5] | 11.1 [3.3] | 7.4 [1.3] | **6.5** [1.3] | 90.7% [94.7] | 73.3% [89.1] |
| | greedy | 19.6 [11.5] | 12.0 [3.3] | 9.3 [2.0] | **7.7** [0.6] | 86.0% [94.0] | 67.1% [87.8] |

The column that matters is the last one. Vint's share of days spent below the
alienation line went **89.8% -> 58.7%** for a cautious player and **88.7% ->
29.3%** for a greedy one -- and the 29-point gap *between* those two is the thing
that did not exist before. Kael's moved too (89.8 -> 82.8, 87.8 -> 67.1) but he
still spends most of a cautious run under the line, which is §5 restated in the
units the player reads.

---

## 9. Gates

- **`pargate` GREEN** -- all balance gates passed, 4000 playouts, 16.9m.
  Cautious 55.4% long grey / 16.2% good / 11.9% terminal; reckless
  **TERMINAL 34.2%** against its (25, 35) band -- unmoved, its 0.8 of headroom
  intact; greedy 13.7% terminal and 40.8% good against `GOOD_CAP` 45.
  **`MIN_CAUTIOUS_ENDINGS` was the flagged risk and it improved**: cautious now
  reaches **6** distinct endings against a floor of 5, where the handoff recorded
  it sitting at exactly 5. The bond changes widened the tail rather than trimming
  it.
- `coverage_audit --assert` -- **starved 73.0 <= 76** (was 73.6),
  **outcompeted 35.6 <= 42** (was 35.8), mean never-fired 108.6 (was 109.4).
  Starved *improved*, because arm A added zero events. Not tightened: the gain is
  under 1% and the successor window is a content/gating window that needs the
  headroom.
- `coverage_audit --parity` -- 3/3 seeds identical.
- `unittest` -- 124 pass.
- `lint_content` -- clean; 26 packs, **503 events, 398 flags** (unchanged).

---

## 9. Discovered mid-window

- **`data/cast.json` does not drive the starting network.**
  `engine.stats.create_starter_fixer` hardcodes all three bonds; cast.json is
  read only by `lint_content` and the legacy-inheritance path. The handoff's
  lever-3 pointer named cast.json alone, so editing it would have been a silent
  no-op. Both are now updated and both carry a comment saying so, but the
  duplication is still live and should be collapsed.
- **Kael's ungated deck is adversarial almost end to end.** Of the branches a
  cautious run reaches on events that name him, the reachable warm ones number
  two. This is a characterization problem as much as a balance one: the ledger
  register is right for him, but a bond with no reachable warm branch is a bond
  the player can only ever lose.
- **`ot_aud_1_counter_audit`, `ot_aud_2_sweep` and `ot_aud_3_successor` fire
  ~40/40 in every deliberate strategy and name Kael without touching him.**
  `ot_aud_2_sweep/sell_the_schedule` is genuine Kael content ("takes the sweep
  schedule to Kael, who pays exactly what you expected"). All three are
  `gate_critical` origin threads, so wiring them perturbs branch scoring on
  content the reachability gates depend on; left alone deliberately, but they are
  the largest unwired Kael surface left.
