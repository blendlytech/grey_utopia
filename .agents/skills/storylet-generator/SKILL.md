---
name: storylet-generator
description: Generate, lint, and validate new quality-based narrative (QBN) JSON storylet cards for GREY UTOPIA adhering to the strict 3-choice fail-forward schema.
---

# Storylet Generator Skill

This skill provides step-by-step instructions for creating new storylets for GREY UTOPIA.

## Storylet Schema Requirements

Every storylet must strictly follow this JSON format:

```json
{
  "id": "unique_string_id",
  "title": "Atmospheric Title",
  "body": "Concise gritty narrative text...",
  "weight": 10.0,
  "cooldown": 3,
  "max_fires": 0,
  "tags": ["job", "undercity"],
  "preconditions": {
    "all": [{"stat": "Heat", "op": ">=", "value": 10.0}],
    "any": [],
    "none": [{"flag": "client_dead"}]
  },
  "choices": [
    {
      "id": "choice_1",
      "text": "Action text",
      "prob": {
        "base": 0.6,
        "mods": [{"stat": "Recklessness", "coef": 0.003}]
      },
      "success": {
        "text": "Outcome narrative text...",
        "deltas": {"Wealth": 200, "Fame": 5}
      },
      "failure": {
        "text": "Fail-forward outcome text...",
        "deltas": {"Heat": 15, "Physical_Integrity": -10},
        "flags_set": ["burned_once"]
      }
    },
    { "id": "choice_2", "text": "...", "prob": {"base": 0.5, "mods": []} },
    { "id": "choice_3", "text": "Refuse / Walk away...", "prob": {"base": 1.0, "mods": []} }
  ]
}
```

## Mandatory Rules
1. Minimum 3 distinct choices per event.
2. Every choice must specify `prob` with a `base` probability and `mods` list.
3. Deltas must use valid stat names: `Wealth`, `Fame`, `Recklessness`, `Mental_Decay`, `Family_Friction`, `Substance_Reliance`, `Heat`, `Physical_Integrity`, `Social_Capital`, `Meaning`, `Tolerance`.
4. Validate generated files by running `python -c "from engine.events import load_events; load_events('data/events/your_file.json')"`
