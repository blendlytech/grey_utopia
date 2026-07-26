"""Check ElevenLabs key validity and account capacity. Read-only — no audio is generated, no ElevenLabs credits spent."""
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("ELEVENLABS_API_KEY")
BASE_URL = "https://api.elevenlabs.io/v1"


def main() -> int:
    if not API_KEY:
        print("Error: ELEVENLABS_API_KEY not set (check .env).")
        return 1

    headers = {"xi-api-key": API_KEY}

    user_resp = requests.get(f"{BASE_URL}/user", headers=headers, timeout=15)
    if user_resp.status_code != 200:
        print(f"Key check failed: HTTP {user_resp.status_code} — {user_resp.text[:300]}")
        return 1

    user = user_resp.json()
    sub = user.get("subscription", {})
    print("=== ElevenLabs account ===")
    print(f"Tier: {sub.get('tier', 'unknown')}")
    print(f"Characters used: {sub.get('character_count')} / {sub.get('character_limit')}")
    print(f"Voice slots used: {sub.get('voice_slots_used')} / {sub.get('voice_limit')}")
    print(f"Can extend character limit: {sub.get('can_extend_character_limit')}")

    voices_resp = requests.get(f"{BASE_URL}/voices", headers=headers, timeout=15)
    if voices_resp.status_code == 200:
        voices = voices_resp.json().get("voices", [])
        print(f"\n=== Available voices ({len(voices)}) ===")
        for v in voices[:20]:
            print(f"- {v.get('name')} ({v.get('voice_id')}) [{v.get('category')}]")
    else:
        print(f"\nVoice list check failed: HTTP {voices_resp.status_code}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
