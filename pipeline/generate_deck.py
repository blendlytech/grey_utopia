"""generate_deck.py -- Multi-Model Build-Time LLM Content Generator for GREY UTOPIA.
Includes model switching checkpoints, cost estimation, chunked batching,
markdown-fence-tolerant JSON parsing, cross-pack ID deduplication, and retries.
"""
from __future__ import annotations
import os
import re
import sys
import json
import glob
import argparse
from typing import Any, Dict, List, Optional, Set

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.events import load_events

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))

# Model Pricing Matrix (per Million Tokens). Rates of None are unconfirmed:
# estimate_cost returns None for those and the banner says so, rather than
# printing a made-up figure. Fill them in from the provider console.
#
# Gemini 3.6 Flash High is deliberately NOT listed here: it is driven
# interactively through Antigravity and there is no API key for it, so it has
# no batch route. Bulk mechanical sweeps on that model are run from the IDE,
# then verified with pipeline/lint_content.py like any other content pass.
PRICING_MATRIX = {
    "opus-5":         {"input": None, "output": None, "role": "Flagship Narrative, World Architecture & Balance Audit"},
    "sonnet-5":       {"input": 2.0,  "output": 10.0, "role": "Bulk Storylet Generation & Flavor Expansion"},
    "gemini-3.1-pro": {"input": 2.0,  "output": 12.0, "role": "Volume Overflow & High-Context Validation"},
}

# API model identifiers (kept separate from the friendly names above)
ANTHROPIC_MODEL_IDS = {
    "opus-5": "claude-opus-5",
    "sonnet-5": "claude-sonnet-5",
}
GEMINI_MODEL_IDS = {
    "gemini-3.1-pro": "gemini-3.1-pro",
}

EVENTS_PER_CHUNK = 8       # Small enough that a chunk never truncates
MAX_TOKENS_PER_CHUNK = 16000
MAX_RETRIES_PER_CHUNK = 2

SYSTEM_PROMPT = """You are a Lead World Builder and Game Writer for GREY UTOPIA, a gritty Quality-Based Narrative (QBN) life-sim set in a post-scarcity AI dystopia.
The world is governed by 'The Steward' -- an AI offering endless UBI and comfort, making human effort obsolete.
The player is an Underground Fixer in the undercity dealing in forbidden goods, off-grid identities, and synthetic vice.

Generate a JSON object under key "events" containing valid storylet cards adhering strictly to this schema:
- Each event MUST have: id (snake_case, unique), title, body (2-4 sentences of vivid second-person prose), weight (1-10), cooldown (days), max_fires (0=unlimited), tags (list), preconditions ({"all"/"any"/"none": [...]}, where each condition is EXACTLY one of {"stat": name, "op": op, "value": number} / {"flag": name, "value": true|false} / {"day": number, "op": op}; op is one of ">=", "<=", ">", "<", "==", "!=" -- NEVER words like "lte" or "gte"; in day conditions the "day" field holds the NUMBER), and >= 3 distinct choices.
- Every choice MUST have: id, text, and a "prob" key holding the hidden probability spec {"base": float 0..1, "mods": [{"stat": str, "coef": float}]} (coefs are multiplied by raw 0-100 stat values, so keep them in the -0.01..0.01 range). No choice may omit "prob" -- even trivial or safe choices need {"base": 1.0, "mods": []}.
- Valid stats: Wealth, Fame, Recklessness, Mental_Decay, Family_Friction, Substance_Reliance, Heat, Physical_Integrity, Social_Capital, Meaning, Tolerance.
- EXCEPTION -- Wealth is raw currency (typical bankroll ~50,000 credits), NOT 0-100. Wealth prob-mod coefs must stay within -0.00002..0.00002 (e.g. 1e-05), and Wealth deltas are in credits (e.g. +250, -1200).
- Every choice branch ("success" and "failure") MUST contain narrative "text" and stat "deltas". Branches may also set "flags_set"/"flags_clear".
- Fail-forward design: failure branches must move the story, not dead-end it.
Respond with ONLY the JSON object. No commentary, no markdown fences."""

FLAGSHIP_PROMPT = """Generate {n} complex flagship storylet cards in JSON under key "events" covering:
1. The Off-Grid Departure smuggling chain
2. Steward therapeutic surveillance interventions and buyout contracts
3. High-purity synthetic vice distribution and overdose risks
Ensure choices have intricate stat trade-offs and fail-forward outcomes.
Do NOT reuse any of these existing event ids: {existing_ids}"""

