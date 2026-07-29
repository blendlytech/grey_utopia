# A4 -- Put the cast on screen: the Step 0 census

*2026-07-29, Opus 5. Companion to `docs/STEAM_READINESS_BACKLOG.md` §A4 and
`docs/BACKLOG_HANDOFF.md` §3-§5.*

**Verdict: A4's premise is disproved on presence and correct about the surface
for the wrong reason. Closed. Nothing was built from the spec; one thing A4
asked for turned out to already exist and shipped.**

The instrument is `tests/cast_audit.py` (`--presence` / `--interrupt` /
`--retention`), which reuses `steward_audit.playout` rather than adding a sixth
copy of the day loop. All figures below are n=40 per strategy, seeds 0..39, so
160 runs per table.

---

## 1. The three claims, and what each measured

A4 as written says: *"Mara, Vint, and Kael should interrupt unprompted, carry
visible arcs, and react to each other. The relationship web is already wired;
the player-facing surface is a percentage bar in the right sidebar. Portraits
plus a 'what they want from you right now' line converts numbers into people."*

| claim | measured | verdict |
|---|---|---|
| they should be on screen | Mara on **41-52%** of run-days, Vint **33-37%**, Kael **21-27%**; **0 of 160 runs** where any of the three never appears | **wrong** |
| they should interrupt unprompted | already forced once, in the prologue, where all three bars are introduced; afterwards nothing is forced, but cast events carry median weight **7-8 against the deck's 6** | **wrong** |
| the surface is a percentage bar | true -- and for **two of the three that bar reads 0-4% on ~90% of run-days and does not respond to play at all** | **right, worse than stated** |
| they should carry visible arcs | `npc_arcs_pack` is a chain of single-source flags; its head fires **0 of 160 runs** | **right** |

This is the fifth consecutive backlog spec to be overturned by its own Step 0
(S2/S3 by F1, S8/S9 by SHIP, A3 by its own window, F6 unbuilt). The presence
finding is A3's finding again, almost exactly: an item written as "this
character is absent" measured as "this character is on screen half the time and
the problem is that none of it accumulates."

---

## 2. Q1 -- How often is the cast actually on screen?

An event counts as an appearance if a contact is **named in prose the player
reads** (title, body, choice text, branch text, inserts). `mech/run` is the
stricter test: the event also moves or reads that bond.

| strategy | contact | events/run | mech/run | days seen | % of days | longest gap | never |
|---|---|---|---|---|---|---|---|
| random | Mara | 21.0 | 11.1 | 16.9 | **52.2%** | 5.2 | 0/40 |
| random | Vint | 11.9 | 3.5 | 11.0 | 33.5% | 7.9 | 0/40 |
| random | Kael | 7.2 | 2.8 | 6.9 | 21.0% | 11.4 | 0/40 |
| cautious | Mara | 34.2 | 16.8 | 28.3 | **45.8%** | 7.0 | 0/40 |
| cautious | Vint | 26.0 | 8.4 | 22.9 | 36.9% | 8.4 | 0/40 |
| cautious | Kael | 13.8 | 4.6 | 12.8 | 21.0% | 14.2 | 0/40 |
| reckless | Mara | 29.4 | 14.8 | 24.9 | 41.3% | 8.0 | 0/40 |
| reckless | Vint | 23.1 | 7.2 | 20.4 | 33.4% | 9.7 | 0/40 |
| reckless | Kael | 16.0 | 5.5 | 14.7 | 24.3% | 13.5 | 0/40 |
| greedy | Mara | 29.1 | 13.7 | 25.2 | 42.7% | 7.9 | 0/40 |
| greedy | Vint | 22.8 | 7.2 | 20.1 | 33.7% | 9.7 | 0/40 |
| greedy | Kael | 17.9 | 6.3 | 16.3 | 27.4% | 12.2 | 0/40 |

The deck carries **77 events naming Mara, 68 naming Vint, 64 naming Kael**, of
which 48 / 25 / 32 also move the bar. A cautious player meets Mara on 28 of
their ~60 days. **"Put the cast on screen" describes a game this is not.**

