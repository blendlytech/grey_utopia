# CLAUDE.md -- GREY UTOPIA Development & Multi-Model Pipeline Directives

This document provides system instructions for Claude models (Opus 5, Sonnet 5), Gemini models (3.1 Pro High, 3.6 Flash High), and the Antigravity dev agent operating on **GREY UTOPIA**, a gritty single-player text RPG / life-sim Quality-Based Narrative (QBN) engine set in a post-scarcity AI dystopia ("The Steward").

---

## 1. Multi-Model Cooperation & Efficiency Stack

To maximize token efficiency, cost effectiveness, and creative quality across your $400 budget, tasks are divided among specialized agents:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      ANTIGRAVITY (Dev Agent)                            │
│  - Codebase orchestration, file editing, local environment management  │
│  - Executes unit tests (`unittest`), linting, & JSON schema validation  │
│  - Runs Monte Carlo simulation audits (`sim_bot.py`) for stat balance   │
└────────────────────┬───────────────────────────────┬────────────────────┘
                     │                               │
                     ▼                               ▼
     ┌───────────────────────────────┐  ┌───────────────────────────────┐
     │    BUILD-TIME GENERATION      │  │      BALANCE & AUDITING       │
     │                               │  │                               │
     │  Opus 5 (flagship only)       │  │  Opus 5 (balance audits)      │
     │  - Master World Bible         │  │  - Stat curve tuning          │
     │  - Flagship narrative chains  │  │  - Ending outcome balance     │
     │                               │  │                               │
     │  Sonnet 5 ($2/$10 Mtok)       │  │  Gemini 3.6 Flash (in-IDE)    │
     │  - 300+ Volume storylets      │  │  - Ambient text & barks       │
     │  - NPC relationship encounters│  │  - Mechanical sweeps & lint   │
     │                               │  │                               │
     │  Gemini 3.1 Pro ($2/$12 Mtok) │  │                               │
     │  - Volume overflow            │  │                               │
     └───────────────────────────────┘  └───────────────────────────────┘
```

**Roster note (2026-07-27):** Fable 5 and Opus 4.8 are no longer available. Flagship
narrative and balance auditing both consolidate onto **Opus 5**. Because Opus 5 is also the
in-session agent, flagship chains are now authored **directly in the working session** --
with the flag graph, `engine/selector.py` chain-depth scheduling and the `pargate` failure
modes already in context -- instead of being generated blind through `generate_deck.py`.
The `--batch flagship` path remains for unattended bulk runs, but it is no longer the main
road. Rates marked TBC are unconfirmed and left as `None` in `PRICING_MATRIX`; the dry-run
banner prints "unavailable" rather than a fabricated estimate until they are filled in.

**Gemini 3.6 Flash High has no API key and therefore no batch route.** It is driven
interactively inside **Antigravity**, so it is deliberately absent from `generate_deck.py`'s
`--model` choices. Its lane is IDE-side bulk work over the existing deck -- dead-flag hunts,
orphaned-event audits, prose-vs-mechanics consistency sweeps -- with `pipeline/lint_content.py`
as the acceptance check afterwards.

---

## 2. Mandatory Model Switch Checkpoints (STOP & REPORT)

LLMs and dev agents MUST halt and notify the user when reaching these explicit checkpoints:

### 🛑 Checkpoint 1: Flagship Core Completion
- **Trigger**: When Opus 5 completes generating the master world bible and 10 flagship narrative storylets (`data/events/opus_5_flagship_pack.json`, or an in-session authored pack).
- **Action**: **STOP GENERATION AND NOTIFY USER**:
  > "Flagship narrative core completed with Opus 5. Switch to Sonnet 5 or Gemini 3.1 Pro for high-volume expansion to save substantially on token cost."
  > **Command**: `python pipeline/generate_deck.py --model sonnet-5 --batch volume`

### 🛑 Checkpoint 2: Volume Deck Completion
- **Trigger**: When Sonnet 5 or Gemini 3.1 finishes generating 100+ volume events.
- **Action**: **STOP AND HAND OFF TO ANTIGRAVITY**:
  > "Volume event deck generated. Handing off to Antigravity to run unit tests and Monte Carlo strategy simulation."
  > **Command**: `python tests/sim_bot.py random`

### 🛑 Checkpoint 3: Code Modification Directive
- **Trigger**: Any request to modify Python simulation code (`engine/*.py` or `ui/*.py`).
- **Action**: **NEVER ROUTE ENGINE CODE THROUGH A BATCH GENERATION RUN** -- `generate_deck.py` emits storylet JSON only. Hand code modifications to **Antigravity**, **Opus 5**, or **Sonnet 5** working directly on the files, and re-run `python -m unittest discover -s tests` before the balance gate.

---

## 3. Cost & Model Matrix

| Model | Cost (In / Out) | Primary Assignment | Efficiency Rule |
|---|---|---|---|
| **Opus 5** | rates TBC | Master World Bible, Flagship Storylets, Probability & Balance Audits | Limit to flagship chains and balance work; NEVER use for volume prose. Authors flagship content in-session, not via batch generation. |
| **Sonnet 5** | $2 / $10 per Mtok | Volume Event Cards & NPC Dialogue | Primary workhorse; the default `--model` for `generate_deck.py`. |
| **Gemini 3.1 Pro High** | $2 / $12 per Mtok | Volume Overflow & High-Context Validation | Second volume lane; whole-deck reads that exceed a comfortable single-pass budget. |
| **Gemini 3.6 Flash High** | via Antigravity (no API key) | Ambient Barks & Bulk Mechanical Sweeps | **Driven interactively from Antigravity -- no `generate_deck.py` route.** Cheap high-volume passes over all 474 events: dead-flag hunts, orphaned-event audits, prose-vs-mechanics consistency. Always verify output with `lint_content.py`. |
| **Antigravity** | Local Dev Agent | Code execution, testing, file management | Free local execution & environment runner. |

---

## 4. Execution Command Reference

```bash
# Preview generation prompt & cost estimate
python pipeline/generate_deck.py --dry-run

# Generate Flagship Core (Opus 5) -- prefer authoring in-session; this is the unattended path
python pipeline/generate_deck.py --model opus-5 --batch flagship

# Generate Volume Deck (Sonnet 5 - Cost Efficient; also the default --model)
python pipeline/generate_deck.py --model sonnet-5 --batch volume

# Generate Volume Overflow (Gemini 3.1 Pro High)
python pipeline/generate_deck.py --model gemini-3.1-pro --batch volume

# Gemini 3.6 Flash High has NO batch route (no API key) -- run those sweeps from
# Antigravity, then verify the result here:
python pipeline/lint_content.py

# Run Engine Unit Tests (Antigravity)
python -m unittest discover -s tests

# Lint All Event Content (ids, flags, items, probability sanity)
python pipeline/lint_content.py

# Re-cut Scene Art from data/assets/originals/ (places-only bands -> data/assets/*.jpg)
python pipeline/crop_scenes.py

# Run Monte Carlo Balance Verification (single strategy)
python tests/sim_bot.py random

# Full Balance Regression Gate (all 4 strategies + assertions; CI-ready)
python tests/sim_bot.py all --assert

# Same Gate, Parallelized (~9 min vs ~28; GU_ROOT=<path> targets another worktree)
python tests/pargate.py

# Play Game Interactively (terminal)
python main.py

# Play Game in Browser (web UI with autosave at saves/autosave.json)
python server.py   # then open http://localhost:8000
```
