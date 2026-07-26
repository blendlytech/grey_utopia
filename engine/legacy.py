"""legacy.py -- Cross-run persistence: the Steward never forgets a cycle.

Endings are recorded to saves/legacy.json. New runs receive legacy_* flags so
content can react to what previous fixers did -- the city remembers the one
who crossed, the one who overdosed, the one who took the switch. The Monte
Carlo sim never calls into this module, so balance gates stay legacy-free.
"""
from __future__ import annotations
import os
import json
from typing import Dict, Any
from engine.stats import Character
from engine import paths

SAVES_DIR = os.path.join(paths.user_data_dir(), "saves")
LEGACY_PATH = os.path.join(SAVES_DIR, "legacy.json")

DATA_DIR = os.path.join(paths.app_root(), "data")
INHERITANCE_PATH = os.path.join(DATA_DIR, "legacy_inheritance.json")

# Knowledge-flags that persist across runs as legacy_echo_<flag> -- things a
# fixer wrote down or leaked into the rumor stratum, never feelings or
# relationships. First five already exist in the deck; the last three are
# minted by the legacy_pack/npc_arcs flagship events.
ECHO_FLAGS: frozenset[str] = frozenset({
    "kael_docket_memorized", "drawer_footprint_found", "tenant_ledger_studied",
    "legend_chased", "switch_logic_run", "winter_terms_read", "mask_dates_run",
    "resident_last_request_known",
})


def load() -> Dict[str, Any]:
    if os.path.exists(LEGACY_PATH):
        try:
            with open(LEGACY_PATH, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            pass
    return {"cycles": 0, "endings_seen": {}, "last_ending": ""}


def record_ending(ending_id: str, character: Character) -> None:
    data = load()
    data["cycles"] = int(data.get("cycles", 0)) + 1
    seen = data.setdefault("endings_seen", {})
    seen[ending_id] = int(seen.get(ending_id, 0)) + 1
    data["last_ending"] = ending_id
    echoes = set(data.get("echoes", [])) | (ECHO_FLAGS & character.flags)
    data["echoes"] = sorted(echoes)
    os.makedirs(SAVES_DIR, exist_ok=True)
    with open(LEGACY_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def apply_legacy_flags(character: Character) -> int:
    """Stamp a fresh character with flags describing previous cycles.

    Returns the completed-cycle count. Flags minted:
      legacy_cycle2plus            -- at least one previous run concluded
      legacy_<ENDING_ID>           -- that ending has been reached before
      legacy_last_<ENDING_ID>      -- the immediately previous run's ending
      legacy_echo_<FLAG>           -- knowledge that escaped into the world
    """
    data = load()
    cycles = int(data.get("cycles", 0))
    if cycles >= 1:
        character.flags.add("legacy_cycle2plus")
        for ending_id in data.get("endings_seen", {}):
            character.flags.add(f"legacy_{ending_id}")
        if data.get("last_ending"):
            character.flags.add(f"legacy_last_{data['last_ending']}")
        for echo in data.get("echoes", []):
            character.flags.add(f"legacy_echo_{echo}")
    return cycles


def apply_legacy_inheritance(character: Character) -> Dict[str, Any]:
    """Adjust a fresh character's starting arithmetic from the prior run's ending.

    Reads last_ending from saves/legacy.json; if it keys an entry in
    data/legacy_inheritance.json, applies that entry's stat_deltas (via
    character.apply_deltas, which clamps and skips unknown stats),
    faction_deltas (via character.add_faction), and rel_deltas (via
    character.adjust_relationship, only for relationships that already exist
    on the character). Returns the applied entry, or {} when nothing applied.
    A missing or corrupt inheritance table is a silent no-op, like load().
    """
    data = load()
    last_ending = data.get("last_ending")
    if int(data.get("cycles", 0)) < 1 or not last_ending:
        return {}

    if not os.path.exists(INHERITANCE_PATH):
        return {}
    try:
        with open(INHERITANCE_PATH, "r", encoding="utf-8") as fh:
            table = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {}

    entry = table.get(last_ending)
    if not entry:
        return {}

    character.apply_deltas(entry.get("stat_deltas", {}))
    for faction, delta in entry.get("faction_deltas", {}).items():
        character.add_faction(faction, delta)
    for name, delta in entry.get("rel_deltas", {}).items():
        if name in character.relationships:
            character.adjust_relationship(name, delta)

    return entry