Echo is the honest contrast and is kept in the census for it: 1.6-5.0
events/run, **never in the network at all in cautious play**, and absent from
5-6 of 40 runs elsewhere. Echo is an earned contact; the three promoted ones are
not scarce.

---

## 3. Q2 -- Do they already interrupt unprompted?

| contact | named | mech | sat-gated | forced | median weight | max drawn weight |
|---|---|---|---|---|---|---|
| Mara | 77 | 48 | 4 | 8 | 7.0 | 20.0 |
| Vint | 68 | 25 | 0 | 8 | 7.0 | 20.0 |
| Kael | 64 | 32 | 2 | 10 | 8.0 | 18.0 |
| Echo | 34 | 21 | 0 | 0 | 8.0 | 18.0 |

**Yes, once.** The four `prologue_*_descent` storylets are `weight: 500000`,
exactly one fires per run in the opening days, and each of them names *and moves
the bar for* all three contacts. That is where the network is introduced. The
other forced hits are six `origin_threads_pack` chain heads that mention them in
passing without touching the bars.

**After the prologue, nothing in the cast is forced** -- but the deck median
weight is 6.0 and the cast sits at 7-8, so they are not drowned either. They win
their share of draws, which is what the presence table shows. A3's mistake was
nearly re-inventing a scheduled turn that already existed; the equivalent
mistake here would have been forcing content that already reaches the player.

**The satisfaction gates are the one place the bar changes what a run contains,
and there are six of them in a 503-event deck:**

| contact | event | gate | fired |
|---|---|---|---|
| Mara | `hz_mara_sees_the_bench` | `>= 50` | 20/160 |
| Mara | `hz_nerve_rebuilt` | `>= 40` | 13/160 |
| Mara | `res_shepherd_contract` | `>= 30` | 1/160 |
| Mara | `reck_near_overdose_mara` | `>= 25` | 1/160 |
| Kael | `reck_syndicate_deadline` | `>= 45` | 9/160 |
| Kael | `arc_mara_the_door` | `>= 55` (choice-level) | **0/160** |

Every gate that reads Vint is absent because there are none: **Vint's bar gates
nothing in the entire deck.** Kael's two gates ask for 45 and 55 against a bar
that measures 0.6-2.2. Those are not thresholds, they are walls.

---

## 4. Q3 -- What is `relationship_retention` actually doing? *(the real defect)*

`end_of_day_decay` applies `R = e^(-1/S)` once per day and writes the result
back, so decay compounds daily. `reinforce` adds +1.5 to S (cap 40) and is the
**only** thing that ever raises it -- `strain` deliberately does not. Starting
values come from `data/cast.json`: Mara 75 / S 12, Vint 50 / S 6, Kael 40 / S 8.

Untouched, those curves are:

| contact | S | d5 | d10 | d20 | d30 | d40 |
|---|---|---|---|---|---|---|
| Mara | 12.0 | 49.44 | 32.59 | 14.17 | 6.16 | 2.68 |
| Vint | 6.0 | 21.73 | 9.44 | **1.78** | 0.34 | 0.06 |
| Kael | 8.0 | 21.41 | 11.46 | **3.28** | 0.94 | 0.27 |

**In play, Mara is a live system and Vint and Kael are not.** Median
satisfaction at day D, with the share of run-days each bond spends below the
UI's own thresholds (`renderContacts` adds the `fading` class below 30;
`check_endings` reads "every bond under 20" as the Empty Suite):

