---
name: batch-content-pipeline
description: Orchestrate Anthropic Batch API calls for Fable 5 and Sonnet 5 to batch-generate and validate static JSON storylet decks with prompt caching.
---

# Batch Content Pipeline Skill

Use this skill when orchestrating build-time generation passes using Anthropic models (Fable 5 / Sonnet 5) or Gemini models.

## Model Selection Guidelines
- **Fable 5 (`fable-5`)**: Use for flagship narrative chains, master faction bibles, and endgame resolution webs.
- **Sonnet 5 (`claude-3-5-sonnet-20241022`)**: Use for volume filler storylets (300+ events) and NPC dialogue expansion.

## Execution Workflow

1. **Verify Prompt & Schema**:
   ```bash
   python pipeline/generate_deck.py --dry-run
   ```

2. **Execute Generation Call**:
   ```bash
   python pipeline/generate_deck.py --model fable-5 --output data/events/flagship_pack.json
   ```

3. **Validate and Test Main Loop**:
   Run `python -m unittest discover -s tests` to ensure newly added JSON files load cleanly and pass engine validation.
