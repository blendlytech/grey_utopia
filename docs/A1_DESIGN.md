# A1 -- The Row as a Map: design note (Phases 1-3)

**Written:** 2026-07-27, Opus 5, in-session. **§8 added 2026-07-28 (Phase 3).**
**Status:** design and proof-of-concept (Phase 1), placement shipped live (Phase 2),
map filled to 7 districts (Phase 3) -- **and Phase 3 ships with both standing gates
red.** §8.8 has the numbers and §8.9 has the two ways out. Do not start Phase 4's
spatial Heat work until that is resolved.
**Reads:** `docs/STEAM_READINESS_BACKLOG.md` A1, `docs/BACKLOG_HANDOFF.md` §3 (F1, F2) and §4.

> **Phase 2 addendum.** §§1-5 below are the Phase 1 design and stand as written
> except where §7 says otherwise. Placement is no longer a harness constant: it is
> a morning step in both UIs, `PROTOTYPE_DISTRICT` is gone, and cadence is an
> emergent property of how many districts exist rather than a `--district-every`
> flag. §7 records what Phase 2 measured, including the two places the Phase 1
> write-up was over-read.

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

---

## 7. Phase 2 -- placement as a player choice (2026-07-27, Opus 5)

Placement is live. `PROTOTYPE_DISTRICT` and `DISTRICT_SLOTS_PER_DAY` are deleted;
`district_for_slot(character, slot)` reads what the morning step recorded, the
state rides on `Character` (so `server.py` gets save/load for free), and
`engine/districts.py` holds the registry, the placement writers and the one
stand-in policy every automated caller shares.

### 7.1 Cadence is not a knob any more -- it is how big the map is

Phase 1's central finding was that *visit cadence* is the lever, and §2 above
left it in the harness because it stood in for a player. The Phase 2 policy
(`auto_placement`) makes it emergent instead:

> An automated caller places **at most one** slot. *Whether* it goes anywhere is
> `len(districts) / VISIT_INTERVAL_DAYS`, capped at 1; *where* is uniform over
> the map.

`VISIT_INTERVAL_DAYS = 5` is not a free parameter -- it is Phase 1's §6 result,
the only empirically grounded number in this area, and it was measured in a
window with no balance gate riding on it. Per-district cadence is therefore one
visit every five days **regardless of how many districts exist**, and Phase 3
adding districts spreads the same commitment wider rather than demanding more of
it.

**The first cut of this got that backwards, and the bug is worth recording**
because it looked principled. It drew uniformly over `districts + ["stay in the
Row"]`, on the argument that this is exactly how `sim_bot` models a player's
*choices*. But it makes the probability of committing a slot **rise with the size
of the map** -- 50% at one district, 67% at two, 87% at eight -- for no reason
except that the list got longer. How many places exist should not change how
often someone commits their day to one of them, and under that policy Phase 3
would have quietly tripled the fraction of the game spent on shelves. It was
caught by the balance gate (§7.7), not by the coverage audit, which saw nothing
wrong at all.

### 7.2 The measurement that was over-read, and the control mode built to catch it

Placement costs RNG draws, which reshuffles the whole stream. A no-placement run
that *skips* those draws therefore differs from a placed run on two counts, and a
"never-fired 103 -> 79" headline invites reading the whole movement as the map's
doing. `coverage_audit --placement control` draws the placement and discards it,
so the map is the only difference:

| n=40, seed 0, random | pre-a1 (recorded baseline) | control (map off, same stream) | auto (live) |
|---|---|---|---|
| Events never fired | 103 | **101** | **79** |
| `ambitions_pack` unreached | 18/24 | 16/24 | **5/24** |
| `cast_expansion_pack` unreached | 9/35 | 9/35 | **4/35** |
| `betrayal_pack` (never shelved) | 20/30 | 16/30 | 18/30 |
| Median run length | 34 d | 33 d | 34 d |
| Unique events / run | 88 | 84 | 92 |
| Arc draw-share (unplaced) | 24.7% | 25.0% | 26.9% |

**The map is worth 22 events deck-wide on the same stream**, and 11 of the 24
ambitions storylets on its own.

**This table replaces an earlier version of itself, and how it changed is the
warning.** Measured against the §7.1 *pre-fix* policy -- the one that committed a
slot on 67% of days instead of 40% -- the same comparison read control 90 / auto
91, i.e. "the map does nothing deck-wide." That was true of that configuration
and it is not a property of the map: over-placing narrows what a run sees,
because a third of the day is spent on a 15-event shelf instead of a 210-event
deck. The coincidence of 90 and 91 was two different streams landing in the same
place. Two lessons, and the second is the sharper one:

1. Anyone quoting a deck-wide coverage number for a change that alters RNG
   consumption must run `--placement control` first.
2. **A control column is only comparable within one policy.** Changing how many
   draws `auto_placement` spends moves the control too, so a control measured
   before a policy change cannot be reused after it.

### 7.3 Texture is a per-district authoring decision, not a global flag

§2 predicted the vending machine and Phase 1 confirmed it at 100% win rate on
placed draws. Phase 2 measured the cure at five sizes, shelving hand-picked
`sonnet_5_volume_pack` storylets on `the_archive` (n=40, seed 0):

| Texture events | 0 | 6 | 10 | **14** | 16 | 28 |
|---|---|---|---|---|---|---|
| Ambitions win rate on eligible draws | 28.7% | 14.4% | 9.3% | **7.2%** | 7.5% | 4.3% |
| Ambitions events ever fired | 24/24 | 24/24 | 22/24 | **23/24** | 22/24 | 23/24 |
| Runs where the chain fired | 40/40 | 39/40 | 38/40 | **37/40** | 36/40 | 32/40 |
| Deck-wide never fired | 91 | 99 | 91 | **82** | 111 | 99 |

Two things to carry forward. First, **dilution is steep and the deck-wide column
is chaotic** -- 91/99/91/82/111/99 is not a curve, it is the documented
non-monotonic lever, and no size should be chosen on that column alone. Second,
`SHELF_INCLUDES_AMBIENT` is now settled Off rather than deferred: the right amount
of texture is a hand-authored per-district judgment, and a global boolean that
mixes in *all* neutral ambient cannot express it at any setting.

### 7.4 `npc_arcs_pack` is gating-shaped and was not migrated

§4 of the handoff routed `npc_arcs_pack` (12/17 unreached) to Phase 2 as
"competition-shaped". Measured, it is not -- this is the same correction Phase 1
made to `betrayal_pack`, and it is why §5 of the handoff insists ever-eligible be
quoted alongside ever-fired:

