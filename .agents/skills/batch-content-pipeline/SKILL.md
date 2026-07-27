---
name: batch-content-pipeline
description: Orchestrate Anthropic Batch API calls for Opus 5 and Sonnet 5 to batch-generate and validate static JSON storylet decks with prompt caching.
---

# Batch Content Pipeline Skill

Use this skill when orchestrating build-time generation passes using Anthropic models (Opus 5 / Sonnet 5) or Gemini models.

## Model Selection Guidelines

- **Opus 5 (`opus-5` -> `claude-opus-5`)**: Flagship narrative chains, master faction bibles, and endgame resolution webs. Prefer authoring these in-session; use the batch path only for unattended bulk runs.
- **Sonnet 5 (`sonnet-5` -> `claude-sonnet-5`)**: Volume filler storylets (300+ events) and NPC dialogue expansion. This is `generate_deck.py`'s default `--model`.
- **Gemini 3.1 Pro High (`gemini-3.1-pro`)**: Volume overflow and high-context whole-deck validation.
- **Gemini 3.6 Flash High**: Ambient barks and bulk mechanical sweeps. **Not a `--model` choice** -- there is no API key for it; it runs interactively inside Antigravity, with `pipeline/lint_content.py` as the acceptance check.

Fable 5 and Opus 4.8 were retired from this project on 2026-07-27 and are no longer valid `--model` values.

## Execution Workflow

1. **Verify Prompt & Schema**:
   ```bash
   python pipeline/generate_deck.py --dry-run
   ```

2. **Execute Generation Call**:
   ```bash
   python pipeline/generate_deck.py --model opus-5 --batch flagship --output data/events/flagship_pack.json
   ```

3. **Validate and Test Main Loop**:
   Run `python -m unittest discover -s tests` to ensure newly added JSON files load cleanly and pass engine validation.
