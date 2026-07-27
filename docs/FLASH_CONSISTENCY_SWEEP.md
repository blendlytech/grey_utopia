# Flash 3.6 Consistency Sweep — reusable prompt

Paste the block below into Gemini 3.6 Flash High inside Antigravity, with the repo open.
Re-run it after any content pass. It reports; it does not edit.

---

You are auditing content for **GREY UTOPIA**, a gritty text RPG / life-sim with a
Quality-Based Narrative engine, set in a post-scarcity AI dystopia governed by an AI called
The Steward. The player is an underground Fixer dealing in forbidden goods, off-grid
identities and synthetic vice. The repo is open in your workspace.

## Your task

Sweep **all 483 storylets across the 24 JSON packs in `data/events/`** for
**prose-vs-mechanics mismatches**: places where the narrative text of an event or a choice
branch says something different from what the engine actually does.

## Hard rule: DO NOT EDIT ANY FILES

Report only. Every `flags_set`, `deltas` or `preconditions` value in this project is
balance-load-bearing — a single flag change shifts the Monte Carlo ending distribution and
requires a 10-minute regression gate run to validate. Fixes get applied deliberately, in
batches, by someone who can run that gate. Your output is a findings report. Nothing else.

Do not run the game, the tests, or the balance gate.

## The schema you are comparing against

Every pack is `{"events": [ ... ]}`. Each event:

- `id`, `title`, `body` (the prose), `weight`, `cooldown`, `max_fires`, `tags`
- `preconditions`: `{"all"/"any"/"none": [cond, ...]}`, each cond being exactly one of
  `{"flag": name, "value": true|false}` · `{"stat": NAME, "op": ">=", "value": n}` ·
  `{"day": n, "op": ">="}` · `{"item": id, "value": bool}` ·
  `{"faction": name, "op": ..., "value": ...}` ·
  `{"relationship": name, "op": ..., "value": ...}` · `{"clock": name, ...}`
- `inserts`: `[{"text": ..., "when": <same condition grammar>}]` — extra paragraphs appended
  to `body` when their conditions match
- `choices`: `[{id, text, prob: {base, mods: [{stat, coef}]}, requires: {...},
  boost_items: [...], success: {...}, failure: {...}}]`

A branch (`success` / `failure`) may carry **only** these keys, which are the ones the
engine actually applies:

```
text, deltas, faction_deltas, rel_add, rel_deltas, dose,
item_rewards, items_consumed, clocks_start, clocks_stop,
flags_set, flags_clear
```

**Any other key is silently ignored at runtime** — a typo like `flag_set`, `delta`,
`flags_add` or `rel_delta` means that effect never happens and nothing warns anyone.
Treat every unrecognised branch key as a finding.

Valid stat names: `Wealth`, `Fame`, `Recklessness`, `Mental_Decay`, `Family_Friction`,
`Substance_Reliance`, `Heat`, `Physical_Integrity`, `Social_Capital`, `Meaning`,
`Tolerance`. Note `Wealth` is raw credits (a typical bankroll is ~50,000), not a 0–100 stat;
every other stat is 0–100. Higher `Mental_Decay`, `Heat`, `Family_Friction`,
`Substance_Reliance` and `Tolerance` are **worse** for the player; higher `Meaning`,
`Physical_Integrity`, `Social_Capital` are **better**.

Exact relationship names usable in `rel_deltas` / `rel_add` (from `data/cast.json`):
`Mara (Sister)`, `Vint (Informant)`, `Kael (Broker)`, `Echo (Resistance)`,
`Brann (Artisan)`, `The Ferryman (Seam)`, `Dex (Dispatcher)`, `Auntie Six (Stallkeeper)`,
`Denny (Root Vendor)`.

## What counts as a finding

1. **Prose asserts an effect the branch doesn't apply.** Text says you pocketed the spike,
   got paid, made an enemy, earned someone's trust — and there is no matching
   `flags_set` / `item_rewards` / `deltas` / `rel_deltas`.
2. **The branch applies an effect the prose contradicts.** *Real example, now fixed:*
   `hz_first_shift` in `horizon_pack.json` had a failure branch whose text has Brann
   stripping your bad rebuild in front of you in silent judgement — while the same branch
   granted `workshop_standing`, the flag meaning he had accepted you.
3. **Prose references a prerequisite the preconditions don't require.** *Real example, now
   fixed:* `flagship_the_crossing` in `fable_spiral_pack.json` opens with "Your forged
   credentials sit warm against your chest" while its preconditions never required
   `credentials_forged`, so the event fired for players who had never forged anything.
