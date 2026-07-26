# LEGACY SYSTEM — Outline & Build Spec (Plan Item 5)

Fable 5 design + flagship callbacks, July 24 2026. Engine changes assigned to **Antigravity or Sonnet 5**
(CLAUDE.md Checkpoint 3: Fable does not edit `engine/*.py` or `ui/*.py`). Volume expansion assigned to Sonnet 5.
Fable-written flagship events live in `data/events/legacy_pack.json` — **10 events after this pass
(5 original + 5 new); do not rewrite any of them.**

## Design intent

Today legacy is pure flavor: `engine/legacy.py` stamps `legacy_cycle2plus` / `legacy_<ENDING_ID>` /
`legacy_last_<ENDING_ID>`, and five one-shot events react with prose. Nothing a previous run does changes
starting conditions, choice availability, or NPC temperature. This spec weaponizes it in three layers:

1. **Layer 1 — The Prior (engine + data, NEW).** The last run's ending adjusts the next run's *starting
   arithmetic*: small stat, faction, and relationship deltas from a data table. Fiction: the new fixer is a
   new person; what persists is the **file's prior about people like you**. The Steward's cohort model, the
   syndicate's default rates, the Row's expectations — the city adjusts its terms before you say a word.
2. **Layer 2 — Echoes (engine, NEW).** A short whitelist of knowledge-flags persists across runs as
   `legacy_echo_<flag>` — knowledge that escaped into the *world* (a studied ledger, a memorized docket
   number, a footprint found and deliberately lost). Never feelings, never relationships: only things that
   were written down or leaked into the rumor stratum.
3. **Layer 3 — The City Remembers (content, THIS PASS + Sonnet).** Flagship callback events for the most
   distinctive endings, plus choice-level `requires` gates that **compose multiple lifetime endings** —
   e.g. a run after Gardener's Winter plays differently again if any past run also reached The Advocate.
   The engine's `requires` field on choices already supports this today; no engine change needed for Layer 3.

The thesis across all three layers: **the player never gets their old save back.** Inheritance is the city's
memory, not the character's. That keeps deaths real while making every previous ending a different opening
position — and makes replaying toward specific ending *combinations* a deliberate cross-run build.

## Invariants (do not violate)

- `tests/sim_bot.py` never calls into `engine/legacy.py` — balance gates stay legacy-free (module docstring
  is already explicit about this). Layers 1–2 are applied only from `main.py` and `server.py`.
- Layer 1 reads **`last_ending` only** — no compounding across many runs, no stacking of every ending ever seen.
- Caps: every inheritance delta satisfies |stat| ≤ 8, |faction| ≤ 8, |relationship| ≤ 8. Anything larger is a
  balance change, not a prior. All values below are inside one typical event's swing.
- Bot/auto runs still skip `record_ending` (existing `if not auto_play` guard in `main.py:122`).

## Layer 1 spec — `data/legacy_inheritance.json` + `apply_legacy_inheritance`

**New data file** `data/legacy_inheritance.json`, keyed by ending id (transcribe exactly):

