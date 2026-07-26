"""Generate the web UI sound-effect set via the ElevenLabs sound-generation API.

One-time build step: writes MP3s to web/audio/. Files that already exist are
skipped, so re-running never spends credits on cues you already have.
Cost is ~25 ElevenLabs credits per second of requested audio (~740 for the
full set). Use --dry-run to preview, --force to regenerate, --only NAME for
a single cue.
"""
import argparse
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("ELEVENLABS_API_KEY")
SFX_URL = "https://api.elevenlabs.io/v1/sound-generation"
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "audio")

CREDITS_PER_SECOND = 25

# name -> (prompt, duration_seconds). Names must match SFX kinds in web/app.js.
MANIFEST = {
    "click": (
        "Single soft muted synthetic interface click, one short clean tap, "
        "minimal dark sci-fi UI blip, dry, no reverb tail",
        0.6,
    ),
    "success": (
        "Short two-note rising synth chime, warm but restrained, subtle hopeful "
        "confirmation tone for a dark ambient sci-fi interface",
        1.5,
    ),
    "failure": (
        "Short low distorted descending synth buzz, dull thud of denial, "
        "failure tone for a bleak dystopian interface, no melody",
        1.5,
    ),
    "day": (
        "Soft distant tolling bell with a faint synthetic hum underneath, "
        "melancholic new-day transition in a sterile utopian city, sparse",
        2.0,
    ),
    "ending-good": (
        "Warm slowly swelling ambient synth chord resolving upward, bittersweet "
        "hopeful cinematic finale, gentle fade out",
        4.0,
    ),
    "ending-neutral": (
        "Ambiguous suspended ambient synth chord that never resolves, quiet "
        "melancholy cinematic finale, slow fade to silence",
        4.0,
    ),
    "ending-terminal": (
        "Deep ominous descending drone with distant sub rumble, grim final "
        "collapse into silence, dark cinematic ending",
        4.0,
    ),
    "ambient": (
        "Seamless looping room tone of a vast sealed arcology interior: low "
        "machinery hum, distant air recyclers, faint deep electrical drone, "
        "sterile and calm, no melody, no voices, constant level",
        12.0,
    ),
    # --- dramatic one-shots ---
    "overdose": (
        "Muffled slowing heartbeat with a high tinnitus ring rising over it, "
        "sounds smearing as if underwater, collapse into blackout, no music",
        3.0,
    ),
    "heat-alarm": (
        "Distant institutional alarm klaxon, two slow pulses muffled through "
        "walls, cold surveillance dread, dark sci-fi, no music",
        2.0,
    ),
    "clock-critical": (
        "Single dry mechanical clock tick followed by one low tense pulse, "
        "deadline warning for a minimal dark interface, short and quiet",
        1.0,
    ),
    "clock-expired": (
        "Single dull heavy bell toll with a short dark reverb tail, "
        "time has run out, somber and final, no music",
        2.0,
    ),
    # --- texture one-shots ---
    "purchase": (
        "Short synthetic credit-transfer chirp, two quick soft digital blips "
        "confirming a transaction, minimal dark sci-fi interface, dry",
        1.0,
    ),
    "rest": (
        "Heavy metal door bolt sliding shut, then one slow tired human "
        "exhale in a quiet small room, intimate and close, no music",
        2.0,
    ),
    "ledger-tick": (
        "Single very soft dry data tick, tiny terminal keystroke blip, "
        "minimal and quiet, no reverb",
        0.5,
    ),
    "warning": (
        "Low ominous two-note medical monitor alert, muffled and dark, "
        "quiet dread, no melody, short",
        1.5,
    ),
    "contact-new": (
        "Two soft warm short synth blips, gentle understated notification of "
        "a new connection, dark sci-fi interface, quiet",
        1.0,
    ),
    # --- per-scene ambient loops (hideout uses the base "ambient" bed) ---
    "ambient-street": (
        "Seamless looping ambient of a desolate dystopian city street at "
        "night: soft wind between towers, distant traffic hum, faint drone "
        "passing overhead, sparse and lonely, no voices, constant level",
        12.0,
    ),
    "ambient-steward": (
        "Seamless looping ambient of a pristine AI administrative tower "
        "interior: soft air-conditioning white noise, faint pure electronic "
        "hum, occasional gentle system pulse, sterile serene unsettling calm, "
        "no voices, constant level",
        12.0,
    ),
    "ambient-vice": (
        "Seamless looping ambient of a hidden underground den: muffled bass "
        "music throbbing through a wall, low indistinct crowd murmur, faint "
        "glass clinks and electrical buzz, close and smoky, no clear voices, "
        "constant level",
        12.0,
    ),
    "ambient-offgrid": (
        "Seamless looping ambient of an off-grid wilderness edge at night: "
        "soft wind in dry grass, sparse distant insects, faint creak of a "
        "metal shelter, no machinery, natural quiet, constant level",
        12.0,
    ),
}


def generate(name: str, prompt: str, seconds: float) -> bool:
    resp = requests.post(
        SFX_URL,
        headers={"xi-api-key": API_KEY},
        json={"text": prompt, "duration_seconds": seconds, "prompt_influence": 0.3},
        timeout=120,
    )
    if resp.status_code != 200:
        print(f"  FAILED {name}: HTTP {resp.status_code} — {resp.text[:300]}")
        return False
    path = os.path.join(OUT_DIR, f"{name}.mp3")
    with open(path, "wb") as f:
        f.write(resp.content)
    print(f"  wrote {path} ({len(resp.content)} bytes)")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="list what would be generated and the credit cost")
    parser.add_argument("--force", action="store_true", help="regenerate cues even if the MP3 already exists")
    parser.add_argument("--only", metavar="NAME", help="generate a single cue by name")
    args = parser.parse_args()

    if args.only and args.only not in MANIFEST:
        print(f"Unknown cue '{args.only}'. Choices: {', '.join(MANIFEST)}")
        return 1

    names = [args.only] if args.only else list(MANIFEST)
    pending = []
    for name in names:
        path = os.path.join(OUT_DIR, f"{name}.mp3")
        if os.path.exists(path) and not args.force:
            print(f"  skip {name} (exists: {path})")
        else:
            pending.append(name)

    total_seconds = sum(MANIFEST[n][1] for n in pending)
    est = int(total_seconds * CREDITS_PER_SECOND)
    print(f"\n{len(pending)} cue(s) to generate, ~{total_seconds:.1f}s of audio, ~{est} credits.")

    if args.dry_run or not pending:
        return 0
    if not API_KEY:
        print("Error: ELEVENLABS_API_KEY not set (check .env).")
        return 1

    os.makedirs(OUT_DIR, exist_ok=True)
    failures = 0
    for name in pending:
        prompt, seconds = MANIFEST[name]
        print(f"Generating {name} ({seconds}s)...")
        if not generate(name, prompt, seconds):
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