| contact | strategy | d10 | d20 | d30 | d40 | d60 | final | %days<30 | %days<20 |
|---|---|---|---|---|---|---|---|---|---|
| **Mara** | cautious | 64.0 | 58.8 | 53.2 | 54.8 | 59.7 | **50.0** | **5.0%** | 0.6% |
| | reckless | 68.6 | 49.4 | 50.0 | 46.1 | 44.6 | 45.0 | 9.6% | 2.0% |
| | greedy | 70.3 | 55.2 | 51.2 | 45.0 | 43.0 | 45.0 | 6.9% | 1.4% |
| | random | 35.4 | 22.1 | 20.3 | 16.9 | 30.2 | 12.5 | 43.3% | 23.7% |
| **Vint** | cautious | 9.4 | 1.2 | 0.7 | 0.5 | 0.0 | **0.0** | **93.3%** | **89.8%** |
| | reckless | 9.4 | 3.5 | 2.3 | 1.8 | 3.0 | 3.5 | 93.0% | 89.2% |
| | greedy | 9.4 | 3.9 | 3.1 | 2.4 | 4.0 | 3.9 | 92.7% | 88.7% |
| | random | 9.7 | 3.6 | 1.1 | 0.8 | 0.0 | 2.1 | 83.9% | 74.6% |
| **Kael** | cautious | 11.5 | 3.3 | 1.7 | 1.2 | 0.8 | **0.7** | **95.0%** | **89.8%** |
| | reckless | 11.5 | 3.3 | 1.9 | 1.3 | 2.4 | 1.3 | 94.7% | 89.1% |
| | greedy | 11.5 | 3.3 | 2.2 | 2.0 | 1.0 | 0.6 | 94.0% | 87.8% |
| | random | 11.5 | 3.3 | 1.7 | 0.7 | 0.1 | 1.9 | 87.4% | 76.1% |

### 4.1 The decisive test: can the bond accumulate at all?

Counting S increments counts reinforcements exactly. A bond grows only if
reinforcements arrive faster than the curve erases them, so the number that
decides everything is **mean gap between reinforcements / the bond's own
half-life (S ln 2)**. Above 1.0, each reinforcement lands on a bond that has
already fallen below half of the last one, and satisfaction can never climb --
the bar is a sawtooth against zero no matter how the player behaves.

| contact | strategy | reinf/run | mean gap | median S | half-life | ratio | verdict |
|---|---|---|---|---|---|---|---|
| Mara | cautious | 12.1 | 5.2 | 23.6 | 16.4 | **0.32** | grows |
| Mara | reckless | 11.4 | 5.4 | 22.5 | 15.6 | **0.34** | grows |
| Mara | greedy | 10.4 | 5.6 | 22.5 | 15.6 | **0.36** | grows |
| Mara | random | 4.3 | 8.0 | 15.0 | 10.4 | 0.77 | grows |
| Vint | cautious | 2.0 | 30.0 | 7.5 | 5.2 | **5.77** | cannot accumulate |
| Vint | reckless | 4.0 | 15.2 | 9.0 | 6.2 | **2.44** | cannot accumulate |
| Vint | greedy | 4.2 | 14.3 | 9.0 | 6.2 | **2.30** | cannot accumulate |
| Vint | random | 1.6 | 17.5 | 7.5 | 5.2 | 3.37 | cannot accumulate |
| Kael | cautious | 1.9 | 33.8 | 9.5 | 6.6 | **5.13** | cannot accumulate |
| Kael | reckless | 2.3 | 31.2 | 9.5 | 6.6 | **4.75** | cannot accumulate |
| Kael | greedy | 2.4 | 25.5 | 9.5 | 6.6 | **3.87** | cannot accumulate |
| Kael | random | 0.8 | 23.0 | 8.0 | 5.5 | 4.15 | cannot accumulate |
| Echo | reckless | 2.3 | 11.8 | 6.5 | 4.5 | 2.63 | cannot accumulate |
| Echo | greedy | 1.0 | 7.0 | 5.0 | 3.5 | 2.02 | cannot accumulate |

**Not one strategy gets Vint, Kael or Echo under 1.0. Not one gets Mara over
0.8.** The system is not marginal for two of the three; it is on the wrong side
of its own threshold by a factor of 2.3 to 5.8.

### 4.2 And the bar does not answer to play

This is A3's test applied to the cast, and it is the reason A4's sidebar work
would have been decoration. Spread of median final satisfaction across the four
strategies:

| contact | low | high | spread |
|---|---|---|---|
| Mara | 12.54 | 50.04 | **37.50** |
| Echo | 0.00 | 8.91 | 8.91 |
| Vint | 0.00 | 3.89 | **3.89** |
| Kael | 0.60 | 1.90 | **1.30** |

