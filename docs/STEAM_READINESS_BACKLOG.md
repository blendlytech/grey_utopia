# GREY UTOPIA -- Steam Readiness Backlog

**Created:** 2026-07-27 (Opus 5, in-session audit)
**Baseline audited:** 483 events across 24 packs, 388 distinct flags, 14 endings, branch `content-audit-and-lint` @ d3de304

This document records every fix and addition identified in the 2026-07-27 deep-dive
audit. Each item carries the measurement that produced it, so a later session can
re-run the measurement and check whether the item is still live.

**Nothing in this document has been implemented.** It is a backlog, not a changelog.

---

## 0. How the numbers here were measured

All figures come from instrumented runs against the live deck, not from reading
content. Reproduce with:

```bash
# Deck composition, choice structure, stat usage
python pipeline/lint_content.py           # 483 events, 388 flags, clean

# Reachability / draw-share figures were produced by ad-hoc harnesses that
# drive select_event -> resolve_choice -> end_of_day_decay for N complete runs
# with random choice picks, counting per-event fire totals and eligible-pool
# composition. tests/sim_bot.py is the maintained equivalent for balance;
# these coverage harnesses were scratch and are NOT checked in.
```

Measured baseline, random play:

| Metric | Value |
|---|---|
| Events in deck | 483 |
| Median eligible pool per day | 207 |
| Unique events seen per run | ~96 (19.8% of deck) |
| Events never fired in 40 runs | 100 (20.7%) |
| Draw-weight share to arc/NPC/relationship content | 22.5% |
| Picks that were repeats | 16.8% |
| Median run length (random) | 37 days |
| Choices that are truly guaranteed (base >= 1.0, no failure branch) | 498 / 1468 (34%) |
| Choices at base 1.0 that still fail 2% via `P_MAX` | 123 |
| Good endings reached in 20 random runs | 0 |

---

## 1. Shortfalls (the diagnosis)

Numbered `S1..S9`. Fixes and additions below reference these.

### S1 -- One verb, never varied
Every interaction is: read text -> pick 1 of 3 -> hidden roll -> read text, for all
483 storylets. No second mechanical layer exists. Category comparison: Citizen
Sleeper (dice drafting/placement), Cultist Simulator (card combination), Fallen
London (item-crafting economy), Roadwarden (map traversal + time-of-day +
inventory). This is the only structural item on the list; everything else is
tuning.

### S2 -- Two of every three storylets are filler
Median eligible pool 207/day; only 22.5% of draw weight reaches arc/NPC/relationship
content. `DEPTH_SCALE ** depth` (`engine/selector.py:115`) boosts chain
*continuations* but cannot help a chain's **first link**, which competes flat
against ~150 always-eligible ambient events. Median weights are actually sane
(ambient 4.0, arc 8.0) -- this is a *volume and eligibility* problem, not a
weight problem.

### S3 -- ~20% of written content is unreachable
100 of 483 events never fired across 40 complete runs:

| Pack | Unreached | Note |
|---|---|---|
| legacy_pack | 18/18 | by design, NG+ gated |
| betrayal_pack | 19/30 | deep-chain gating |
| ambitions_pack | 18/24 | deep-chain gating |
| npc_arcs_pack | 11/17 | deep-chain gating |
| cast_expansion_pack | 7/35 | |
| reckoning_pack | 7/25 | |
| resistance_pack | 5/12 | |
| second_ferryman_pack | 4/7 | |
| horizon_pack | 3/13 | |
| sonnet_5_volume_pack | 3/185 | |

Meanwhile `sonnet_5_volume_pack.json` is 185 events (38% of deck) and 182 fire
regularly.

### S4 -- The economy is not one
10 items, ~12,750 cr for the full catalog. Random play: 1,080 cr at day 20,
3,290 cr at day 30, then plateau. The market does **not** consume an action slot
(`main.py:175-177`), so there is no opportunity cost. Wealth is neither scarce
enough to plan around nor abundant enough to feel like power.

### S5 -- Three stats are decorative

| Stat | Deltas written | Read in event preconds | Engine reads |
|---|---|---|---|
| Fame | 114 | 12 | none |
| Recklessness | 60 | 1 | one stress term (`W_RECK`) |
| Social_Capital | 551 | 3 | one ending check |

Social_Capital is the most-used probability mod in the deck (326 uses) but is
read by 3 preconditions -- a passive dice-fixer, never a resource spent.
Tolerance is well-modeled but displayed as "0.00 / 10.0" with no explanation of
what it costs.