```json
{
  "TERMINAL_overdose_death":       { "stat_deltas": { "Heat": 4 }, "faction_deltas": { "Undercity": 3 } },
  "TERMINAL_institutionalized":    { "stat_deltas": { "Heat": -3 }, "faction_deltas": { "Steward": 5 } },
  "TERMINAL_synthetic_detachment": { "stat_deltas": { "Substance_Reliance": 3, "Social_Capital": -2 } },
  "TERMINAL_syndicate_ledger":     { "faction_deltas": { "Undercity": -5 }, "rel_deltas": { "Kael (Broker)": -8 } },
  "TERMINAL_gardeners_winter":     { "stat_deltas": { "Meaning": 4, "Mental_Decay": 4 } },
  "GOOD_offgrid_escape":           { "stat_deltas": { "Heat": 4, "Meaning": 3 }, "faction_deltas": { "Undercity": 5 } },
  "GOOD_small_real_things":        { "stat_deltas": { "Family_Friction": -5 }, "rel_deltas": { "Mara (Sister)": 6 } },
  "GOOD_the_advocate":             { "stat_deltas": { "Fame": 5, "Social_Capital": 3 }, "faction_deltas": { "Steward": 3 } },
  "NEUTRAL_the_open_door":         { "stat_deltas": { "Heat": 3 }, "faction_deltas": { "Undercity": 4 } },
  "NEUTRAL_stewards_shepherd":     { "stat_deltas": { "Social_Capital": -3 }, "faction_deltas": { "Resistance": -8 } },
  "NEUTRAL_cashed_out_compliance": { "faction_deltas": { "Undercity": -4, "Steward": 4 } },
  "NEUTRAL_keeper_of_the_switch":  { "stat_deltas": { "Meaning": 3 }, "faction_deltas": { "Steward": 5 } },
  "NEUTRAL_the_long_grey":         { "stat_deltas": { "Meaning": -4, "Social_Capital": -2 } },
  "NEUTRAL_alienation_empty_suite":{ "stat_deltas": { "Social_Capital": -4, "Fame": 3 } }
}
```

Rationale, one line each (the prior is how the city treats fixers now, never a stat carryover):

- **overdose_death** — wellness attention on the cohort (Heat), the Row mourns its own (Undercity).
- **institutionalized** — the file says fixers break toward comfort; the Steward relaxes and waits (Heat −, Steward +).
- **synthetic_detachment** — Parlor Row preloads the cohort's preferences; the Row respects it less.
- **syndicate_ledger** — Kael's book opens colder for fixers; the undercity remembers the default, not the person.
- **gardeners_winter** — the Winter Garden exists; stakes are visible from day one (Meaning +, Mental_Decay +).
- **offgrid_escape** — the legend is confirmed (Undercity +, Meaning +) and the lattice watches fixers harder (Heat +).
- **small_real_things** — the Row's model of fixers includes one who came to dinner; Mara starts warmer.
- **the_advocate** — a fixer holds the chair; the name travels (Fame +) and the machines are politer (Steward +).
- **the_open_door** — the ferry economy runs; seam-adjacent trades favor fixers (Undercity +) and drones linger (Heat +).
- **stewards_shepherd** — shepherd doctrine: every fixer is a presumptive plant (Resistance −8, Social_Capital −).
- **cashed_out_compliance** — the buyout testimonial: fixers sell (Undercity −), and sell well (Steward +).
- **keeper_of_the_switch** — the machines chose a fixer as their audit once (Steward +, Meaning +).
- **the_long_grey** — the Row expects nothing from fixers anymore; that expectation is contagious.
- **alienation_empty_suite** — the name still opens doors (Fame +); nobody walks through them toward fixers (Social_Capital −).

**Engine change** (Antigravity/Sonnet — `engine/legacy.py` only):

- Add `INHERITANCE_PATH = data/legacy_inheritance.json` and
  `def apply_legacy_inheritance(character: Character) -> Dict[str, Any]`.
- Behavior: load `saves/legacy.json`; if `cycles >= 1` and `last_ending` is a key in the table, apply
  `stat_deltas` via `character.apply_deltas` (engine clamps), `faction_deltas` via `character.add_faction`,
  `rel_deltas` via `character.adjust_relationship` **only for relationships that already exist**. Return the
  applied entry (empty dict when nothing applied). Missing/corrupt table file = silent no-op, like `load()`.
- Defensive: skip unknown stats; assert nothing (content errors must not crash a boot).
- Call sites: `main.py` immediately after `legacy.apply_legacy_flags(character)` (line 106); `server.py`
  after both call sites (lines 38 and 172). When non-empty, print/emit one line:
  `[The file precedes you. The city has adjusted your terms.]`