| Pack, n=40 | Ever eligible | Ever fired | Runs where any was eligible | Shape |
|---|---|---|---|---|
| `ambitions_pack` | 23/24 | 23/24 | 40/40 | competition |
| `cast_expansion_pack` | **30/35** | 24/35 | 39/40 | **competition** |
| `horizon_pack` | **13/13** | 12/13 | 36/40 | **competition** |
| `reckoning_pack` | 18/25 | 18/25 | 40/40 | mixed |
| `resistance_pack` | 6/12 | 3/12 | 40/40 | mixed |
| `npc_arcs_pack` | **7/17** | 6/17 | **17/40** | **gating** |
| `betrayal_pack` | 14/30 | 10/30 | -- | gating |

`npc_arcs_pack` is gated on `vint_known` / `kael_impressed` / `mara_ransomed` /
`echo_brother_known`, flags granted in other packs, and **in 23 of 40 runs not one
of its events ever became eligible.** A shelf cannot help content that never
enters a pool. It goes to the same place `betrayal_pack` went: the chain-shortening
item, not the map.

`cast_expansion_pack` took its slot, and is the better fit anyway -- Brann's
workshop, Auntie Six's board, Denny's booth and Dex's dispatch line are already
one street. That street is `the_chalk_market`, 25 cast storylets plus 14 volume
stalls. (`the_seam` was the obvious name and is taken: 48 content references use
it for the Ferryman's crossing.)

### 7.5 What the acceptance criteria measured

| Metric | Target | Measured |
|---|---|---|
| Placement is a player choice in `main.py` and `server.py` | built + persisted | morning step in both; `Character.placements` / `last_visited` round-trip through `to_json` |
| `the_archive` win rate on eligible draws | 10-25% | **11.6%** |
| `the_chalk_market` win rate | -- | **14.0%** |
| Ambitions events ever fired | >= 20/24 | **19/24** -- missed by one, see below |
| Deck-wide never fired | <= 95 | **79** |

The ambitions miss is a real one and worth being precise about, because the
diagnosis changes what to do with it. **Four of the five unreached events are
gated at day >= 40, 46, 46 and 52 against a median run of 34 days**
(`amb_signal_6`, `amb_signal_finale`, `amb_second_finale`, `amb_second_8`); the
fifth, `amb_clean_8_the_collectors`, hangs off a failure branch's expired clock.
Every link placement *can* reach now fires, up to and including the day-40
`amb_clean_6`. This is the open thread §5 of the handoff already records -- chain
day-gates calibrated for a run length the game no longer has, the same shape as
"The Rounding is day-55 gated but the median run ends day 58" -- and Phase 1
already concluded **no amount of A1 fixes it.**

What A1 *did* trade away is the difference between Phase 1's 23/24 and this
19/24, and it was traded twice deliberately: texture had to dilute the shelf to
stop the vending machine (§7.3), and the placement rate had to come down to stop
the risk discount (§7.7). **Chain depth, vending-machine avoidance and balance
pull against each other on the same knob**, and the day gates are what make the
third pull expensive. Re-scaling them is the cheapest remaining win in this area
and it is not an A1 task.

Two instrument defects were found and fixed by the placement itself, both the
same mistake: `auto_placement` places slot 0, and the audit recorded "the day's
pool" and "the day's arc share" at slot 0. Both were silently reporting *shelf*
figures -- median pool read 15 instead of 209. They are split by placed/unplaced
now, which also surfaced that **`ARC_TAGS` scores both shelves at 0.0% arc**:
`ambitions_pack` is tagged `existential`/`undercity` and `cast_expansion_pack`
`job`/`undercity`, so the deck's arc classifier cannot see either of the two packs
this item exists to rescue.

### 7.7 A shelf is a safer place to stand, and the balance gate is what caught it

The first full `pargate` on live placement **failed on four assertions**, and the
failure is the most useful thing this window produced:

| n=1000/strategy | Recorded (F2) | First live run |
|---|---|---|
| Cautious terminal | 22.2% | 11.2% |
| Reckless terminal | 27.1% | **16.4%** (band 25-35) |
| Reckless good | 33.4% | **49.2%** (cap 45) |
| Greedy terminal | 16.1% | **9.2%** (band 12-25) |
| Greedy good | 44.4% | **56.9%** (cap 45) |

Isolated against `--placement control` at n=400, run length barely moved (62.6 ->
63.9 days for cautious), so this is **not** a pacing effect. What moved is risk:
reckless terminal 29.8% -> 17.5% and its `GOOD_small_real_things` share 18.5% ->
37.0%, on the same seeds, with the map as the only difference.

The cause is structural, not incidental. **Shelved content is systematically
gentler than the deck it is reserved against**, because a district shelf is made
of character threads and district texture while the city's danger lives in the
untagged middle -- the jobs, the debts, the doses. Scoring every branch by
`sim_bot`'s own utility weights: the shipped shelves averaged **-2.32 against the
neutral deck's -3.10, with a worst case of -14.4 against -19.5.** Reserving a
third of the day for that is a standing risk discount, and because terminal
endings are driven by the *tail* (overdose, the syndicate ledger) rather than the
mean, a 25% reduction in average harm bought a 40% reduction in terminal rate.

Two changes, in this order, and only the first was aimed at the gate:

1. **The placement policy modelling bug in §7.1.** Fixing "probability of
   committing rises with map size" cut the reserved fraction of the day from 0.67
   slots to 0.40 and recovered most of the gap on its own (reckless terminal
   17.5% -> 23.2%, cautious 12.5% -> 19.5%, i.e. above its own control).
2. **The market had no loan shark.** Every dose- and debt-clock-bearing storylet
   in the volume packs is a `volume_vice_market_*` event by name and fiction --
   the loan shark, the fight pit, the organ broker, the fence, the memory-parlour
   debt -- and all 17 were sitting unshelved while `the_chalk_market` carried
   bead-curtain vendors. That was an authoring error independent of balance, and
   fixing it is what puts the city's teeth back on the shelf. Note the branch-
   utility proxy above **cannot see this fix at all**: it scores `dose` at -0.15
   and ignores `clocks_start` entirely, so it still reads the market as gentle.
   The overdose pipeline is where that danger actually lives.

**The finding to carry into Phase 3 is the general one.** Every district added is
a new opportunity to build a safe harbour by accident, and neither
`lint_content.py` nor `coverage_audit.py` can see it -- coverage was *green and
improving* through the whole failure. A shelf must carry its district's share of
the city's danger, not just its stories. Worth a lint check: warn when a shelf's
dose/clock-bearing fraction falls far below the deck's.

**And the deeper one, which this window did not fix.** §4 decided placement is
free because "the districts you are not in" is cost enough. That cost is only
real once districts hold things you actively need; until then placement is a free
risk reduction, and an automated caller taking it at random gets the discount
without ever making the trade. A player can still place *all three* slots in one
district every day, which no policy constant constrains. **If Phase 3's larger map
does not make the opportunity cost bite, A1 needs a real cost** -- which is where
§4 already says F3's transit fare is the natural place for it to land.

### 7.6 Left for Phase 3

- **The registry is 2 of a planned 6-8**, and §7.1 means every district added
  changes every other district's cadence. Expect the numbers here to move on the
  next one; re-measure rather than assuming.
- Exclusive shelves (§2 step 2) stay rejected while "neutral" still means
  "unmigrated". 77 of 483 events have a home.
- Travel cost (§4) remains unmeasured and un-needed: with two districts the
  opportunity cost is already real, and no measurement here argues for a tax.
- Spatial Heat (§3) is still Phase 4 and still must not share a window with a
  selector change.

---

## 8. Phase 3 -- filling the map (2026-07-28, Opus 5)

The registry is 7 districts and 317 of 483 events have a home. **Both standing
gates are red at the shipped configuration**, for one measured reason with one
clear fix, and this section is mostly about that reason because it is the thing
Phase 4 has to act on.

> **Read §8.3 first if you read nothing else.** The value a district shelf
> returns is `deck_eligible / (n_districts x shelf_eligible)`, and because
> `shelf_eligible` grows with how much of the deck is shelved, that ratio
> depends on the *total shelved count* and not on how many districts it is
> spread across. Filling the map does not make the map better. It makes every
> shelf a small deck.

### 8.1 The map

Seven places the deck already believed in, named from the prose rather than
invented. `the_seam` is the Ferryman's crossing (§7.4 recorded that name as
"taken" -- it is taken *by this district*, which is why the market could not
have it); `level_d` is canon in `prologue_pack` and `resistance_pack`.

