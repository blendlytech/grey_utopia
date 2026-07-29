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
> **CORRECTED 2026-07-27 (F1 window), measured by `tests/coverage_audit.py`.** The
> conclusion holds but the cause below is wrong. `ambient`+`micro` is only **20.8%**
> of eligible draw weight; arc is 24.6%; the untagged middle (`job`, `undercity`,
> `existential`, `steward`, `vice`, `family`, `vendor`) is **55.8%**. Budgeting
> ambient therefore redistributes ~2.3:1 into that middle, and arc draw-share is
> capped near 30.6% even by a total ambient ban. Also note only 16 events in the
> whole deck have no preconditions -- "~150 always-eligible ambient events" below is
> not accurate. See §3 of `BACKLOG_HANDOFF.md` for the full F1 result.
Median eligible pool 207/day; only 22.5% of draw weight reaches arc/NPC/relationship
content. `DEPTH_SCALE ** depth` (`engine/selector.py:115`) boosts chain
*continuations* but cannot help a chain's **first link**, which competes flat
against ~150 always-eligible ambient events. Median weights are actually sane
(ambient 4.0, arc 8.0) -- this is a *volume and eligibility* problem, not a
weight problem.

### S3 -- ~20% of written content is unreachable

> **CORRECTED 2026-07-27 (F1 window).** The count is right but N-dependent -- 97 at
> n=40, 69 at n=100 -- so it must always be quoted with its run count. More
> importantly, this is an **eligibility** problem, not a selection one: 50 of the 54
> unreached non-legacy storylets are gated behind a flag only another storylet can
> grant, so they never enter the pool and no weighting change can reach them. The
> real levers are shorter chains, earlier first-link flags, or A1's district shelves.
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

### F1 -- Per-day ambient quota  *(CLOSED 2026-07-27 -- premise disproved)*
**Addresses:** S2, S3
**Effort:** ~1 weekend. Highest impact-to-effort ratio in this document.

> **Built, measured, and shipped disabled.** The quota works exactly as specified
> and misses every acceptance criterion below, because the tag set it budgets is
> only 20.8% of draw weight (see the S2 correction) and because unreached content is
> gated, not out-competed (see the S3 correction). It also cost a balance gate --
> reckless terminal rate fell to 21.8%, under sim_bot's 25% floor. The mechanism is
> retained in `engine/selector.py` behind `AMBIENT_SLOTS_PER_DAY = None` because it
> is the right shape for budgeting A1's district shelves. Full result and numbers:
> §3 of `BACKLOG_HANDOFF.md`. **Do not re-open without reading that entry.**

Cap ambient/micro-tagged events at 1 of the 3 daily slots. Implementation lives in
`engine/selector.py` -- `select_event` already receives `exclude_ids`; add an
analogous per-day tag budget threaded from the day loop in `main.py` and
`server.py`.

**Acceptance:** re-run the 40-run coverage harness; unreached count should fall
well below 100, and arc draw-share should rise above 22.5%. Then re-run
`python tests/pargate.py` -- this is a balance change, so gates must still pass.

### F2 -- Kill the fake dice  *(CLOSED 2026-07-27)*
**Addresses:** S1 (partially), player-trust
**Effort:** small

> **Closed.** The 498-choice sub-item was already handled before this item was
> written (the F1 window found the roll-suppression already in place). The real
> defect was the other 123: `guaranteed` was defined in `engine/resolver.py` as
> `p >= P_MAX` (a probability threshold) rather than "no reachable failure
> branch," so 123 choices with a live failure branch were presented as certain
> and still failed ~2% of the time. Fixed by redefining the flag as `not
> choice.failure`, then resolving all 123 by hand: 101 had a failure branch that
> was textually identical to (or entirely absent from) the success branch and
> were deleted; 22 had a genuinely distinct consequence and were committed to as
> real gambles (`prob.base` lowered to 0.80-0.90). `pipeline/lint_content.py`
> gained a `--report-dice` mode and a standing WARN check so this defect
> re-entering the deck (e.g. via a future Sonnet 5 / Gemini 3.1 Pro volume batch)
> surfaces on the next lint run. Full numbers, the two-sub-defect correction, and
> the verified `pargate` result: `BACKLOG_HANDOFF.md` §3/§4.

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

### A1 -- The Row as a map  *(the big one)*  *(Phase 3 BLOCKED 2026-07-28 -- map built, both gates red)*
**Addresses:** S1, S2, S3, S7, S8
**Effort:** ~6-8 weeks