- Tests (`tests/test_legacy_inheritance.py`, new): every table key is a `RESOLVER_ENDINGS` member; every
  stat key is in `STAT_SPEC`; every |delta| ≤ 8; every rel key is a cast name; applying with
  `last_ending = TERMINAL_syndicate_ledger` lowers Kael satisfaction on a starter fixer and leaves the
  sim path (no legacy call) untouched.
- Optional lint addition: validate `legacy_inheritance.json` stats/rel names in `pipeline/lint_content.py`.

## Layer 2 spec — echo flags

- In `engine/legacy.py`, add `ECHO_FLAGS: frozenset` =
  `{ "kael_docket_memorized", "drawer_footprint_found", "tenant_ledger_studied", "legend_chased",
     "switch_logic_run", "winter_terms_read", "mask_dates_run", "resident_last_request_known" }`.
  (First five already exist in the deck; last three are minted by this pass's new events.)
- Change `record_ending(ending_id)` → `record_ending(ending_id, character)`: store
  `sorted(set(data.get("echoes", [])) | (ECHO_FLAGS & character.flags))` under `data["echoes"]`.
  Union across runs — knowledge accumulates in the world. Missing key = empty (backward compatible with
  existing `legacy.json` files).
- `apply_legacy_flags` additionally mints `legacy_echo_<flag>` for each stored echo. The `legacy_` prefix
  keeps lint's required-but-never-set check happy automatically.
- Update callers to pass `character`: `main.py:123`, `server.py:120`, `server.py:152`.
- Content that consumes echoes (Sonnet, AFTER the engine change lands — do not ship these first):
  - `legacy_echo_the_docket` — requires `legacy_echo_kael_docket_memorized` (the hook NPC_ARCS_OUTLINE
    explicitly reserved): the previous tenant's ledger holds Tomas's docket number; run-2 leverage on Kael
    that no first-run player can have.
  - `legacy_echo_footprint` — requires `legacy_echo_drawer_footprint_found`: the bolt-hole with the
    machine-sealed mail addressed to THE AUDIT, found again, faster, by someone who read the notes.

## Layer 3 — flagship callbacks (THIS PASS, done) and prioritization

Coverage before this pass: 3 of 14 endings had a dedicated callback (overdose_death, offgrid_escape,
keeper_of_the_switch). This pass adds **5 flagship events** (now 8 of 14 covered):

| New event | Ending consumed | Why flagship tier |
|---|---|---|
| `legacy_winter_intake` | `TERMINAL_gardeners_winter` | World-state ending — the Garden physically reaches the Row and pitches in the dead fixer's trade argot. Also carries the pack's one **composed choice**: `requires legacy_GOOD_the_advocate` (file for standing against the kiosk). |
| `legacy_exhibit_hours` | `GOOD_the_advocate` | World-state ending — the court exists, sessions are public sport, and it subpoenas unmanaged lives as exhibits. "DO NOT PREPARE." |
| `legacy_the_new_mark` | `NEUTRAL_stewards_shepherd` | The resistance minted new chalk grammar for shepherd risk, and it's on the player's door. Reputation as inheritance. |
| `legacy_continuity_of_care` | `TERMINAL_institutionalized` | The predecessor is still *alive*, optimized, visitable. The Steward's best horror, pointed at the player's own future. Carries the pack's single strong-profanity slot. |
| `legacy_voice_behind_the_mask` | `NEUTRAL_the_open_door` | The current Ferryman *is* the previous fixer. The seam's tests are now calibrated from inside the player's own job. |

**Left to the Sonnet 5 volume pass** (6 endings — real events, lower ceiling; specs below, betrayal-outline
format: id | gate | delivery):

1. `legacy_best_customer` | `legacy_TERMINAL_synthetic_detachment`, day ≥3 | Parlor Row kept the recliner
   paid for a body that stopped mattering; the house offers the new fixer "cohort preference preloading" —
   the predecessor's favorite tracks, as a loyalty perk. Decline/sample/ask-who choices.
2. `legacy_remembered_nothing` | `legacy_TERMINAL_syndicate_ledger`, day ≥4 | The undercity agreed to
   remember nothing; the player's asking is the only record that the person existed. Kael prices the
   question itself ("curiosity has a rate this quarter").
3. `legacy_the_bench_is_taken` | `legacy_GOOD_small_real_things`, day ≥3 | Brann's workshop keeps one bench
   under a tarp — the fixer who stopped. Brann compares the player's hands to the previous pair, unfavorably,
   and offers the tarp anyway.
4. `legacy_the_template` | `legacy_NEUTRAL_cashed_out_compliance`, day ≥3 | The Steward opens with a
   pre-approved buyout quote for the player's network — valuation attached, based on comparable-sale data
   the predecessor signed away. The insult is how accurate the comparable is.
5. `legacy_no_story` | `legacy_NEUTRAL_the_long_grey`, day ≥4 | The Row has no story about the last fixer —
   no chalk mark, because nothing ended; it just stopped. The event is the absence. Hardest to write; the
   wound is that the most common ending gets no monument.
6. `legacy_sealed_floor` | `legacy_NEUTRAL_alienation_empty_suite`, day ≥4 | The suite still stands, paid up,
   sealed, lights cycling on schedule for no one; a standing delivery contract still runs. Undercity
   couriers bid on the route because it always pays and never answers the door.

The Steward's **day-1 opening address** stays a single ritual: `legacy_the_loop` (weight 60, untouched).
Per-ending day-1 variants would fragment it; per-ending texture belongs in the day ≥2 events above.

## Hard mechanical rules (unchanged; verified against engine)

- Copy the JSON shape of the existing events in `legacy_pack.json`. Same field names, same grammar.
- Every event: `max_fires: 1`, ≥3 choices (engine assert), `prob` on every choice, symbol ops only.
- Preconditions: `"op"`/`"value"` — NEVER `"min"`/`"max"` (engine silently passes the gate).
- Every event keeps ≥1 choice without `requires` (lint soft-lock check). Choice-level `requires` may gate on
  any `legacy_*` flag freely (lint exempts the prefix; choice requires aren't scanned at all).
- Harm ≤ ~12–14 on bad branches. Relationship keys exact: `Mara (Sister)`, `Vint (Informant)`,
  `Kael (Broker)`, `Echo (Resistance)`.
- Do not modify `engine/*.py` or `ui/*.py` in a content pass (CLAUDE.md Checkpoint 3).
- Voice: docs/VOICE_BIBLE.md is law. The Steward never swears. Vint types lowercase, he/him. Kael prices.
  Echo is terse. End on the wound.
- Profanity budget: the 10-event legacy pack now carries exactly **one** strong use
  (`legacy_continuity_of_care`, player interiority, heard-logged-forgiven). Sonnet's 6 volume events: zero.

## New wiring introduced by this pass (complete list — add nothing else)

- Flags set: `winter_terms_read`, `testified_uncompressed`, `shepherd_mark_answered`, `chalk_rate_known`,
  `visited_the_resident`, `resident_last_request_known`, `mask_dates_run`, `seam_greeting_sent`.
  Chekhov status: `winter_terms_read`, `mask_dates_run`, `resident_last_request_known` join `ECHO_FLAGS`
  (Layer 2); the rest are reserved for ending-epilogue reactions and the Sonnet volume pass.
- Choice gate consumed: `legacy_GOOD_the_advocate` (composed choice in `legacy_winter_intake`).
- No new clocks, items, or cast names.

## Verification gate (after every batch; all must pass)

```
python -m unittest discover -s tests
python pipeline/lint_content.py
python tests/sim_bot.py all --assert
```

Build order: (1) this pass's content ships alone and is inert-safe — it only reads flags the engine already
mints. (2) Antigravity/Sonnet lands Layer 1 + Layer 2 engine changes with tests. (3) Sonnet writes the 6
volume events, then the 2 echo events. Lint between batches; full gate at the end.