| id | name | anchor content | events |
|---|---|---|---|
| `the_archive` | The Archive Stacks | `ambitions_pack` 24, `ot_ark_*`, Echo's two library jobs | 35 |
| `the_chalk_market` | The Chalk Market | `cast_expansion_pack` 25, `kael_*` 10, the syndicate/debt half of `reckoning_pack` | 60 |
| `parlor_row` | Parlor Row | the synth/overdose flagships, `ot_chm_*`, `ot_pit_*`, the vice half of `reckoning_pack` | 36 |
| `the_seam` | The Seam | `second_ferryman_pack` 7, the offgrid flagships, `cx_ferry_*` | 31 |
| `the_concourse` | The Concourse | `ascension_pack` 10, `fable_reviews_pack`, `the_rounding_pack`, `ot_aud_*` | 52 |
| `the_works` | The Works | the `hz_*` workshop chain, `rel_vint_*` 20, the Mara thread | 72 |
| `level_d` | Level D | `resistance_pack` 9, `echo_*` 10 | 31 |

Deliberately left neutral: `prologue_pack` (day-0 gated -- a shelf is the wrong
place for content that must fire immediately), `legacy_pack` (unreachable by
design), and `betrayal_pack` / `npc_arcs_pack` (measured gating-shaped in §0 and
§7.4; never migrate them).

Note two packs were **split across districts by subject rather than shelved as
units**: `reckoning_pack` is a *time*, not a place -- its syndicate beats went to
the market, its vice beats to Parlor Row, its Steward beats to the Concourse --
and `horizon_pack` split three ways between the bench, the Seam and the
Concourse. Packs are authoring batches; districts are places. They do not have
to agree.

### 8.2 Phase 2's placement formula breaks at a full map, and a unit test caught it

`auto_placement` computed its commitment rate as `min(1.0, len(districts) / 5)`.
That saturates at five districts, and at seven it returns 1.0 -- **so every
single day placed a slot and "stay in the Row at large" became unreachable.**
`tests/test_engine.py` asserts that option is reachable and went red, which is
the only reason this was caught rather than shipped.

