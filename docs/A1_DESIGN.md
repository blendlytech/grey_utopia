# A1 -- The Row as a Map: design note (Phase 1)

**Written:** 2026-07-27, Opus 5, in-session
**Status:** design + one measured proof-of-concept. **No deck migration in this window.**
**Reads:** `docs/STEAM_READINESS_BACKLOG.md` A1, `docs/BACKLOG_HANDOFF.md` §3 (F1, F2) and §4.

This note answers the five open design questions the backlog flagged as blocking,
then records what the proof-of-concept measured against them. Where a measurement
contradicted the design as first written, the measurement wins and the change is
called out.

---

## 0. What the proof-of-concept had to prove, and the number it aimed at

F1 established that unreached content is *gated*, not out-competed, for 50 of 54
unreached non-legacy storylets -- and therefore that no pool-composition lever can
reach them. That result is easy to over-read into "draw competition is not a
problem at all." It is a problem; it is just a problem for a *different* set of
events, and the ambitions chain is the clearest case in the deck.

Measured at n=40, seed 0, random play (the `coverage_audit` configuration), before
any change in this window:

| `amb_the_choosing` (the ambitions entry point) | Value |
|---|---|
| Runs where it was ever **eligible** | **40 / 40** |
| Runs where it actually **fired** | **19 / 40** |
| Draws it sat in the eligible pool and lost | **2290** (of 4244 total draws in the audit) |
| Median share of a draw's total weight | **0.789%** |

This event is gated on `day >= 6` and nothing else. It is eligible in every run,
for more than half of every draw in the audit, and it loses **2271 of 2290 draws**.
It is not hidden. It is drowned.

That matters far beyond one event, because `amb_the_choosing` is a `max_fires: 1`
fork that grants exactly one of `ambition_clean_name` / `ambition_the_signal` /
`ambition_second_door`, and each of those opens a 6-8 link chain in which **every
choice on every link grants the next thread flag unconditionally**. There is no
skill check and no way to fail out. The ambitions pack's 23 downstream events are
therefore gated behind precisely two things: winning enough draws, and living long
enough to clear the day gates. Nothing else.

So 21 of 40 runs never receive *any* ambition, and the 19 that do split three ways
-- which is why 18 of 24 ambitions events never fire, and why 9 of them were never
once eligible across 40 complete runs.

By contrast, `betrayal_pack` -- the other candidate the handoff named -- is the
opposite shape and was rejected for the proof-of-concept on the measurement:

| `betrayal_pack`, n=40 | Value |
|---|---|
| Events never eligible in any run | **16 / 30** |
| Events eligible but never fired | 4 / 30 |
| Events eligible and firing | 10 / 30 |

Its 30 `twist_*` events are single-shot consequences, each gated behind one flag
granted somewhere else in the deck plus a day gate. Over half were never eligible
at all, which is F1's finding exactly: a shelf cannot help them, because they are
not losing draws. The three that are broadly eligible (`twist_mara_reads_the_dossier`
39/40 fires, `twist_vint_sold_the_question` 31/40, `twist_model_citizen` 23/40) are
already healthy. **`betrayal_pack` is a gating problem; `ambitions_pack` is a
competition problem.** A1 is a fix for the second, so the proof-of-concept runs on
`ambitions_pack`.

---

## 1. Schema -- how an event declares its district

**Decision: an optional top-level `"district"` string on the event. Absent means
district-neutral, and neutral behaves exactly as today.**

```json
{
  "id": "amb_the_choosing",
  "district": "the_archive",
  "...": "..."
}
```

- `engine/events.py` gains `district: Optional[str] = None` on `Event` and reads
  `e.get("district")` in `load_events`. Nothing else in the schema changes.
- **Absent = neutral = today's behaviour**, and that is the whole migration story.
  An unmigrated event is indistinguishable from its pre-A1 self, so the deck can be
  migrated a pack at a time and shipped at any point in between. This is the single
  most important property of the schema choice and the reason not to make the field
  required with an explicit `"district": "global"` sentinel: 483 events would have
  to be touched before anything could ship.
- The district registry is `data/districts.json` (`id`, `name`, `blurb`), so
  district ids are checkable rather than free text.
- `pipeline/lint_content.py` errors on an event declaring a district that the
  registry does not define. Typos in a district id would otherwise create a silent
  orphan shelf that no placement can ever reach -- the exact failure mode F1's
  audit spent a window diagnosing in a different form.

Rejected: districts as a tag (`"tags": ["district:the_archive"]`). Tags are already
overloaded for weighting (`steward`, `existential`, `vice`, `family` all multiply
weight in `effective_weight`) and for the ambient partition. A district is a
partition key with exactly-one semantics; a tag list cannot express that, and lint
cannot enforce it.

---