4. **Prose references gear** that appears in neither `boost_items`, `item_rewards` nor
   `items_consumed`.
5. **Stat direction contradiction.** Text describes a beating but `Physical_Integrity` is
   zero or positive; text describes getting paid but `Wealth` is absent or negative; text
   describes calm but `Mental_Decay` rises sharply, etc.
6. **Success and failure texts describe the same outcome** — the branches aren't
   distinguishable as written.
7. **Choice text promises something no branch delivers.**
8. **An `insert`'s `when` conditions contradict its text.**

## What NOT to flag

- **Anything schema-shaped. The schema is already machine-verified and clean.**
  `pipeline/lint_content.py` enforces duplicate ids, precondition operators, numeric `day`
  values, probability-coefficient sanity, missing branch text, item ids, exact relationship
  names, and soft-locked events — and it currently reports zero issues. A separate
  deterministic scan has already confirmed there are no unrecognised event/choice/branch
  keys anywhere in the deck. **Reporting "the schema is valid" is not a finding and tells
  the reader nothing.** Your entire value here is reading the *prose* against the *effects*.
  If a pack genuinely has no semantic mismatch, say so in one line — do not list the schema
  properties you checked.
- Deliberate ambiguity, dread, foreshadowing, or emotional suggestion. Prose here is
  literary; only flag *factual* claims about world state.
- NPCs or the Steward lying, spinning, or being wrong. Characters are unreliable on purpose.
- Failure branches that still move the story forward — "fail-forward" is the house style and
  a failure granting *some* progress is intentional. Flag it only when the granted effect
  directly contradicts what the text describes (category 2).
- Knowledge costing `Meaning` or `Mental_Decay`. That's the game's thesis, not a bug.
- Balance opinions. Do not comment on whether a probability or delta is too generous.

## How to work

**Calibration pass first.** Do `sonnet_volume_pack.json` (20 events, 60 choices) and stop.
It is bulk-generated and has never been hand-audited, so it is a fair test of the bar. For
the **first five events in it**, before any findings table, output a **claims ledger** that
proves you read the prose:

| event id | branch | factual claim made by the prose | effect that backs it |

One row per factual claim — every concrete assertion about world state the text makes
("he pays you", "you keep the spike", "she never speaks to you again", "you wake in a
Steward ward"). In the last column put the exact JSON effect that delivers it
(`deltas.Wealth: +900`, `flags_set: [...]`) or the single word **NONE**. A `NONE` is not
automatically a finding — judge it — but the ledger is what makes a "no findings" result
believable. Then give the findings table for the whole pack and stop for review.

After the calibration is approved, continue **pack by pack, smallest first**, emitting a
section per pack as you finish it. Leave `sonnet_5_volume_pack.json` (185 events, 556
choices — by far the largest, same bulk-generated origin) for last.

Packs, by size:
`faction_jobs` 2 · `intro_jobs` 2 · `steward_interventions` 2 · `origins_pack` 3 ·
`fable_reviews_pack` 3 · `vice_lifestyle` 3 · `the_rounding_pack` 4 ·
`second_ferryman_pack` 7 · `prologue_pack` 9 · `ascension_pack` 10 ·
`fable_flagship_pack` 10 · `fable_spiral_pack` 11 · `resistance_pack` 12 ·
`horizon_pack` 13 · `origin_threads_pack` 13 · `npc_arcs_pack` 17 · `legacy_pack` 18 ·
`sonnet_volume_pack` 20 · `ambitions_pack` 24 · `reckoning_pack` 25 ·
`sonnet_volume_pack_2` 25 · `betrayal_pack` 30 · `cast_expansion_pack` 35 ·
`sonnet_5_volume_pack` 185

Skip `data/events/endings.json` — different schema, not part of this sweep.

## Output format

One markdown table per pack, most severe first, plus a one-line count. Columns:

| event id | choice id | branch | category | what the prose says | what the mechanics do | fix side | confidence |

- **branch**: `body`, `success`, `failure`, `choice text`, or `insert N`
- **category**: the number from the list above
- **fix side**: `PROSE` (rewrite the text to match the mechanics) or `MECHANICS` (change the
  effect to match the text) — pick the one that preserves the author's evident intent, and
  prefer `PROSE` when it's a close call, because prose edits don't need a balance gate run
- **confidence**: `high` / `medium` / `low`. Be strict: a `high` should be something a
  reader would agree is simply wrong, not a matter of taste.

Finish with a summary: total findings, the breakdown by category, and the five you would fix
first.