### S6 -- Good endings are invisible until you are inside them
20 random runs: 7 overdose, 4 institutionalized, 3 alienation, 2 long grey,
2 buyout, 1 detachment, 1 winter garden, **0 good**. `crossed_wire`,
`chose_small_life`, `advocate_accepted` each need deliberate multi-week pursuit;
the UI signposts exactly one (the Exit Chain panel). 13 endings have no in-fiction
breadcrumb.

### S7 -- NG+ does not change the game
`engine/legacy.py` mints `legacy_cycle2plus`, per-ending flags, and 8 possible
echo flags, plus a stat nudge from `data/legacy_inheritance.json`. Run 2 plays
identically to run 1.

### S8 -- Presentation under-built for a paid release
Six scene images (`data/assets/*.jpg`) for 483 events and 14 endings. No NPC
portraits despite `data/cast.json` existing. No per-ending art. The web UI is a
three-column meter dashboard rather than a mood.

### S9 -- Missing shipping infrastructure
Single autosave slot (`server.py:79-118`), no manual saves, no settings menu
(audio is a binary ON/OFF), **no reduced-motion option** despite a full-screen CRT
overlay and `glitch-text` animation, no text scaling, no colorblind consideration
on tier-colored meters, no content warning screen (addiction / overdose /
involuntary commitment), no achievements, no Steam integration, no controller
support, no localization scaffolding.

---

## 2. Fixes to existing systems

### F1 -- Per-day ambient quota
**Addresses:** S2, S3
**Effort:** ~1 weekend. Highest impact-to-effort ratio in this document.

Cap ambient/micro-tagged events at 1 of the 3 daily slots. Implementation lives in
`engine/selector.py` -- `select_event` already receives `exclude_ids`; add an
analogous per-day tag budget threaded from the day loop in `main.py` and
`server.py`.

**Acceptance:** re-run the 40-run coverage harness; unreached count should fall
well below 100, and arc draw-share should rise above 22.5%. Then re-run
`python tests/pargate.py` -- this is a balance change, so gates must still pass.

### F2 -- Kill the fake dice
**Addresses:** S1 (partially), player-trust
**Effort:** small

Two sub-items:
- For the **498 truly guaranteed choices** (base >= 1.0, no failure branch),
  suppress the roll reveal in `web/app.js:913-974` and label them as decisions,
  not gambles.
- For the **123 base-1.0 choices that DO have a failure branch**, `P_MAX = 0.98`
  (`engine/resolver.py:11`) makes them fail 2% of the time. Either commit to a
  real gamble (lower the base) or delete the failure branch. An invisible 2%
  failure on a choice presented as certain reads to players as the game cheating.

### F3 -- Make money a decision
**Addresses:** S4
**Effort:** medium

- Market browsing should consume an action slot (`main.py:175-177`, and the
  `/api/buy_item` path in `server.py:353`).
- Add a daily upkeep burn in `end_of_day_decay`.
- Re-price the 10-item catalog against the new curve.

**Caution:** this is a balance change on a lever that has not been characterized.
Run the full gate, not the quick one.

### F4 -- Give Fame and Social_Capital a spend
**Addresses:** S5
**Effort:** medium (content + engine)

- **Fame** should open doors *and* raise Heat generation -- a real tradeoff
  rather than a number that moves 114 times and does nothing.
- **Social_Capital** should be spendable to call in favors. Pairs directly with
  A2 (preparation as an action), which gives it a sink.
- **Tolerance** needs a player-facing explanation of its cost in the HUD tooltip
  (`web/index.html:58`).

### F5 -- Signpost the endings in-fiction
**Addresses:** S6
**Effort:** medium

Not a quest log. A "what you could still become" panel showing the 2-3 endings the
player's current flags point at, phrased vaguely and in-fiction. Fallen London's
ambitions are the reference implementation. The existing Exit Chain panel
(`web/index.html:113-117`) is the pattern to generalize -- it already does this
for exactly one of fourteen endings.

---

## 3. Additions

### A1 -- The Row as a map  *(the big one)*
**Addresses:** S1, S2, S3, S7, S8
**Effort:** ~6-8 weeks

Turn 3 action slots into 3 **placements** across 6-8 districts. Each district
carries its own Heat, its own storylet shelf, and a travel cost.

Why this is the keystone item:
- It is the missing second verb (S1).
- Arc first-links get a district shelf instead of competing with ~150 ambient
  events, which fixes S2/S3 structurally rather than by tuning.