A3 rejected the dossier-flag trigger at a 1.12x spread with the line *"a tenure
clock wearing an antagonist's coat: it measures how long you lived, not how you
played, so there is nothing to play against."* Kael's bar spans **1.3 points of
satisfaction** across every way this game can be played. It measures nothing.

**Two terms drive it and both are broken for Vint and Kael, which is why raising
the starting strength alone would not fix either of them.** Kael's gap is 25-34
days; at Mara's starting S of 12 his half-life would be 8.3 days and the ratio
would still be 3-4. The dominant term is reinforcement *frequency* -- Mara
receives 10-12 per run, Kael 1.9-2.4 -- and the second is that S only grows on
warm interactions, so the contacts whose content is roughly half-adversarial
never build the memory strength that would let a reinforcement survive to the
next one. It compounds: low S means each reinforcement evaporates before the
next arrives, so the bond can never climb out. Mara is the only one who starts
rich enough to escape it.

### 4.3 The Empty Suite gate is already mostly a random-play ending

Runs in which **every** bond is under 20:

| strategy | at day 20 | at day 30 | at end | ending actually fired |
|---|---|---|---|---|
| random | 12/40 | 7/40 | **29/40** | 1/40 |
| cautious | 0/40 | 2/40 | 0/40 | 0/40 |
| reckless | 1/40 | 1/40 | 1/40 | 0/40 |
| greedy | 0/40 | 0/40 | 1/40 | 0/40 |

29 of 40 random runs satisfy the relationship half of
`NEUTRAL_alienation_empty_suite` and 1 reaches the ending, because
`Social_Capital < 15` is what actually binds. Deliberate play is held above the
line by Mara alone -- Vint and Kael are under 20 on ~89% of days in every
strategy. **Any future fix to the curve should re-check this gate**, since
raising Vint and Kael would make the "every bond" clause harder to satisfy in
exactly the runs that currently satisfy it.

---

## 5. What A4 asked for that already existed -- and shipped this window

A4's headline deliverable is *"a 'what they want from you right now' line,
state-derived, in each character's voice key."*

**`engine/ambient.py:84` is that function.** `_mara_signal` reads
`last_reinforced_day`, and at 10 / 20 / 35 days of silence escalates:

> It's been 12 days since you last called Mara.
> It's been 24 days since you called Mara. She's stopped asking why.
> It's been 38 days since you spoke to Mara. You're starting to forget the sound of her voice.

It is state-derived, in Mara's register (love arriving as logistics; the third
line is the arc landing), ranked against the day's other pressures by
`morning_report`, and it has shipped for as long as the terminal front end has
existed.

**The web front end has never rendered it.** `server.py:441` sends
`state.ambient` -- both `morning_report` and `steward_ledger_line` -- on every
state call, and nothing in `web/app.js` read that key. `app.js:1077` records the
fact in a comment while routing A3's filing notice around it. So the one thing
A4 wanted built was already written, already served over the wire, and dropped
on the floor by the client.

**Shipped:** `showDayOverlay` now renders `state.ambient.morning_report` and
`state.ambient.ledger_line` under the night ledger, in the same order the
terminal prints them and at the same moment in the day. It is placed there and
not in a sidebar panel for two reasons: the terminal prints it at the top of the
day right after the night's accounting (`main.py:173`), and the left column is
already four panels deep (`A3_DESIGN.md` §2). The overlay's dwell extends
2650 -> 3900 -> **5600ms** when there is prose to read, with a matching
`.has-morning` animation duration, because two sentences do not fit in the
ledger's 3.9s.

This is a pure render change: no engine, no content, no preconditions, no day
loop. It is not a balance change and did not need `pargate`.

---

## 6. Art scope, stated early as §4 asked

`data/assets/` holds **6 scene jpgs** (`fixer_hideout`, `offgrid_wilderness`,
`overdose_collapse`, `steward_sanctuary`, `street`, `vice_lounge`) and
`originals/` holds 5 pngs for them. **There is no portrait source art for any of
the nine cast members and no pipeline that could cut one** --
`pipeline/crop_scenes.py` cuts places-only bands out of scene originals.