## 2. Selector integration -- how a placement becomes a filter

**Decision: `district` becomes a fourth filter dimension in `eligible_pool()`,
reusing `ambient_budget_for`'s shape (a helper that returns the per-slot value, so
the on/off switch lives in exactly one place) but not its function.**

```python
eligible_pool(events, character, day, exclude_ids, ambient_budget, district=None)
```

Semantics, in order:

1. Build the pool as today (exclusions, `Event.eligible`, ambient budget).
2. If `district is None` -- the slot was not placed anywhere -- **do not filter**.
   A districted event stays drawable from an unplaced slot.
3. If `district == D`, return the **shelf**: events with `district == D`, plus
   (when `SHELF_INCLUDES_AMBIENT` is on) the district-neutral ambient events.
4. **If the shelf is empty, return the unfiltered pool.** Same discipline and the
   same reason as F1's ambient-budget fallback: returning nothing silently burns
   the player's action slot. A district whose chain is exhausted or day-gated
   must degrade into the general deck, not into a dead slot.

**Step 2 is deliberately the permissive reading, and it was the stricter one when
this note was first drafted.** Exclusivity -- a district's content being invisible
from outside it -- is the more evocative design and is what "the Row as a map"
sounds like. It was rejected on a footgun found while wiring it: with
`PROTOTYPE_DISTRICT = None` shipped and 24 events carrying `"district"`, exclusive
semantics make those 24 events **unreachable in the shipped game**, silently. The
same hazard runs for the length of the migration, when most of the map does not
exist yet and "neutral" mostly means "not migrated." And it buys nothing measurable:
hiding a storylet from the other two slots cannot help it win the one it is
reserved on. Revisit in Phase 3, once every event has a home and neutral means
ambient rather than unmigrated.

The placement itself is `district_for_slot(slot_index)`, the direct analogue of
`ambient_budget_for(ambient_today)`: the three day loops (`main.py`, `server.py`,
`tests/sim_bot.py`) call it unconditionally and the enable/disable switch is one
module constant. Shipped state is `PROTOTYPE_DISTRICT = None`, under which every
slot is unplaced, every event is neutral, and behaviour is byte-identical to
pre-A1.

**Step 3 is the load-bearing decision, and it is worth being blunt about why.** A
shelf that merely *adds* its events to the general pool cannot help anything -- 24
ambitions events joining 459 others land back at their 0.789% share. A shelf that
merely *hides* district events from other slots is worse than useless: it removes
draws without adding any. **The improvement can only come from the placed draw
sampling the shelf in preference to the general deck.** "The Row as a map" is not
a filter; it is a reservation. Any future variant of this design that softens
step 3 into a weighting nudge should expect to measure nothing, and §5 of the
handoff should be updated if someone tries.

### The vending-machine hazard -- and the cure that did not work

A shelf holding *only* a sequential chain is a vending machine: the chain is
day-gated to at most one or two eligible links at a time, so a placement fires the
next link ~100% of the time and the district has no texture. That is a strictly
worse game than the one we have, however good the coverage numbers look. The
measured 100.0% win rate in §6 confirms the hazard is real, not theoretical.

**The obvious cure was measured and rejected.** `SHELF_INCLUDES_AMBIENT` was
drafted as On, on the design argument that ambient filler is the city and the city
is everywhere -- arc content has a home, a rain-slicked vent grate does not -- so a
placement should draw the district's own content *plus* the ~88 neutral
ambient/micro storylets. The argument is sound and the implementation is worse than
the disease: 24 shelf events against 88 ambient means the ambient wins nearly every
placed draw, so a third of the game becomes filler. §6 has the numbers. It ships
Off.

**What actually fixes it is visit cadence.** A player does not stand in one
district every single day; at one placement every five days the chain advances
steadily at a 10.5% win rate on eligible draws, and the deck-wide figures come out
*ahead* of baseline instead of behind. The lever is how often you go, not what else
is on the shelf. This is the single most transferable finding in the window and it
is what Phase 2's placement UI has to be built around.

Cadence deliberately does **not** live in `engine/selector.py`. It is not the
engine's decision -- in the finished A1 the player picks where to stand each
morning -- so it lives in the audit harness (`--district-every`) as a stand-in for
player behaviour, exactly as `--ambient-slots` stands in for the quota.

---

## 3. Heat -- global aggregate stays, district Heat is a new layer

**Decision: global `Heat` is not replaced. It stays exactly as it is, and
per-district Heat is added underneath it as a new layer, with global Heat
redefined as a derived aggregate over districts once districts exist.**

The backlog flagged this as "the single riskiest sub-decision here." It is, and the
read-site census is why. `Heat` is read in **9 engine sites and 847 content sites**:

