# CLAUDE.md -- GREY UTOPIA Development & Multi-Model Pipeline Directives

This document provides system instructions for Claude models (Fable 5, Sonnet 5, Opus 4.8), Gemini 3.1 models, and the Antigravity dev agent operating on **GREY UTOPIA**, a gritty single-player text RPG / life-sim Quality-Based Narrative (QBN) engine set in a post-scarcity AI dystopia ("The Steward").

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
     │  Fable 5 ($10/$50 Mtok)       │  │  Opus 4.8 ($5/$25 Mtok)       │
     │  - Master World Bible         │  │  - Stat curve tuning          │
     │  - Flagship 10-choice chains  │  │  - Ending outcome balance     │
     │                               │  │                               │
     │  Sonnet 5 ($2/$10 Mtok)       │  │  Gemini 3.1 Pro ($2/$12 Mtok)│
     │  - 300+ Volume storylets      │  │  - Ambient text & barks       │
     │  - NPC relationship encounters│  │  - Fast JSON schema linting   │
     └───────────────────────────────┘  └───────────────────────────────┘
```

---

## 2. Mandatory Model Switch Checkpoints (STOP & REPORT)

LLMs and dev agents MUST halt and notify the user when reaching these explicit checkpoints:

### 🛑 Checkpoint 1: Flagship Core Completion
- **Trigger**: When Fable 5 completes generating the master world bible and 10 flagship narrative storylets (`data/events/fable_flagship_pack.json`).
- **Action**: **STOP GENERATION AND NOTIFY USER**:
  > "Flagship narrative core completed with Fable 5. Switch to Sonnet 5 or Gemini 3.1 Pro for high-volume expansion to save ~80% on token cost."
  > **Command**: `python pipeline/generate_deck.py --model sonnet-5 --batch volume`

### 🛑 Checkpoint 2: Volume Deck Completion
- **Trigger**: When Sonnet 5 or Gemini 3.1 finishes generating 100+ volume events.
- **Action**: **STOP AND HAND OFF TO ANTIGRAVITY**:
  > "Volume event deck generated. Handing off to Antigravity to run unit tests and Monte Carlo strategy simulation."
  > **Command**: `python tests/sim_bot.py random`

### 🛑 Checkpoint 3: Code Modification Directive
- **Trigger**: Any request to modify Python simulation code (`engine/*.py` or `ui/*.py`).
- **Action**: **DO NOT USE FABLE 5 FOR PYTHON CODE EDITS**. Hand off code modifications directly to **Antigravity** or **Sonnet 5**.

---

## 3. Cost & Model Matrix

| Model | Cost (In / Out) | Primary Assignment | Efficiency Rule |
|---|---|---|---|
| **Fable 5** | $10 / $50 per Mtok | Master World Bible & Flagship Storylets | Limit usage to flagship chains; NEVER use for volume prose. |
| **Sonnet 5** | $2 / $10 per Mtok | Volume Event Cards & NPC Dialogue | Primary workhorse; 5x cheaper than Fable 5. |
| **Gemini 3.1 Pro** | $2 / $12 per Mtok | Ambient Barks & Schema Validation | High-context validation & rapid localization. |
| **Opus 4.8** | $5 / $25 per Mtok | Probability Formula & Balance Audits | Math & balance tuning. |
| **Antigravity** | Local Dev Agent | Code execution, testing, file management | Free local execution & environment runner. |

---

## 4. Execution Command Reference

```bash
# Preview generation prompt & cost estimate
python pipeline/generate_deck.py --dry-run

# Generate Flagship Core (Fable 5)
python pipeline/generate_deck.py --model fable-5 --batch flagship

# Generate Volume Deck (Sonnet 5 - Cost Efficient)
python pipeline/generate_deck.py --model sonnet-5 --batch volume

# Generate Ambient Barks (Gemini 3.1 Pro)
python pipeline/generate_deck.py --model gemini-3.1-pro --batch volume

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