- Heat becomes spatial -- "the Row knows your face, work the Terraces this week."
- It converts the art problem into an art opportunity: 8 district images with real
  mechanical payoff beats 6 generic ones (S8).
- It gives NG+ something structural to unlock (S7).

**Open design work before starting:** schema changes to the storylet format,
selector rework, and a migration path for all 483 existing events (which currently
carry no location data).

### A2 -- Preparation as an action
**Addresses:** S1, S5
**Effort:** medium

Let a slot buy *setup*: scout a job, call in a favor (spends Social_Capital), buy a
specific edge. Converts the hidden roll from a coinflip into a plan -- the
difference between "I got unlucky" and "I under-prepared." Also gives the
probability model in `engine/resolver.py:119-132` something to be legible about.

### A3 -- Make the Steward take a turn
**Addresses:** S1, world-presence
**Effort:** medium

The Steward is the premise and is currently a stat modifier with 6 events in
`data/events/steward_interventions.json`. Give it a **visible weekly move**: it
files something, offers something, corrects something, escalates. One line the
player sees coming and can play against. An antagonist you can anticipate is worth
ten atmospheric mentions.

### A4 -- Put the cast on screen
**Addresses:** S8
**Effort:** medium (needs art)

Mara, Vint, and Kael should interrupt unprompted, carry visible arcs, and react to
each other. The relationship web is already wired (`docs/CAST_BIBLE.md`,
`data/cast.json`); the player-facing surface is a percentage bar in the right
sidebar. Portraits plus a "what they want from you right now" line converts numbers
into people.

### A5 -- Achievements you already wrote
**Addresses:** S9
**Effort:** small

`RUN_MEMORY_LINES` (`engine/resolver.py:396-428`) is 31 flag-keyed past-tense
lines. That is a ready-made achievement list. Add the 14 endings and you have 45
achievements with zero new design work.

---

## 4. Steam shipping checklist

| Item | Status | Note |
|---|---|---|
| Settings menu (volume sliders, text size, reduced motion) | Not started | **blocking** |
| Content warning screen | Not started | **blocking** -- addiction, overdose, involuntary commitment |
| Manual save slots | Not started | **blocking** -- autosave-only today |
| Steam achievements | Not started | A5 makes this nearly free |
| Steam Cloud (for `saves/legacy.json`) | Not started | NG+ depends on it |
| Controller / Steam Deck verification | Not started | |
| Capsule art, trailer, 5+ screenshots | Not started | |
| Scene art (12+ minimum, plus per-ending art) | 6 images | |
| Localization scaffolding | Not started | Strings live in 24 JSON packs -- cheap now, expensive later |
| Windows build | Done | `dist/GreyUtopia.exe` via `grey_utopia.spec` |

**Reduced motion is not optional.** `web/styles.css` runs a full-screen CRT
overlay and a `glitch-text` animation on the title. Shipping without a toggle is an
accessibility failure that will surface in reviews.

---

## 5. Positioning

Category comps: Citizen Sleeper ($20), Cultist Simulator ($20), Roadwarden ($20),
Sunless Sea ($19).

- **As-is:** an $8-12 game. Very good writing, invisible-to-players systems depth,
  one verb, thin presentation. Reviews as "great prose, repetitive."
- **With A1 + A3 + F1:** a $15-20 game and a legitimate category pick, because it
  would have a mechanical identity to match the writing.

---

## 6. Recommended sequencing

1. **F1 + F2** -- one weekend. Surfaces ~20% more content and stops the dice from
   lying.
2. **A1 (the map)** -- the big build. Retroactively fixes S2, S3, S7, S8.
3. **A3 + A4** -- makes the world feel inhabited rather than simulated.
4. **Shipping block** -- settings, saves, achievements, content warning, art.
5. **F3 / F4** -- economy and stat pass. Best done *after* the map exists, since
   districts change the shape of both.

---

## 7. Standing caveat

F1, F3, and F4 are all balance changes. `docs/`-adjacent memory
(`grey-utopia-balance-levers`) records that this deck's levers are non-monotonic
and chaotic: changes to guaranteed-chain content and to pool composition collapse
bot strategies in ways that do not compose additively. Run
`python tests/pargate.py` after each, and do not chase sub-point gate overages --
see the `feedback_balance_perfectionism` memory.

**The core insight to carry forward:** the systems are deeper than players can
perceive, and the content is broader than the selector will show. Both are fixable
without writing another word of prose.