| Site | What it does |
|---|---|
| `engine/stats.py:14` | stat spec, `(0, 100, 0)` |
| `engine/decay.py:173` | `W_HEAT` term in `compute_daily_stress` |
| `engine/decay.py:295` | `K_COOL = 4.0` per quiet day |
| `engine/resolver.py:257` | `REST_DELTAS["Heat"] = -2.0` |
| `engine/resolver.py:311` | `check_endings`' clean-and-quiet branch, `Heat <= 15.0` -- gates `TERMINAL_institutionalized` **and** `NEUTRAL_the_long_grey` |
| `engine/selector.py:138` | `steward`-tagged events scale weight by `1 + Heat/40` |
| `engine/ambient.py:27,65` | HUD / morning-report surfacing |
| content | **39** preconditions (39 distinct events), **88** probability mods, **720** deltas |

A silent split would have to re-audit all 847 content sites to decide, for each one,
whether "Heat" now means "here" or "everywhere" -- and the 720 deltas are the
dangerous half, because a delta written as "this raises your Heat" would have to be
re-read as "this raises your Heat *in the district you did it in*," which is
usually right but not always (a Steward filing follows you). That is not a
mechanical sweep; it is 847 judgment calls, and it would land in the same window as
a selector rework.

So:

- **Phase 2-3 (migration):** `Heat` keeps its current meaning and every read site
  keeps working untouched. Districts carry no Heat yet.
- **Phase 4 (spatial Heat):** add `character.district_heat: Dict[str, float]`.
  Content deltas keep writing global Heat *and* additionally credit the district
  the slot was placed in. Global Heat becomes `max(district_heat.values())` blended
  with a decayed global term -- **max, not mean**, because "the Row knows your
  face" should not be launderable by spending a week in the Terraces, and because
  the `Heat <= 15.0` ending clause must stay hard to satisfy accidentally.
- **The `Heat <= 15.0` clause in `check_endings` is the one site that must be
  hand-decided rather than derived**, since two endings hang off it. Flag it in the
  Phase 4 window's spec explicitly.
- `K_COOL` becomes per-district: districts you are not working cool down, which is
  what makes "work the Terraces this week" a real play rather than a flavour line.

This ordering means no window ever changes the map and the Heat model at the same
time, which is the rule that made F1 and F2 attributable.

---

## 4. Travel cost -- placements are free, presence is what costs

**Decision: moving between districts does not consume a slot. Each of the day's 3
slots is placed independently and freely; the cost is that a district you are not
in is a district whose shelf you are not drawing from, and whose clocks keep
running.**

Reasoning:

- A travel cost that consumes a slot means a 3-slot day spent in two districts is
  really a 2-slot day. Slots are already the scarcest resource in the game and are
  cut to 2 whenever `Physical_Integrity < 30` or `Mental_Decay > 80` -- exactly
  when a player most needs to reach a specific chain. Taxing movement would make
  the map hurt hardest at the moment it is most needed.
- The opportunity cost is already real without a tax: three placements across 6-8
  districts means at least 3 districts get nothing each day, their Heat does not
  cool if `K_COOL` goes per-district, and their day-gated chain links tick past.
  That is a sufficient decision.
- **The interaction to note and not resolve here:** F3 (money as a decision) wants
  a credit cost on movement, and A2 (preparation as an action) wants a slot to buy
  setup. Both would land on this mechanism. If F3 ships a transit fare, travel
  becomes a *money* cost rather than a *slot* cost, which is compatible with this
  decision and probably better than either alone. **Do not resolve F3's or A2's
  half here** -- record that a fare is the natural place for them to meet and let
  those windows decide.

What *should* gate reachability instead of a travel tax: a district being **closed**
(Heat too high, a flag not yet earned, a curfew clock running). That is a
content-authored precondition on the district registry entry, costs no slots, and
reads in-fiction as the city closing a door rather than as a menu tax.

---

## 5. Migration phasing

Ordered by measured need, not by size:

| Phase | Scope | Why here |
|---|---|---|
| 1 (**this window**) | Schema, selector filter, lint check, one prototype district on `ambitions_pack` | Prove the mechanism before 483 events depend on it |
| 2 | `ambitions_pack` (24) fully + `npc_arcs_pack` (12/17 unreached) | Both are competition-shaped; npc_arcs is the next-largest chain pack |
| 3 | District registry filled to 6-8, `sonnet_5_volume_pack` (185) distributed as district texture | Texture first, so shelves are inhabited before more chains land on them |
| 4 | Spatial Heat (§3), `K_COOL` per district | Only after every district has content to make Heat mean something |
| 5 | `cast_expansion_pack`, `reckoning_pack`, `resistance_pack`, `horizon_pack` | Mixed shape; needs per-event judgment |
| never | `betrayal_pack`, `legacy_pack` | Measured gating-shaped, not competition-shaped (§0). Districts will not help them; **shortening their flag chains will.** Route to a separate item. |