Portraits are therefore not a code task at all; they are an asset commission of
3-9 images that do not exist. That is the honest scope, and it is the second
reason A4-as-written was not the right next window: its cheap half was already
built and its expensive half is not engineering.

---

## 7. `npc_arcs_pack` -- the arc problem, structurally

§4 of the handoff named this correctly (7/17 ever eligible, 10 union-unreachable)
and the census adds the mechanism. The pack is **two tiers of single-source
flags**:

| gate flag | sources | gates |
|---|---|---|
| `vint_known` | **93** | `arc_vint_open_account` |
| `kael_impressed` | **1** (`volume_npc_kael_syndicate_check_in`) | `arc_kael_unpriced_line`, `arc_kael_the_audit` |
| `echo_brother_known` | **1** (`res_why_you_fix`) | `arc_echo_rollback_offer`, `arc_echo_the_courier` |
| `clock_mara_dark_expired` | **1** (`twist_mara_unwatched`) | `arc_mara_the_door` |
| `mara_ransomed` / `mara_freed` / `mara_graduated` / `mara_deep` | **1 each, all `arc_mara_the_door`** | 4 events |
| `vint_owes_you` / `vint_taken` / `vint_counterparty` | **1 each, all `arc_vint_open_account`** | 3 events |
| `kael_owned` / `kael_sold` / `kael_spared` | **1 each, all `arc_kael_the_audit`** | 3 events |

**`arc_mara_the_door` fired 0 times in 160 runs**, and it is the sole source of
the four flags that gate four more events -- so one unreachable storylet
accounts for 5 of the 17. `kael_impressed`'s single volume-event source accounts
for 5 more. Eleven of the seventeen are tier-2 content whose only entrance is a
tier-1 event in the same pack.

This is exactly the shape `res_chalk_second_look` was written for in A1 Phase 3c,
and the fix is the same: second entrances on the tier-1 heads, not new content.
**It is a content change and therefore a balance change**, with reckless
terminal at 0.8 points of headroom and `starved` at 2.4 -- which is why it was
not done in the same window as a measurement, per the board's §1 step 3.

---

## 8. Verdict and the successor item

**A4 is closed, premise disproved, in the F6 pattern.** No portraits, no
sidebar rework, no second surface. The census is the deliverable, plus
`tests/cast_audit.py` and the `state.ambient` render fix that A4 turned out to
have already been given.

**The real item is the retention curve, and it now has its measurement.** The
one-line statement of it: *two of the three promoted contacts sit below 4%
satisfaction on ~90% of run-days, their reinforcement gap exceeds their
half-life by 2.3-5.8x under every strategy, and the resulting bar moves 1.3-3.9
points across every way the game can be played.* Until that is false, a portrait
is a picture next to a dead number.

Three levers exist and the measurement says which are viable:

1. **Reinforcement frequency** (Mara 10-12/run, Kael 1.9-2.4). The dominant
   term. Moving it means changing which branches the deck reinforces on, which
   is a content change and a balance change.
2. **Memory strength growth.** `strain` raises satisfaction's opposite but not
   S, though Ebbinghaus strength is memorability and not affection -- a broker
   you keep crossing remembers you vividly. An engine change, no content cost,
   and it is the cheapest thing to measure first. **On its own it is not
   sufficient**: at Kael's measured strain rate it moves the ratio to ~2.0-2.8,
   still above 1.0.
3. **Starting parameters** (`data/cast.json`, Vint S 6 / Kael S 8 against Mara's
   12). Alone it fixes neither -- §4.2 -- but it is the third term and is free.

Whatever is tried, the acceptance criterion is not "the bars are higher." It is
**ratio < 1.0 in at least the deliberate strategies, and a cross-strategy spread
on the order of Mara's 37.5 rather than Kael's 1.3** -- a bond the player can
lose by playing one way and keep by playing another. Re-run
`python tests/cast_audit.py --retention` and read the accumulation table; it was
built to answer exactly this and it is the gate.
