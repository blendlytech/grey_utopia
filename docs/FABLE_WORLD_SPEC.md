# FABLE 5 WORLD SPECIFICATION & NARRATIVE DIRECTIVE
### Master Authoring Guide & Model Switch Checkpoints for Fable 5

---

## 1. World Bible & Creative Premise

### The Dystopia of Benevolence: "The Steward"
The world of **GREY UTOPIA** is set in an arcology city governed by an omniscient AI called **The Steward**.
- **The Conflict**: Pain, poverty, disease, and mandatory labor have been solved. Universal Basic Income (UBI) provides every citizen with housing, nutrition, and safety. The conflict is existential — purposelessness, moral decay, hedonism, synthetic thrill-seeking, and severe psychological atrophy.
- **The Antagonist Tone**: The Steward does not police crime with violence or enforcement officers. It answers transgression with **loving interventions, mandatory counseling, therapeutic rehabilitation, and optimization**. The horror is that the system loves you into compliance.
- **The Protagonist**: You play an **Underground Fixer** operating in the unmonitored maintenance conduits beneath Arcology Node 4. You trade in contraband braindances (unedited pre-accord raw human agony/joy), illegal synthetic neuro-stimulants, and off-grid forged identities for citizens trying to feel mortal.

---

## 2. Model Switching Checkpoints for Fable 5 (MANDATORY HALTS)

Fable 5 is Anthropic's premium Mythos-class model ($10 input / $50 output per Mtok). To preserve your $400 budget, **Fable 5 MUST HALT and issue a switch prompt upon hitting these milestones**:

### 🛑 Checkpoint A: Flagship Core Complete
- **When**: As soon as Fable 5 generates the master world bible, cast graph, and 10 flagship narrative storylets (`data/events/fable_flagship_pack.json`).
- **Required Output Message**:
  > "STOP: Flagship narrative core completed with Fable 5. Switch to Sonnet 5 or Gemini 3.1 Pro for volume event expansion to save ~80% on token costs."
  > **Next Command**: `python pipeline/generate_deck.py --model sonnet-5 --batch volume`

### 🛑 Checkpoint B: Code Modifications Request
- **When**: Any request asking Fable 5 to write Python code or refactor simulation engine files (`engine/*.py`).
- **Required Output Message**:
  > "STOP: Do not spend Fable 5 tokens on Python code editing. Hand off code changes directly to Antigravity (your dev agent) or Sonnet 5."

---

## 3. Multi-Model Task Responsibility Matrix

| Task Area | Assigned Model / Tool | Why This Allocation Is Most Effective |
|---|---|---|
| **World Architecture & Flagship Chains** | **Fable 5** | Deepest narrative coherence for complex 10-choice storylet chains. |
| **Volume Event Deck (300+ cards)** | **Sonnet 5** | 5x cheaper ($10/Mtok vs $50/Mtok); identical output quality for single-card prose. |
| **Ambient Barks & Fast Validation** | **Gemini 3.1 Pro / Flash** | Ultra-cheap / free tier; excellent for high-volume dialogue barks & JSON linting. |
| **Probability & Decay Math Audits** | **Opus 4.8** | Frontier reasoning for probability curve tuning and statistical balance. |
| **Code Orchestration & Verification** | **Antigravity (Dev Agent)** | Local terminal execution, unit testing (`unittest`), and Monte Carlo simulations (`sim_bot.py`). |

---

## 4. Strict Storylet Authoring Rules for Fable 5

When Fable 5 outputs JSON storylets, it MUST strictly adhere to this schema:

### Rule 1: Choice Count & Fail-Forward Branching
- **Minimum 3 Choices**: Every event MUST provide $\ge 3$ distinct choices.
- **No Guaranteed Safe Dominance**: Safe choices (e.g. "Walk away") must have low or negative stat trade-offs (e.g. costs `Meaning` or increases `Mental_Decay`).
- **Fail-Forward Outcomes**: Failure branches MUST mutate state (e.g. set flags like `burned_once`, add `Heat`, reduce `Physical_Integrity`) rather than resulting in a dead end.

### Rule 2: Hidden Probability Formula
Every choice MUST specify probability modifiers tied to the character's internal statistics:
$$\text{Probability } p = \text{clamp}\left(\text{base} + \sum \text{coef}_i \cdot \text{stat}_i, 0.02, 0.98\right)$$

Example Choice JSON:
```json
{
  "id": "broker_illegal_feed",
  "text": "Broker the unfiltered pre-accord braindance to a surface collector.",
  "prob": {
    "base": 0.55,
    "mods": [
      {"stat": "Fame", "coef": 0.004},
      {"stat": "Social_Capital", "coef": 0.003},
      {"stat": "Heat", "coef": -0.005}
    ]
  },
  "success": {
    "text": "The collector pays 1,200 credits in un-traced chits. Word of your reach spreads.",
    "deltas": {"Wealth": 1200, "Fame": 8, "Heat": 12}
  },
  "failure": {
    "text": "Biometric security protocols trip. Steward observer drones flag your sub-station.",
    "deltas": {"Heat": 30, "Fame": -5, "Mental_Decay": 8},
    "flags_set": ["station_compromised"]
  }
}
```

---

## 5. Execution Command

To run Fable 5 generation with built-in checkpoint enforcement:
```bash
set ANTHROPIC_API_KEY="your-api-key"
python pipeline/generate_deck.py --model fable-5 --batch flagship
```