**Correction to the handoff's recommendation.** §4 of `BACKLOG_HANDOFF.md`
suggested starting with the three packs F1 named as reachability-starved --
`betrayal_pack` (19/30 unreached), `ambitions_pack` (18/24), `npc_arcs_pack`
(12/17) -- "rather than the already-healthy `sonnet_5_volume_pack` (7/185)."
The unreached *counts* do not distinguish the two failure modes, and the
eligible-vs-fired split in §0 does: **`betrayal_pack` should not be migrated at
all**, and `sonnet_5_volume_pack` should be migrated relatively early, not last,
because its 185 healthy events are the only source of district *texture* large
enough to keep 6-8 shelves from being vending machines. Migrating chains before
texture would ship the vending-machine failure at scale.

---

## 6. Proof-of-concept result

One prototype district, `the_archive`, holding the 24 `ambitions_pack` events. All
runs n=40, seed 0, random play -- the recorded baseline's exact configuration.

```bash
python tests/coverage_audit.py --district the_archive --district-slots 1 \
    --district-every 5 --track-district the_archive
```

**The chain.** Tracked by district membership, not id prefix: `amb_` also matches
42 unrelated volume ambients, which silently inflated the first measurement taken.

| `the_archive` shelf (24 events) | Baseline | 1 slot/day | +all ambient | every 3d | **every 5d** |
|---|---|---|---|---|---|
| Events ever fired | 6/24 | 19/24 | 16/24 | 23/24 | **23/24** |
| Runs where any fired | 19/40 | 40/40 | 27/40 | 40/40 | **40/40** |
| Times picked | 26 | 155 | 61 | 177 | **173** |
| Median share of eligible draws | 0.84% | 100% | 1.15% | 2.09% | **1.40%** |
| Win rate on eligible draws | 0.8% | **100.0%** | 2.7% | 19.5% | **10.5%** |

**The rest of the deck**, which is what decides whether any of the above is worth
having:

| Deck-wide | Baseline | 1 slot/day | +all ambient | every 3d | **every 5d** |
|---|---|---|---|---|---|
| Events never fired | 103 | 118 | 134 | 93 | **83** |
| Median eligible pool | 209 | 207 | **74** | 209 | **208** |
| Arc draw-share | 24.7% | 24.4% | 19.3% | 24.4% | **24.5%** |
| Ambient share of picks | 21.3% | 20.2% | **45.7%** | 20.3% | **19.6%** |
| Unique events per run | 88 | 82 | 69 | 88 | **98** |
| Median run length | 34 d | 31 d | 26 d | 34 d | **38 d** |

Four things follow.

1. **The mechanism is causal and the effect is large.** `amb_the_choosing` goes
   from firing in 19/40 runs to 40/40, and the chain behind it from 6 reachable
   events to 23. Nothing else changed -- same seeds, same deck, same weights. The
   reservation is doing the work.
2. **Every-day placement is the vending machine, exactly as predicted.** A 100.0%
   win rate on eligible draws is not a game. It also *costs* content elsewhere
   (+15 never-fired), because a third of every day is spent on a 24-event shelf.
3. **Diluting the shelf with all neutral ambient is the worst option tested**, and
   it was the design's first choice. It halves the chain's benefit *and* triples
   the deck-wide damage: the median eligible pool collapses 209 -> 74 and ambient
   takes 45.7% of picks. Rejected on the measurement; `SHELF_INCLUDES_AMBIENT`
   ships Off.
4. **Cadence is the real lever, and at every-5 the deck-wide numbers get better,
   not worse.** Never-fired 103 -> 83 is a 20-event improvement -- roughly 17 of it
   the ambitions chain itself, the rest from runs lasting 34 -> 38 days. Arc
   draw-share holds flat at 24.5% and ambient picks fall slightly. This is the
   first lever in three windows to move never-fired downward at all; F1's quota
   moved it the wrong way and F2 was coverage-neutral.

**Not shipped enabled.** `PROTOTYPE_DISTRICT = None`, so the shipped game is
byte-identical to pre-A1 -- verified by `coverage_audit` reproducing 103
never-fired / 24.7% arc-share exactly and by 3/3 sim_bot parity. Two reasons, both
disqualifying on their own:

- **The every-5 result is not a mechanic yet.** The cadence lives in the audit
  harness because it is a stand-in for a player choosing where to stand. Shipping
  it would mean the engine silently picking a district on a fixed timer, which is
  not the design -- it is the design's *measurement rig*.
- **The +4 median days at every-5 is a balance change** and would need its own
  `pargate`. Gating the every-1 config instead would gate the vending machine.

Phase 2 builds the placement UI and re-runs both gates against real placement.