> **Phase 3 correction, 2026-07-28 -- read this before the Phase 1-2 summary
> below, which two of its claims no longer support.**
>
> The map is at 7 districts and 317 shelved events, and it ships with
> `coverage_audit --assert` red (107 never-fired vs a gate of 85) and `pargate`
> red (reckless terminal 19.6% against a 25-35% band). `docs/A1_DESIGN.md` §8 is
> the full account; `BACKLOG_HANDOFF.md` §4 is the task that unblocks it.
>
> **"6-8 districts lands near the every-5 cadence" below is wrong**, and it was
> wrong in a way that deleted a player option: the formula it describes
> (`min(1.0, len(districts)/5)`) saturates at five districts, so at seven it
> reserved a slot *every day* and made "stay in the Row" unreachable. Replaced
> with a flat `PLACEMENT_RATE`.
>
> **"Phase 3 gets that by writing districts, not by tuning anything" is also
> wrong.** Adding districts is free, but adding shelved *content* is not: a
> shelf's value is `deck_eligible / (n_districts x shelf_eligible)`, the district
> count cancels, and only the total shelved count matters. Phase 2's map was
> worth +22 events deck-wide on 88 shelved; Phase 3's is worth **-9** on 317.
> **The `>= 300 events shelved` target is retired** (§8.3).
>
> Two positions below are now settled *harder* by Phase 3, not softened:
> exclusivity is dead on measurement (never-fired 107 -> 212), and §7.7's warning
> came true -- but inverted and larger. Shelves of pure thread content are a risk
> *discount*, because thread content is where the deck keeps its wins while the
> untagged middle keeps its deaths. The deck has only 17 dose-bearing and 15
> clock-bearing storylets in total, which is the real ceiling on how many
> districts can carry the city's lethality.

> **Phase 1 proved the mechanism; Phase 2 shipped it.** Design decisions and all
> Phase 2 findings are in `docs/A1_DESIGN.md` (§7 for Phase 2); numbers are in
> `BACKLOG_HANDOFF.md` §3 and §6. There is now a morning placement step in both
> UIs, two districts, and 77 shelved events. Headline: **`ambitions_pack` went
> from 18/24 unreached to 5/24 and `cast_expansion_pack` from 9/35 to 4/35**, and
> deck-wide never-fired from 103 to **79** -- 22 of those against a same-RNG-stream
> control, so the map is doing the work. Both shelves sit well short of the 100%
> win rate a bare shelf produces.
>
> **Cadence is no longer a knob.** The automated stand-in places one slot,
> uniformly over the districts plus "stay in the Row", so how often a district is
> visited falls out of how big the map is -- 6-8 districts lands near the every-5
> cadence Phase 1 measured as best. Phase 3 gets that by writing districts, not by
> tuning anything.
>
> Four design positions are settled by measurement and one by a footgun, and
> **none should be re-opened without reading `A1_DESIGN.md` first**: shelves do
> **not** carry the general ambient pool (209 -> 74 eligible pool, 45.7% of picks);
> texture is hand-sized per district, not global (dilution is steep and
> non-monotonic -- §7.3); districts are **not** exclusive until "neutral" stops
> meaning "unmigrated"; and `betrayal_pack` **and `npc_arcs_pack`** are never
> migrated -- both are *gating*-shaped (npc_arcs: 7/17 ever eligible, and in 23 of
> 40 runs not one of its events entered a pool), which no shelf can reach.
>
> Two measurement caveats worth carrying. **Placement changes RNG consumption**,
> so any A/B here needs `coverage_audit --placement control` (same draws spent,
> map off) rather than a no-placement run -- and a control is only valid for the
> policy it was measured under. **And a district shelf is a safer place to stand
> than the open deck**: the first live `pargate` failed four assertions because
> the shelves were stocked with gentle content, which no coverage metric can see.
> A1_DESIGN §7.7 has the diagnosis; Phase 3 must not repeat it at scale.

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

1. ~~**F1 + F2** -- one weekend. Surfaces ~20% more content and stops the dice from
   lying.~~ **F1 closed 2026-07-27 without surfacing content** -- the selector was
   never what was hiding it. **F2 closed 2026-07-27**, independently of F1: 0/1468
   choices now presented as certain that can still fail.
2. **A1 (the map) -- Phase 1 DONE 2026-07-27, Phase 2 next.** The big build.
   Retroactively fixes S2, S3, S7, S8. **F1's result promoted this from "the big
   one" to the only structural fix on the list for S2/S3, and Phase 1 confirmed
   it**: giving a chain its own district shelf took it from 6/24 events reachable
   to 23/24 and moved deck-wide never-fired 103 -> 83. The per-shelf reservation
   mechanism F1 left behind in `engine/selector.py` was indeed the hook it needed.
   Phase 2 turns the winning visit cadence into a real player choice.
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
