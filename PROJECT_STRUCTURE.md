# GREY UTOPIA -- Repository File Structure

This document outlines the complete directory layout and module responsibilities for the GREY UTOPIA Quality-Based Narrative (QBN) engine.

```
c:\Users\DELL\Dice_Roll_2\
├── .agents/
│   └── skills/
│       ├── storylet-generator/       # Skill: Creating & validating JSON storylets
│       ├── balance-tester/           # Skill: Running Monte Carlo simulations & tuning math
│       └── batch-content-pipeline/   # Skill: Orchestrating LLM batch generation calls
├── data/                             # Static Data Libraries (Zero runtime LLM calls)
│   ├── assets/                       # Scene artwork (PNG): places only, never featured people
│   │   └── originals/                # Pre-crop originals (contained prominent figures; not served)
│   ├── events/
│   │   ├── intro_jobs.json           # Fixer job contracting storylets
│   │   ├── steward_interventions.json# Steward surveillance & counseling storylets
│   │   ├── vice_lifestyle.json       # Synthetic drugs, family, & off-grid exit storylets
│   │   ├── faction_jobs.json         # Faction-aligned contract storylets
│   │   ├── fable_flagship_pack.json  # 10 flagship narrative chains (Fable 5)
│   │   ├── fable_spiral_pack.json    # Doom-spiral & finale content incl. The Crossing
│   │   ├── reckoning_pack.json       # Consequence engine: debts, deadlines & flag payoffs
│   │   ├── resistance_pack.json      # Echo arc: recruitment -> the Archive twist -> Shepherd
│   │   ├── horizon_pack.json         # Quiet-life arc, Ferryman succession, Steward set-pieces
│   │   ├── ascension_pack.json       # THE DEPRECATION: day-gated AI-takeover world arc (money dies -> succession)
│   │   ├── sonnet_volume_pack.json   # Volume events batch 1 (Sonnet 5)
│   │   ├── sonnet_volume_pack_2.json # Volume events batch 2 (Sonnet 5)
│   │   └── endings.json             # 11 endings + reactive per-run epilogue tables
│   ├── items.json                    # Black-market gear catalog
│   └── cast.json                     # Named NPC definitions & Ebbinghaus memory params
├── engine/                           # Decoupled Core Simulation Engine
│   ├── __init__.py
│   ├── stats.py                      # 11 bounded stats, Character, clocks & relationship model
│   ├── decay.py                      # EMA mood, Ebbinghaus retention, Hill drug curve, OD math, clock ticks
│   ├── events.py                     # Schema validator, precondition matcher (stats/flags/items/factions/relationships/clocks)
│   ├── items.py                      # Catalog access: prob-bonus gear, single-use burns
│   ├── selector.py                   # Weighted selector: instability bias, story momentum, repetition damping
│   └── resolver.py                   # Probability + gear boosts, dose/OD pipeline, 11 endings, reactive epilogues
├── pipeline/
│   ├── generate_deck.py              # Chunked LLM batch generator (Opus 5 / Sonnet 5 / Gemini)
│   └── lint_content.py               # Static content linter (ids, flags, items, prob sanity)
├── ui/
│   ├── __init__.py
│   └── terminal.py                   # Atmospheric ANSI text HUD & choice renderer
├── web/
│   ├── index.html                    # Web UI shell (HUD, storylet stage, ending modal)
│   ├── styles.css                    # Neon-noir theme, meters, roll reveal, day overlay
│   └── app.js                        # Frontend controller (typewriter, keyboard, gallery)
├── saves/                            # Autosave slot written by server.py (gitignorable)
├── tests/
│   ├── __init__.py
│   ├── test_engine.py                # Unit test suite for math and engine logic
│   └── sim_bot.py                    # Monte Carlo bot: random/cautious/reckless/greedy + gates
├── docs/
│   └── FABLE_WORLD_SPEC.md           # Master world-building directive for Fable 5
├── CLAUDE.md                         # Model allocation matrix & CLI execution instructions
├── main.py                           # Terminal game entry point (Interactive & --auto mode)
├── server.py                         # Web server: REST API, autosave persistence, asset host
└── PROJECT_STRUCTURE.md              # This file
```

## Core Architectural Guarantees
1. **Decoupled Engine**: Core statistical simulation (`engine/`) does not depend on UI rendering (`ui/`) or content generation (`pipeline/`).
2. **Zero Runtime API Cost**: All game events are loaded from static JSON files in `data/events/`.
3. **Fail-Forward Choice Mechanics**: Every storylet contains $\ge 3$ choices with hidden probability outcomes that mutate game state regardless of success or failure. Crisis events may corner the player behind `requires` gates, but at least one choice is always visible (lint-enforced).
4. **Consequence Persistence**: Flags set by any storylet are consumed by later ones (`reckoning_pack.json`), deadline clocks tick toward enforced reckonings, and every ending composes a reactive epilogue from the run's actual history.
5. **Balance Gates as CI**: `python tests/sim_bot.py all --assert` enforces: every ending reachable, random play dies ≥35% and wins ≤20%, EV-optimal play beats random, and reckless play trails optimal play by ≥3 points.