VOLUME_PROMPT = """Generate {n} standard volume storylet cards in JSON under key "events" covering ambient undercity jobs, minor vice vendors, family and relationship upkeep encounters, and Steward micro-interventions.
Do NOT reuse any of these existing event ids: {existing_ids}"""


def estimate_cost(model_name: str, input_tokens: int, output_tokens: int) -> Optional[float]:
    """Estimated USD cost, or None when this model's rates are unconfirmed."""
    rates = PRICING_MATRIX.get(model_name, {})
    if rates.get("input") is None or rates.get("output") is None:
        return None
    return (input_tokens / 1e6) * rates["input"] + (output_tokens / 1e6) * rates["output"]


def existing_event_ids() -> Set[str]:
    """Collect every event id already present in data/events/ for dedup."""
    ids: Set[str] = set()
    for filepath in glob.glob(os.path.join(DATA_DIR, "events", "*.json")):
        if os.path.basename(filepath) == "endings.json":
            continue
        try:
            with open(filepath, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            for e in data.get("events", data if isinstance(data, list) else []):
                if isinstance(e, dict) and "id" in e:
                    ids.add(e["id"])
        except (json.JSONDecodeError, OSError):
            continue
    return ids


def extract_json_object(raw: str) -> Dict[str, Any]:
    """Parse a JSON object out of an LLM response, tolerating markdown fences
    and leading/trailing prose."""
    text = raw.strip()
    # Strip ```json ... ``` fences if present
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    # Fall back to the outermost braces
    if not text.startswith("{"):
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("No JSON object found in model response")
        text = text[start:end + 1]
    return json.loads(text)


def generate_with_anthropic(model_key: str, api_key: str, prompt: str) -> str:
    try:
        import anthropic
    except ImportError:
        print("Please install the Anthropic SDK: pip install anthropic")
        sys.exit(1)
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=ANTHROPIC_MODEL_IDS[model_key],
        max_tokens=MAX_TOKENS_PER_CHUNK,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    # Models with adaptive thinking (e.g. Sonnet 5) may lead with thinking
    # blocks; the JSON payload lives in the text block(s).
    parts = [b.text for b in response.content if b.type == "text"]
    if not parts:
        raise ValueError(f"No text block in response (stop_reason={response.stop_reason})")
    return "".join(parts)


def generate_with_gemini(model_key: str, api_key: str, prompt: str) -> str:
    try:
        import google.generativeai as genai
    except ImportError:
        print("Please install google-generativeai SDK: pip install google-generativeai")
        sys.exit(1)
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(GEMINI_MODEL_IDS[model_key], system_instruction=SYSTEM_PROMPT)
    response = model.generate_content(prompt)
    return response.text


def generate_chunk(model_key: str, api_key: str, prompt: str) -> str:
    if "gemini" in model_key:
        return generate_with_gemini(model_key, api_key, prompt)
    return generate_with_anthropic(model_key, api_key, prompt)


def main():
    parser = argparse.ArgumentParser(description="Multi-Model Storylet Deck Generator for GREY UTOPIA")
    parser.add_argument("--model", default="sonnet-5", choices=list(PRICING_MATRIX.keys()), help="LLM Model choice")
    parser.add_argument("--batch", default="flagship", choices=["flagship", "volume"], help="Batch type to generate")
    parser.add_argument("--count", type=int, default=None, help="Total events to generate (default: 10 flagship / 20 volume)")
    parser.add_argument("--output", help="Custom output JSON path")
    parser.add_argument("--dry-run", action="store_true", help="Preview prompt and cost estimate")
    args = parser.parse_args()

    model_key = args.model
    batch_type = args.batch
    total_count = args.count or (10 if batch_type == "flagship" else 20)
    prompt_template = FLAGSHIP_PROMPT if batch_type == "flagship" else VOLUME_PROMPT
    output_path = args.output or os.path.join(DATA_DIR, "events", f"{model_key.replace('-', '_')}_{batch_type}_pack.json")

    known_ids = existing_event_ids()
    n_chunks = max(1, -(-total_count // EVENTS_PER_CHUNK))  # ceil division
    est_input_tokens = (len(SYSTEM_PROMPT) + len(prompt_template) + 20 * len(known_ids)) // 4 * n_chunks
    est_output_tokens = total_count * 1200  # ~1200 output tokens per full storylet
    est_cost = estimate_cost(model_key, est_input_tokens, est_output_tokens)

    print("\n" + "=" * 80)
    print("  GREY UTOPIA MULTI-MODEL GENERATION PIPELINE")
    print("=" * 80)
    print(f"  Target Model: {model_key.upper()} ({PRICING_MATRIX[model_key]['role']})")
    print(f"  API Model ID: {GEMINI_MODEL_IDS[model_key] if 'gemini' in model_key else ANTHROPIC_MODEL_IDS[model_key]}")
    print(f"  Batch:        {batch_type.upper()} -- {total_count} events in {n_chunks} chunk(s) of <= {EVENTS_PER_CHUNK}")
    cost_line = (f"~${est_cost:.2f} USD" if est_cost is not None
                 else "unavailable -- rates unconfirmed in PRICING_MATRIX")
    print(f"  Est. Cost:    {cost_line} (in ~{est_input_tokens:,} t, out ~{est_output_tokens:,} t)")
    print(f"  Existing IDs: {len(known_ids)} (will be excluded)")
    print(f"  Target File:  {output_path}")
    print("=" * 80 + "\n")

    if args.dry_run:
        print("=== DRY RUN COMPLETE ===")
        if model_key == "opus-5" and batch_type == "volume":
            print("  WARNING: Opus 5 is the costliest model in the roster; volume generation there")
            print("  is not cost-effective.")
            print("  RECOMMENDATION: python pipeline/generate_deck.py --model sonnet-5 --batch volume")
        return

    # Model Switching Checkpoint Rule
    if model_key == "opus-5" and batch_type == "volume":
        print("MODEL SWITCHING CHECKPOINT TRIGGERED")
        print("Opus 5 is reserved for flagship narrative architecture and balance audits.")
        print("  --> python pipeline/generate_deck.py --model sonnet-5 --batch volume\n")
        confirm = input("Override checkpoint and continue with Opus 5 anyway? (y/N): ").strip().lower()
        if confirm != "y":
            print("Generation halted by Model Switch Checkpoint.")
            sys.exit(0)

    # API Key Retrieval
    if "gemini" in model_key:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        key_name = "GEMINI_API_KEY"
    else:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        key_name = "ANTHROPIC_API_KEY"
    if not api_key:
        print(f"Error: {key_name} environment variable not set.")
        sys.exit(1)

    # Load any events already in the output file so re-runs append instead of clobber
    collected: List[dict] = []
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as fh:
                collected = json.load(fh).get("events", [])
            print(f"Resuming: {len(collected)} events already in {output_path}")
        except (json.JSONDecodeError, OSError):
            pass
    known_ids |= {e["id"] for e in collected if "id" in e}

    while len(collected) < total_count:
        want = min(EVENTS_PER_CHUNK, total_count - len(collected))
        prompt = prompt_template.format(n=want, existing_ids=", ".join(sorted(known_ids)) or "(none)")

        chunk_events: List[dict] = []
        for attempt in range(1, MAX_RETRIES_PER_CHUNK + 2):
            try:
                raw = generate_chunk(model_key, api_key, prompt)
                data = extract_json_object(raw)
                candidates = data.get("events", [])
                # Schema-validate each event individually through the real engine
                # loader so one malformed card doesn't void the whole chunk
                valid: List[dict] = []
                for e in candidates:
                    try:
                        load_events({"events": [e]})
                        valid.append(e)
                    except Exception as bad:
                        print(f"  Skipping invalid event {e.get('id', '?')}: {bad}")
                if not valid:
                    raise ValueError("no valid events in chunk")
                # Drop duplicates against everything we know
                fresh = [e for e in valid if e.get("id") not in known_ids]
                dropped = len(valid) - len(fresh)
                if dropped:
                    print(f"  Dropped {dropped} duplicate-id event(s) from chunk")
                chunk_events = fresh
                break
            except Exception as err:
                print(f"  Chunk attempt {attempt} failed: {err}")
                if attempt > MAX_RETRIES_PER_CHUNK:
                    print("  Giving up on this chunk after retries; saving what we have.")
        if not chunk_events:
            break

        collected.extend(chunk_events)
        known_ids |= {e["id"] for e in chunk_events}
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump({"events": collected}, fh, indent=2)
        print(f"  Progress: {len(collected)}/{total_count} events saved to {output_path}")

    print(f"\nDone. {len(collected)} schema-verified storylets in {output_path}")
    print("Next: python pipeline/lint_content.py  &&  python tests/sim_bot.py all --assert")

    # Post-Generation Checkpoint Guidance
    if model_key == "opus-5" and batch_type == "flagship":
        print("\n" + "-" * 80)
        print("MODEL SWITCH CHECKPOINT REACHED")
        print("Flagship narrative core completed with Opus 5!")
        print("Next Step: switch to Sonnet 5 / Gemini 3.1 Pro for volume expansion:")
        print("  --> python pipeline/generate_deck.py --model sonnet-5 --batch volume --count 60")
        print("-" * 80 + "\n")


if __name__ == "__main__":
    main()