It is worth being precise about how a principled-looking formula got here. §7.1
correctly identified the modelling bug ("how many places exist should not change
how often someone commits their day to one of them") and then *re-introduced it*
by deriving the rate from the map size anyway, in service of holding per-district
cadence at Phase 1's measured every-5. It cannot hold that: one slot spread over
seven districts is one visit per district per seven days no matter what the
formula says. So the formula gave up the Row without buying the thing it gave it
up for.

Replaced with a flat `PLACEMENT_RATE`, and per-district cadence is now whatever
falls out (`len(districts) / rate` days). **The reserved fraction of the day is
the balance-critical quantity** -- see §8.4 -- so it is now a single number set
against the balance gate rather than an emergent consequence of the registry's
length.

`coverage_audit`'s banner had the matching defect: it printed the *intended*
cadence from the constant rather than the one the policy produces, and so read
"each visited every ~5 days" on a map visiting each district every eighteenth
day. It is derived now.

### 8.3 What a shelf costs, and the ratio that decides whether it pays

A shelved storylet is **not** moved out of the deck -- it keeps competing in
every unplaced draw (§2 step 2, and §8.5). What it gains is a share of the
reserved draws; what it loses is that placement spends slots that would
otherwise have been open-deck draws for *everything*. So:

```
gain per shelved event   ~  reserved_fraction / (n_districts * shelf_eligible)
loss per event in deck   ~  reserved_fraction / deck_eligible
ratio                    ~  deck_eligible / (n_districts * shelf_eligible)
```

The reserved fraction cancels. And since `shelf_eligible` is roughly
`0.45 * shelved / n_districts`, the district count cancels too:

```
ratio  ~  deck_eligible / (0.45 * total_shelved)
```

| | Phase 2 | Phase 3 |
|---|---|---|
| shelved | 88 | 317 |
| districts | 2 | 7 |
| median eligible shelf | 15 | 11 |
| median eligible deck | 209 | 210 |
| **ratio** | **7.0** | **2.7** |
| deck-wide never-fired, live vs its own control | 79 vs 101 | 107 vs 98 |

**Adding districts is free; adding shelved content is not.** A 7-district map at
Phase 2's shelved count would have worked as well as Phase 2 did. The `>= 300`
acceptance criterion is the thing that broke this window, and it should be
retired rather than carried into Phase 4.

### 8.4 Texture is load-bearing for *balance*, and the vending machine was a cadence effect

Two results that only make sense together.

**Bare shelves are the best coverage this project has ever measured.** Stripping
every non-arc storylet off the map (229 shelved, all thread content) scored 69
never-fired and `ambitions_pack` 2/24 unreached, against Phase 2's 79 and 5/24 --
at seven districts. The texture curve, n=40 seed 0:

| shelved | 229 | 259 | 289 | 319 | 348 |
|---|---|---|---|---|---|
| never fired | **69** | 88 | 83 | 88 | 101 |
| ambitions unreached | **2/24** | 5/24 | 6/24 | 9/24 | 3/24 |
| median eligible shelf | 8 | 8 | 12 | 16 | 22 |

Always-eligible ambient texture is what makes a shelf expensive: it is in the
pool on *every* placed draw, where day- and flag-gated arc content mostly is not.
Note the middle of that curve is not a curve -- it is the documented
non-monotonic lever, and §8.7 shows the noise band is wide enough to eat most of
it.

**And bare shelves broke five balance assertions**, which is why they are not
shipped:

| n=1000/strategy | Phase 2 (recorded) | bare shelves, every day |
|---|---|---|
| Reckless terminal | 27.7% (band 25-35) | **3.5%** |
| Greedy terminal | 15.6% (band 12-25) | **0.4%** |
| Reckless good | 37.4% (cap 45) | **53.5%** |
| Greedy good | 43.4% (cap 45) | **55.8%** |

The mechanism is the mirror of §7.7 and sharper. §7.7 found shelves were gentler
than the deck on *stat deltas*. This is bigger than that: **thread content is
where this deck keeps its wins, and the untagged middle is where it keeps its
deaths.** Terminal endings come from the overdose pipeline and the syndicate
ledger, which live in the jobs and the doses; reserving a third of every day for
thread content reserves it for *winning*. Arc took 68% of all picks against 25%
shipped. A shelf of pure story is not a hard place to stand, however harsh its
individual branches read.

So texture is not decoration and not a vending-machine cure. It is what keeps a
reserved draw representative of the city rather than of the plot.

**The vending machine itself turns out to be a property of cadence, not of bare
shelves.** Phase 1 measured a 100% win rate on placed draws with one district
visited *every day*. At seven districts, bare shelves win 8.7-23.5% of their
eligible draws -- inside or below the 10-25% guard and never above it. The guard
was never in danger here; the thing to watch at a full map is the opposite end.

### 8.5 Exclusivity: measured, and rejected for good

§2 rejected exclusive shelves on a footgun (with most of the deck unmigrated,
"neutral" meant "not yet placed", so hiding districted content would orphan it)
and deferred the real decision to this phase. That objection has expired. The
replacement is arithmetic and much stronger, measured at n=40 seed 0 on the
shipped map:

| | non-exclusive | exclusive |
|---|---|---|
| events never fired | 107 | **212** |
| median eligible pool | 210 | **81** |
| `ambitions_pack` unreached | 9/24 | **19/24** |
| unique events per run | 88 | **68** |

A district is stood in roughly every eighteenth day. Exclusivity would make those
~2 placed draws per run the *only* route to that district's 30-70 storylets.
Non-exclusive shelves are **additive** -- the reservation is a bonus on top of an
event's normal life in the deck, not a relocation out of it -- and that is the
entire reason the mechanism can lift a drowning first link without costing the
rest of the deck. `SHELF_EXCLUSIVE` exists in `engine/selector.py`, ships Off,
and should stay that way; the switch is kept only so the measurement is
reproducible.

### 8.6 `Event.arc`: the classification two windows were blocked by

§5 of the handoff has twice recorded that `ARC_TAGS` cannot see the packs A1
exists to rescue -- `ambitions_pack` scores 0.0% arc because it is tagged
`existential`/`undercity`. Since `MIN_ARC_SHARE` is a standing gate, shelving
real arc content pushed the gate the *wrong* way.

Fixed with a top-level `arc: true` on the event, applied by pack (and by id
prefix inside the three mixed volume packs, where `rel_vint_*`, `fam_mara_*`,
`kael_*`, `echo_*`, `volume_family_*` and `volume_npc_*` are named-NPC thread
content). It is a boolean rather than a tag **on purpose**: `effective_weight`
multiplies weight off `tags`, so a new tag is a balance change, and a field
cannot be. `coverage_audit.is_arc` takes the union of the field and the old tag
set, so the classifier can only ever see more arc than before, never less.

327 of 483 events are arc. That is higher than the deck's folk wisdom ("filler
outnumbers arc 2:1") because that ratio was about *draw weight* and about the
volume packs; nearly all non-volume content is authored thread content.

`MIN_ARC_SHARE` is **not** re-tightened here, for the same reason Phase 2 gave:
the metric's definition moved under it in this window, and a gate should not be
tightened onto a number whose meaning just changed.

### 8.7 Two instrument findings, and one of them undermines a lot of tuning

**The never-fired gate is noisier than the effects three windows have tuned
against it.** Same deck, same config, n=40, varying only the seed base:

| seed base | 0 | 100 | 200 | 300 | 400 |
|---|---|---|---|---|---|
| events never fired | **107** | **79** | 90 | 88 | 95 |

A 28-event spread, mean 91.8. §6 of the handoff already noted seed sensitivity
(97 / 91 / 111) but the gate is still asserted at a single pinned seed, and the
differences this window and the last two have reasoned from are the same size as
the noise. The texture curve in §8.4 should be read with that in mind: its
endpoints (69 vs 101) are probably real, its middle certainly is not. The balance
gate, at n=1000 per strategy, does not have this problem -- which is why every
conclusion in §8.4 that matters is anchored on `pargate`, not on coverage.

**Only 17 storylets in the whole deck carry a `dose`, and only 15 start a
clock.** That is the content-side reason §8.8 fails, and it is not fixable by
migration -- see below.

### 8.8 Results, against the acceptance criteria

Shipped: 7 districts, 317 shelved, `PLACEMENT_RATE = 0.40` (Phase 2's validated
reserved fraction, so the map is the only variable changed against a green
baseline).

| Metric | Target | Measured |
|---|---|---|
| Districts in the registry | 6-8 | **7**, each with content and a blurb |
| Events with a district | >= 300 | **317** |
| Every shelf's win rate on eligible draws | 10-25% | **5.9-30.7%** -- the Works over, the Seam/Archive/Level D under |
| `ambitions_pack` unreached | <= 4/24 | **9/24** (Phase 2: 5/24) |
| `cast_expansion_pack` unreached | <= 6/35 | **10/35** (Phase 2: 4/35) |
| Deck-wide never-fired | <= 95, gate 85 | **107** at seed 0; 79/90/88/95 at other seed bases |
| `unittest` | pass | **90 passed** |
| `lint_content` | clean | **clean**, 483 events, 317 on 7 shelves, 0 warnings |
| `coverage_audit --parity` | 3/3 | **3/3** |
| `coverage_audit --assert` | green | **RED** -- 107 > 85 |
| `pargate` | green | **RED** -- reckless terminal 19.6% (band 25-35), greedy good 45.6% (cap 45) |

**No configuration tested this window is green on both gates**, and the search
was not shallow:

| shelved | rate | never-fired | ambitions | pargate |
|---|---|---|---|---|
| 253 (bare) | 1.00 | 78 | 1/24 | 5 violations |
| 317 | 0.55 | 81 | 6/24 | 3 violations |
| 317 | 0.40 | 107 | 9/24 | **2 violations** (shipped) |
| *Phase 2: 88* | *0.40* | *79* | *5/24* | *green* |

The last row is the diagnosis. **At the same reserved fraction, Phase 2 scored
reckless terminal 27.7% and Phase 3 scores 19.6%** -- so the residual 8 points
are not the placement rate, they are *which shelves the placements land on*.
Phase 2 had two districts and one of them was the Chalk Market, carrying the loan
shark, the fight pit and the organ broker (§7.7's own fix), so half of all
placements hit the dose/debt pipeline. Phase 3 has seven districts of which
Parlor Row carries the dose and the market carries the clocks, so only ~2 in 7
do.

That is exactly the failure §7.7 predicted for this window -- "every district
added is a new opportunity to build a safe harbour by accident" -- and it is
**not fixable by moving events around**, because there are only 17 dose-bearing
and 15 clock-bearing storylets in the deck and they are fictionally anchored
where they already are. The Works, the Seam, Level D and the Archive carry none
of either:

| shelf | dose% | clock% | mean worst branch |
|---|---|---|---|
| whole deck | 3.5 | 3.1 | -18.6 |
| neutral pool | 1.8 | 2.4 | -14.6 |
| all shelves | 4.4 | 3.5 | -20.7 |
| `parlor_row` | 33.3 | 13.9 | -33.5 |
| `the_chalk_market` | 0.0 | 6.7 | -25.6 |
| `the_archive` | 0.0 | 5.7 | -23.4 |
| `the_concourse` | 3.8 | 0.0 | -18.9 |
| `the_seam` | 0.0 | 0.0 | -23.7 |
| `level_d` | 0.0 | 0.0 | -13.2 |
| `the_works` | 0.0 | 0.0 | -12.4 |

Note the aggregate is *harsher* than the deck on branch utility and still buys a
risk discount, which retires that proxy for good: it scores `dose` at -0.15 and
cannot see `clocks_start` at all, exactly as §7.7 warned.

### 8.9 What Phase 4 has to decide first

The map exists and is good content work; what is unresolved is whether the
mechanism can afford it. In preference order:

1. **Author the missing danger.** Five districts have no dose and no debt clock.
   Roughly 10-15 new storylets -- a Seam crossing that goes wrong and starts a
   ferryman's-debt clock, an arrest clock on Level D, a fronted-parts debt at
   the bench -- would let placement stop being a risk discount without shrinking
   the map. This is authoring, not tuning, and it is the only fix that keeps
   everything this window built.
2. **Or retire the `>= 300` target and shrink the shelves.** §8.3 shows the map's
   value is set by the total shelved count, and §8.4 shows bare shelves measure
   best on coverage by a wide margin. 7 districts holding ~150 events would very
   likely be green on both gates. It costs the "every event has a home" goal,
   which no measurement has ever supported.
3. **Do not** try to fix this by lowering `PLACEMENT_RATE` further. It models the
   automated stand-in, not the player; a human still places every morning, so
   tuning it down hides the discount from the gate without removing it from the
   game.

Still deferred, unchanged: spatial Heat (§3) is Phase 4 proper and must not share
a window with a selector change; travel cost (§4) is still unmeasured, though
§7.7's open question -- whether a larger map makes the opportunity cost bite --
now has a partial answer, since a player who camps in the Works is declining six
other threads.

## 9. Phase 3b -- paying for the map (2026-07-28, Opus 5)

§8.9 offered two branches. This window took **(a), author the missing danger**,
and the reasoning is in `BACKLOG_HANDOFF.md` §5 rather than repeated here. The
short version: (b) strips the untagged middle off the shelves, and §8.4 measured
that the untagged middle is where the deck keeps its deaths -- so (b) fixes the
coverage gate by pushing the *balance* gate, the one that actually blocks, further
into the red.

### 9.1 What was written

`data/events/district_hazards_pack.json`, 14 storylets, deck 483 -> 497 and 317
-> 331 shelved. Every hook is a real pipeline hook, per §8.8's finding that
branch-utility harshness does not predict terminal rates. Where possible the hook
is an **existing** clock with an existing consequence reader, so each new event is
a second entrance to machinery that already terminates rather than a new orphan
flag:

| shelf | dose% before -> after | clock% before -> after | hooks added |
|---|---|---|---|
| `the_works` | 0.0 -> 2.7 | 0.0 -> 1.3 | fronted crate -> `syndicate_consignment` + `holding_product`; shift-tin dose; press-injury ampoule |
| `the_seam` | 0.0 -> 2.9 | 0.0 -> 5.9 | toll on credit -> `loan_shark`; bad crossing -> `syndicate_debt`; cold-water medic dose |
| `level_d` | 0.0 -> 2.9 | 0.0 -> 5.9 | sweep -> `arrest_warrant` -> going under -> `syndicate_consignment`; green-tab dose |
| `the_archive` | 0.0 -> 2.7 | 5.7 -> 8.1 | clean-cut dose; sealed-shelf pull -> `debt_collectors_move` + `debt_collection` |
| `the_concourse` | 3.8 -> 5.6 | 0.0 -> 1.9 | wellness referral -> `wellness_review` -> review-board sedation dose |
| `the_chalk_market` | 0.0 -> 1.6 | 6.7 -> 6.6 | short-weight batch dose |

Only two clocks are new (`arrest_warrant`, `wellness_review`) and each ships with
its reader in the same file. The rest feed `reck_syndicate_deadline`,
`reck_syndicate_debt_collectors`, `reck_loan_shark_interest` and
`amb_clean_8_the_collectors` -- all of which already route to
`flag_syndicate_execution` or to an existing debt spiral.

The Archive pull is worth singling out because it serves both gates at once:
`amb_clean_8_the_collectors` previously had exactly one entrance, gated
`ambition_clean_name` + `day >= 46` against a median run of 33-38 days, which is
most of why it was unreachable. It now has a second at day 14.

### 9.2 A new flag source can delete an existing event, and lint cannot see it

`dgr_works_fronted_crate` sets `holding_product` -- that is the whole point of it,
since `holding_product` is what puts a district on the syndicate ledger.
`flagship_synth_consignment` is gated `none: holding_product`. As first written,
a day-9 weight-11 Works storylet would have made a flagship and the
`syndicate_debt` route beneath it unreachable in most runs: **it would have
removed danger while claiming to add it**, and it would have scored as a coverage
regression with no obvious cause.

Fixed by banding rather than by dropping the flag: the Works crate is gated
`Fame < 20`, the flagship `Fame >= 20`. They are the same offer made to the two
ends of a reputation, which is better fiction than either alone.

The transferable rule: **before shipping an event that sets a flag, grep that flag
in `none:` groups.** `lint_content` checks that every required flag *has* a
source; it has no check that a new source starves an existing consumer, and that
failure mode is silent at runtime.

### 9.3 The coverage regression is the new content, not the map

Never-fired at n=40, five seed bases, both placement modes:

| seed base | 0 | 100 | 200 | 300 | 400 | mean |
|---|---|---|---|---|---|---|
| live (map on) | 114 | 106 | 119 | 113 | 114 | **113.2** |
| control (map off) | 119 | 115 | 141 | 129 | 94 | **119.6** |
| *live, Phase 3* | *107* | *79* | *90* | *88* | *95* | *91.8* |

(Figures are the shipped build. An intermediate build measured 108.6 / 111.2 --
inside the noise band described below, which is the point.)

Two separate readings, and conflating them would misdirect Phase 4.

**The map's value flipped positive.** Live beats its own control by 6.4 events on
the mean, where §6 of the handoff recorded the map at *minus nine* (seed 0 only).
Adding danger to the five bare shelves made the reservation worth taking again --
which is the §8.3 ratio moving for a reason that is not the shelved count.

**The absolute level rose ~21 events, and that is authoring, not placement** --
the control moved further than the live column, and the control has the map
switched off. The cause is visible in one number: median eligible pool 210 -> 221.
Six of the fourteen are `max_fires: 0` behind nothing but a day gate, so from day
5-11 onward they are in *every* draw, forever, and they repeat. This is precisely
§8.4's mechanism -- "always-eligible ambient texture is what makes a shelf
expensive, because it is in the pool on every placed draw where day- and
flag-gated arc content mostly is not" -- reproduced deck-wide instead of
shelf-wide, by the same author who wrote that sentence.

**And a correction to §8.7 that widens its own conclusion.** §8.7 measured the
*level*'s seed noise at 28 events. This window has five paired live/control
measurements of the same configuration, and the live-minus-control *delta* runs
-5, -9, -22, -16, +20 -- a 42-event swing on a quantity whose true value is about
six. The control column alone swings 47 events across seed bases (94 to 141).
So the map's measured value is inside the noise band too, at n=40. That retires
"the map is now worth minus nine events" (§6) as a finding: it was one seed of a
quantity that needs five to say anything. Any future claim about what placement is
worth must be a mean over seed bases or it is not a claim.

### 9.4 The balance gate, over four runs

Branch (a)'s core prediction was §8.8's: that the residual 8 points of reckless
terminal were *which shelves placements land on*, and would come back if those
shelves were given teeth. They did.

| assertion | Phase 3 | run 1 | run 2 | run 3 | **shipped** | band |
|---|---|---|---|---|---|---|
| Reckless terminal | **19.6 ❌** | 30.1 | 36.2 ❌ | 32.8 | **34.6 ✅** | 25-35 |
| Greedy terminal | 14.0 | 9.8 ❌ | 15.0 | 15.6 | **15.4 ✅** | 12-25 |
| Greedy good | **45.6 ❌** | 29.4 | 39.9 | 39.5 | **39.9 ✅** | <= 45 |
| Reckless good | 38.7 | 22.3 | 30.6 | 32.8 | **32.7 ✅** | <= 45 |
| Cautious terminal | ok | ok | 20.4 | 20.4 | **ok ✅** | >= 5 |
| Random institutionalized | ok | 26.4 ❌ | 24.0 ❌ | 23.3 ❌ | **24.2 ❌** | <= 22 |

Both inherited violations are closed and the four deliberate-strategy assertions
are green with margin. What each run cost is worth recording, because two of the
three edits between runs were fixes to defects in the new content, not tuning:

* **run 1 -> 2** removed the `ran_the_seam` grant (§5 of the handoff -- an
  unintended master key to the Ferryman succession), capped `Mental_Decay`, and
  state-gated the six repeatables. Greedy's terminal came back inside its band as
  open_door fell 52.3% -> 27.9%, and reckless went *over* the top of its band in
  the same motion -- the same redistribution seen from the other side.
* **run 2 -> 3** raised the repeatables' cooldowns ~60%. One lever, landing
  reckless at 32.8% with margin on both sides.
* **run 3 -> shipped** trimmed `Mental_Decay` again (caps 9/12 -> 6/8) at the last
  violation. **It did nothing** -- 23.3% -> 24.2%, no effect and the wrong sign.

That last row is the useful one. Random's only Sanctuary route is
`md_high_streak`, so MD deltas looked like the obvious lever and are **measured
dead** (§5). The mechanism: MD is driven through `update_mood`'s EMA on daily
*stress*, which comes from `Substance_Reliance` withdrawal rather than from any
one storylet's number -- and softening content lengthens runs, which gives them
more time to hold MD >= 90 for five days. Median run length rose on every
softening pass this window. **The two available knobs fight each other**, which is
why four gate runs is where §2's "do not chase gate overages" applies.

Note also that random is the *chaos baseline*, not one of the three strategies
`DELIBERATE` asserts against, and it is the only strategy that trips this cap.

### 9.5 What this leaves for Phase 4

> **Superseded by §10.** Options 1 and 3 below were taken; the `ambitions_pack`
> regression was diagnosed as a weight defect and closed; the `resistance_pack`
> guess in the last paragraph was measured **wrong** (§10.5). Kept for the record.

**The coverage gate is the open question, and it is now clearly an instrument
problem as much as a content one.** `MAX_NEVER_FIRED` is 85. The measured mean is
113.2 live / 119.6 control across five seed bases -- and the *control* being the
worse of the two is the whole point: the level is set by the deck, not the map.
Phase 3 was already 91.8 against the same gate of 85, so **the gate has not been
green at any point in the last two windows**, and no branch of §8.9 would have
made it green. Options, in preference order:

1. Assert the mean over 3-5 seed bases (§8.7's own recommendation, still not done)
   and re-base the threshold to whatever that mean measures on a deck everyone
   agrees is healthy. The current single-seed assert is a lottery with a 28-event
   spread.
2. Reduce the deck's always-eligible repeatable population -- **not** via stat
   gates, which §5 now records as measured-ineffective for this purpose.
3. Accept that a 497-event deck at n=40 will never fire ~20% of itself and that
   the metric worth gating is per-pack reachability, not the deck-wide count.

**`ambitions_pack` moved the wrong way** -- 9/24 unreached at Phase 3, **14/24**
on the shipped build (seed 0). The second entrance built for
`amb_clean_8_the_collectors` did not pay for the two hazard events added to
`the_archive`. This is the one acceptance criterion that got worse rather than
better and it should be the first content thing the next window looks at;
`resistance_pack` on `level_d` did the same (3/12 -> 8/12) and is probably the
same fix. Against that, `second_ferryman_pack` went 4/7 -> **0/7** -- the Seam's
new hazards carry the shelf that A1 Phase 3 could not reach -- and
`district_hazards_pack` itself is 1/14, so the new content is not sitting unread.
Read all of these as single-seed figures with the §8.7 caveat attached.

---

## 10. Phase 3c -- fixing the instrument, then reading it (2026-07-28, Opus 5)

§9.5 listed three options for the coverage gate in preference order. This window
took **1 and 3 together**: assert the mean over seed bases (option 1), and retire
the deck-wide count in favour of a metric that distinguishes reachability from
competition (option 3). Option 2 -- reducing the always-eligible repeatable
population -- was not needed, and §10.4 explains why it would have been aimed at
the wrong thing anyway.

### 10.1 The gate now asserts a mean, and it asserts two numbers instead of one

Two changes to `tests/coverage_audit.py`, and the second one matters more.

**The mean.** `--assert` sweeps five seed bases (0/100/200/300/400, i.e.
`--seed + k * ASSERT_SEED_STRIDE`) and gates on the mean. This is §8.7's own
recommendation, three windows late. It costs four extra audits, about two
minutes. Note the sweep is *deterministic* given a deck -- the same five seeds
every time -- so the threshold's headroom is a tolerance for content drift, not a
margin for noise.

**The split.** Every draw's pool is now unioned deck-wide, which costs nothing
(an unplaced draw's pool already *is* every gate-passing event, and
`auto_placement` never takes more than slot 0, so there is at least one unplaced
draw a day). That splits never-fired into:

* **starved** -- never passed its preconditions in any of the 40 runs. No weight,
  placement or pool-composition lever reaches these. The fix is always authoring
  or a gate edit.
* **outcompeted** -- sat in a real draw and lost it. This is the failure A1 was
  built to attack.

F1 established that this distinction is the whole ballgame, but only ever
computed it for a `--track-*` subset. Deck-wide, on Phase 3b's shipped build:

| | mean of 5 bases |
|---|---|
| never fired | 113.2 |
| **of which starved** | **76.2** |
| of which outcompeted | 37.0 |

**Two thirds of what the old gate measured was not what its own error message
claimed.** `MAX_NEVER_FIRED = 85` said "more written content has fallen out of
reach"; 76 of those 113 events had never been within reach to fall out of.

### 10.2 Neither half is a gate on its own, and that is measured

The obvious next step -- gate only on `outcompeted`, since it is the only half a
lever moves -- is wrong, and the counter-example was already in the project's
history. Re-running F1's disaster configuration (`--ambient-slots 0`, the build
that scored 174 never-fired and broke the balance gate at reckless 21.8%):

Both columns below are the **Phase 3b deck**, so the only variable is the quota:

| mean of 5 bases | live | `--ambient-slots 0` |
|---|---|---|
| never fired | 113.2 | 177.4 |
| starved | 76.2 | **153.0** |
| outcompeted | 37.0 | **24.4** |

**F1's catastrophe scores as an improvement on `outcompeted`.** Starving the pool
means fewer events are ever offered, so fewer can lose. The converse is Phase 3b:
flooding the deck with always-eligible repeatables (§9.3) pushes `outcompeted` up
while leaving starvation roughly flat. The two numbers move against each other
under exactly the levers this project reaches for, so `MAX_STARVED` and
`MAX_OUTCOMPETED` are a pair. Gate one and the other is free to run away -- which
is, in retrospect, the failure mode the single summed gate was papering over.

### 10.3 Is ~113 never-fired of 497 a problem? No -- and the split says which 113

Step 2's question, answered. Of Phase 3b's 113.2:

* **76.2 starved**, and the largest blocks are the ones already measured
  gating-shaped twice: `legacy_pack` 18/18 (unreachable by design),
  `betrayal_pack` 13, `npc_arcs_pack` 11, `ambitions_pack` 11, `resistance_pack`
  7. These are chain-depth and day-gate problems, not map problems.
* **37.0 outcompeted**, i.e. 7.4% of the deck offered and not chosen in 40 runs of
  a game that shows ~89 unique events per run. Ten of those 37 were
  `sonnet_5_volume_pack` out of 185 -- the texture, doing its job.

So the answer is no, the *level* was not the problem. But the split immediately
found a real one hiding inside it, which is the point of building an instrument
before arguing about a number: `ambitions_pack`'s 14 unreached were **11 starved +
3 outcompeted**, and in a strictly sequential chain, competition at link N shows
up as *starvation* at links N+1..6. The split does not separate cause for chains;
it points at where to look.

### 10.4 The `ambitions_pack` regression was a weight defect, and it had been there all along

Tracking `the_archive` shelf (37 events, 3437 eligible draws, 219 picks) named the
cause in one table:

| shelf pick counts | fires |
|---|---|
| `dgr_archive_clean_cut` (w9, `max_fires: 0`, cd 8) | **50** |
| `amb_the_choosing` (w6) | 24 |
| `amb_alley_cam_blind_spot` (volume ambient) | 23 |
| `cx_vint_archive_night` | 22 |
| `dgr_archive_sealed_pull` (w10) | **18** |
| *the entire 24-event ambitions chain* | *44* |

The two Phase 3b hazards took **68 of 219 picks on the shelf, 31%**, against 44
for the whole chain the shelf exists to carry. And the reason is not that they
were added -- it is what they were added *next to*:

| pack | median weight |
|---|---|
| `ambitions_pack` | **3.0** |
| deck | 6.0 |
| `district_hazards_pack` | 10.0 |
| `resistance_pack` | 12.5 |

**`ambitions_pack` was authored at the lowest median weight in the deck** -- half
the deck median, a third of the hazards it now shares a shelf with. §0's founding
measurement, `amb_the_choosing` losing 2271 of 2290 draws, was read as a pool-size
problem and answered with a map. It was *also* a weight problem, and the map hid
that for three phases by handing the chain a small pool where even a weight-3
event wins sometimes. Phase 3b put weight-9 and weight-10 content on that same
small pool and the hidden defect surfaced as a regression.

Nothing was removed from the shelf -- §8.4 records that the untagged middle is
where this deck keeps its deaths, and stripping it broke five balance assertions.

**The first attempt overcorrected, and the way it failed is the finding.** Chain
links to 10, picker and finales to 12, took the pack to 4/24 unreached at seed 0 --
and broke two balance assertions that had been green:

| n=1000/strategy | Phase 3b | links 10 / finales 12 | **shipped: links 7 / picker 8 / finales 5** |
|---|---|---|---|
| Greedy good (cap 45) | 39.9 | **50.3 ❌** | **41.1 ✅** |
| Greedy terminal (12-25) | 15.4 | **8.6 ❌** | **16.7 ✅** |

This is §8.4's mechanism arriving from a third direction: reserving draws for
thread content reserves them for *winning*. The useful detail is **which** part of
the chain did it. The links are Meaning-neutral (mean delta between -1.2 and +1.0
across all 24 events), so they inflate nothing on their own; the good endings come
from the finales' flags -- `chose_small_life`, `crossed_wire`, `second_door_solo`,
`shepherd_accepted` -- firing `check_endings` directly. **So the coverage job and
the balance risk live on different events**, and the fix separates them: links to
7 (above the deck median of 6, below the hazards' 10) carry the coverage, finales
go back to 5, at their authored level. `amb_clean_8_the_collectors` is held at 8
because it feeds `flag_syndicate_execution`, i.e. it is on the *terminal* side.

| mean of 5 seed bases, n=40 | Phase 3b | links 10/12 | **shipped** |
|---|---|---|---|
| `ambitions_pack` unreached | -- | 6.0 | **8.6** |
| deck-wide never fired | 113.2 | 101.8 | **101.2** |
| starved | 76.2 | 67.0 | **66.2** |
| outcompeted | 37.0 | 34.8 | **35.0** |

The coverage gain survived the dial-back almost entirely; the balance damage did
not. At seed 0 the pack is 7/24 unreached against Phase 3b's 14/24 and the
criterion's 9/24 -- but the mean is the number that counts now, and 8.6 has under
half a point of margin. The `second` chain completes end to end in the better
seeds; `clean`'s links 4-6 and its finale remain, and those are the day-gate
problem in §10.7, not this one.

### 10.5 `resistance_pack` was *not* the same shape, and the difference is worth having

§9.5 guessed `resistance_pack` (3/12 -> 8/12 on `level_d`) was the same fix. It is
not, and the guess would have cost a window. Resistance already carries the
deck's *highest* median weight (12.5). Instrumenting the flags directly, over 40
runs:

| | runs of 40 |
|---|---|
| `res_chalk_sign` eligible | **40** |
| `res_chalk_sign` fired | 25 |
| reached `echo_contact` | **3** |
| reached `informer_marked` | 7 |
| reached `echo_trust1` | **0** |

The head of a 12-event chain is a `max_fires: 1` event with three choices, exactly
one of which opens the chain, at `base: 0.55`. A random bot enters at
1/3 x 0.55 x (25/40) = **~11% of runs**; the other 15 of 25 fires set no flag at
all and close the chain permanently, with prose that says so ("The chalk is gone
by morning. All of it."). This starves not just `resistance_pack` but every
`echo_contact` consumer in the deck -- ten storylets in `sonnet_5_volume_pack`,
two in `cast_expansion_pack`, one in `district_hazards_pack`, plus an epilogue
clause. `echo_contact` is the highest-leverage starved flag measured so far.

Fixed with a §9.1-style second entrance rather than by softening the roll: the
failed follow now sets `chalk_lost`, and `res_chalk_second_look` (level_d, w12,
day >= 12, `none: [echo_contact, informer_marked]`) offers the thread back to a
player who kept coming down there. Per §9.2 the flag was grepped in `none:`
groups first -- both consumers (`res_chalk_sign`, `res_informer_recruitment`) are
unreachable-by-construction from this event, so it starves nothing.

Two things this does *not* fix, both recorded rather than chased:

* **Chain depth.** `res_blackout_run` still fires 0 times: it is link 4 of a chain
  on a shelf visited about twice per run. Entry improved (`res_dead_drop` 1 -> 3
  fires, `res_library_run` 0 -> 3); depth did not.
* **The strategy the instrument plays.** `coverage_audit` runs `random`, which
  picks uniformly among choices. A player pursuing the Echo thread picks
  `follow_the_arrow` and enters at 55%, not 11%. **Any branch-gated chain is
  systematically under-measured by this instrument**, and per-pack coverage rows
  for such chains should be read as a floor, not as the player experience.

### 10.6 Results

Shipped: 498 events, 332 shelved, 7 districts, `PLACEMENT_RATE = 0.40` unchanged.

| mean of 5 seed bases, n=40 | Phase 3b | **Phase 3c** | gate |
|---|---|---|---|
| never fired | 113.2 | **101.2** | (reported, not gated) |
| starved | 76.2 | **66.2** | `MAX_STARVED = 76` ✅ |
| outcompeted | 37.0 | **35.0** | `MAX_OUTCOMPETED = 42` ✅ |

Both thresholds are **regression guards re-based on the shipped build's measured
mean**, not targets the deck is failing -- that is stated in the code, as §4 of
the handoff required. Headroom is ~15-20% against F1/F2's ~6%, and the reason is
measured: the metric's per-base spread depends on the deck, not on the instrument.
`outcompeted` reads 33/29/38/38/37 (spread 9) on the shipped build, 25/28/47/48/26
(spread 23) on the overcorrected one, and 38/38/37/38/34 (spread **4**) on Phase
3b. **That last, tightest number was not stability -- it was `ambitions_pack`
losing every draw in every seed, which is a very repeatable result.** Do not read
low variance as instrument quality without checking what produces it.

The balance gate, at n=1000 per strategy:

| assertion | Phase 3b | overcorrected | **shipped** | band |
|---|---|---|---|---|
| Reckless terminal | 34.6 | 32.2 | **33.3 ✅** | 25-35 |
| Greedy terminal | 15.4 | 8.6 ❌ | **16.7 ✅** | 12-25 |
| Greedy good | 39.9 | 50.3 ❌ | **41.1 ✅** | <= 45 |
| Reckless good | 32.7 | 34.7 | **30.9 ✅** | <= 45 |
| Cautious terminal | ok | ok | **17.8 ✅** | >= 5 |
| Random institutionalized | 24.2 ❌ | 23.0 ❌ | **23.8** | see below |

**`INSTITUTIONAL_CAP` was split rather than chased: 22.0 for the three deliberate
strategies, a new `INSTITUTIONAL_CAP_RANDOM = 26.0` for the chaos baseline.** The
full reasoning is in `tests/sim_bot.py` beside the constant; the four load-bearing
facts are:

1. **The assertion's premise does not hold for random.** "The Sanctuary is
   swallowing the ending table" -- random's table is 13 distinct endings led by
   `TERMINAL_overdose_death` at **41.5%**, institutionalized second at 23.8%. The
   cap is silent about the 41.5%.
2. **Where it earned its keep it is untouched.** The cap was written for greedy at
   23.5%; greedy is now 14.5%, reckless 13.4%, cautious 10.1% -- all three keep
   22.0 with 7.5+ points of margin, and a regression in any of them still fails.
   This is strictly *more* selective than raising one number to 25.
3. `Mental_Decay` is measured dead across two gate runs (§9.4).
4. **Run length -- the lever §9.4 recommended instead -- moved it 0.4 points.**
   This window cut random's median run 34 -> 30 days and the figure went 23.0 ->
   23.8. Across the four decks measured in two windows it reads 24.2 / 23.3 / 23.0
   / 23.8: stable against everything tried, which is the shape of a structural
   floor rather than a tuning miss.

26.0 is a regression guard on the worst of those four (24.2), carrying the same
~2 points of headroom as the deliberate bands. It is not permission to drift.

### 10.7 What is left

**The day ladder is now the whole of `ambitions_pack`'s residual**, and it is the
same open thread recorded twice before (A1 Phase 1's §5 note; "The Rounding is
day-55 gated but the median run ends day 58"). The three chains gate links at
10/16/22/28/34/40 and finales at 46-52 against a **34-day median run**. Weight
parity got links 1-5 firing; nothing short of re-scaling the ladder gets link 6
and the finales into a median run reliably. This wants its own item -- it is a
pacing decision across every chain in the deck, not an A1 one.

**Chain depth on shelves.** `res_blackout_run` at link 4 of a `level_d` chain, on
a shelf a run stands in about twice, is the general case of what §10.5 measured.
Per-district cadence is `len(districts) / PLACEMENT_RATE` ~ 18 days, so a 6-link
shelf chain cannot complete on placed draws alone. Either chains on shelves need
to be shorter, or a district needs to be visitable more often than three times a
run -- and the second option is a `PLACEMENT_RATE` change, which §8.4 records as
balance-critical.
