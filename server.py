"""server.py -- Lightweight REST API Server & Web UI host for GREY UTOPIA.
Hooks directly into the Python QBN engine (engine/).
"""
from __future__ import annotations
import os
import json
import random
import glob
import re
import uuid
import threading
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

from engine.stats import create_starter_fixer, Character
from engine.events import Event, load_events
from engine.selector import select_event, is_ambient, ambient_budget_for, district_for_slot
from engine.districts import (
    apply_placements, clear_placements, district_hint, load_districts
)
from engine.resolver import (
    choice_probability, resolve_choice, check_endings,
    eligible_choices, build_epilogue, build_run_memories,
    desperation_edge, apply_rest
)
from engine import resolver as resolver_module
from engine import legacy
from engine import paths
from engine import steward
from engine.decay import end_of_day_decay, compute_daily_stress, build_day_report
from engine.ambient import morning_report, steward_ledger_line

PORT = 8000
BASE_DIR = paths.app_root()
DATA_DIR = os.path.join(BASE_DIR, "data")
WEB_DIR = os.path.join(BASE_DIR, "web")
ASSETS_DIR = os.path.join(DATA_DIR, "assets")
IMAGE_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
               ".png": "image/png", ".webp": "image/webp"}
SAVES_DIR = os.path.join(paths.user_data_dir(), "saves")
AUTOSAVE_PATH = os.path.join(SAVES_DIR, "autosave.json")

# Bumped only when the session payload's *meaning* changes, not when a field is
# merely added (tolerant .get(key, default) reads already handle that). A save
# with no version is treated as v0 and adopted silently; one with a version
# greater than this build knows is refused rather than tolerant-read, since a
# newer shape read by an older reader is exactly what a missing-key default
# cannot detect. See docs/BACKLOG_HANDOFF.md SHIP item, Step 3 (save-versioning
# proposal), for the full reasoning.
SAVE_FORMAT_VERSION = 1

# Manual save slots live beside autosave.json in the same directory as
# legacy.json (engine/legacy.py). Filenames are never derived from the
# player-chosen display name -- that name lives inside the file instead --
# so a slot cannot collide with legacy.json/autosave.json or escape SAVES_DIR
# via "/" or "..", and Windows-reserved names (CON, NUL, PRN, AUX...) are moot.
SLOT_ID_RE = re.compile(r"^[0-9a-f]{12}$")
SLOT_FILENAME_RE = re.compile(r"^slot_([0-9a-f]{12})\.json$")


def _slot_path(slot_id: str) -> str:
    return os.path.join(SAVES_DIR, f"slot_{slot_id}.json")


def list_slots() -> list[dict]:
    """Every manual save, discovered by scanning SAVES_DIR -- no separate index
    file to keep in sync or corrupt. Metadata (name, day, ending, timestamp)
    is read out of each slot file itself."""
    if not os.path.isdir(SAVES_DIR):
        return []
    out = []
    for filepath in glob.glob(os.path.join(SAVES_DIR, "slot_*.json")):
        m = SLOT_FILENAME_RE.fullmatch(os.path.basename(filepath))
        if not m:
            continue
        try:
            with open(filepath, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            char = data.get("character") or {}
            out.append({
                "id": m.group(1),
                "name": ((data.get("slot_meta") or {}).get("name")) or "Unnamed run",
                "saved_at": data.get("saved_at", ""),
                "day": int(char.get("day", 0)),
                "ending": char.get("ending") or None,
            })
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            continue  # a corrupt slot file just doesn't appear in the list
    out.sort(key=lambda s: s["saved_at"], reverse=True)
    return out


def delete_slot(slot_id: str) -> bool:
    if not SLOT_ID_RE.fullmatch(slot_id or ""):
        raise ValueError("Invalid slot id.")
    path = _slot_path(slot_id)
    if os.path.isfile(path):
        os.remove(path)
        return True
    return False


# Global Game Session State
class GameSession:
    def __init__(self):
        self.rng = random.Random()
        self.character: Character = create_starter_fixer()
        self.cycles: int = legacy.apply_legacy_flags(self.character)
        if legacy.apply_legacy_inheritance(self.character):
            print("[The file precedes you. The city has adjusted your terms.]")
        self.events: list[Event] = self.load_all_events()
        self.endings_db: dict = self.load_endings()
        self.current_event: Event | None = None
        self.current_slots: int = 3
        self.used_slots_today: int = 0
        self.fired_today: set[str] = set()
        self.ambient_today: int = 0
        # A1: the day is gated on the morning placement step until the player
        # has said where they are working. The placement itself lives on the
        # character (so it saves with everything else); this flag is only "has
        # today's step been answered yet", and it is what makes advance_event
        # hold off on drawing a storylet for a slot whose district is not
        # decided. Drawing first and placing after would mean the placement
        # never reached the draw it was for.
        self.awaiting_placement: bool = True
        self.last_outcome: dict | None = None
        self.day_report: dict | None = None
        self.last_day_report: dict | None = None
        self.last_saved_at: str | None = None
        if not self.load_state():
            self.advance_event()

    def load_all_events(self) -> list[Event]:
        events_dir = os.path.join(DATA_DIR, "events")
        all_evs = []
        for filepath in glob.glob(os.path.join(events_dir, "*.json")):
            if os.path.basename(filepath) == "endings.json":
                continue
            all_evs.extend(load_events(filepath))
        return all_evs

    def load_endings(self) -> dict:
        endings_file = os.path.join(DATA_DIR, "events", "endings.json")
        if os.path.exists(endings_file):
            with open(endings_file, "r", encoding="utf-8") as fh:
                return json.load(fh).get("endings", {})
        return {}

    def calculate_slots(self) -> int:
        slots = 3
        if self.character.get("Physical_Integrity") < 30.0 or self.character.get("Mental_Decay") > 80.0:
            slots -= 1
        return max(1, slots)

    def _session_payload(self) -> dict:
        """The one save shape, shared by autosave and every manual slot. A
        slot file is this payload plus a "slot_meta" block (see save_slot)."""
        return {
            "version": SAVE_FORMAT_VERSION,
            "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "character": json.loads(self.character.to_json()),
            "used_slots_today": self.used_slots_today,
            "fired_today": sorted(self.fired_today),
            "ambient_today": self.ambient_today,
            "awaiting_placement": self.awaiting_placement,
            "event_state": {
                e.id: {"fire_count": e.fire_count, "last_fired_day": e.last_fired_day}
                for e in self.events if e.fire_count > 0 or e.last_fired_day > -9999
            },
            "current_event_id": self.current_event.id if self.current_event else None,
        }

    def _apply_session_payload(self, data: dict) -> None:
        """Shared by autosave restore and slot load. A version newer than this
        build knows is refused (raises ValueError) rather than tolerant-read --
        see SAVE_FORMAT_VERSION. Missing/0 is adopted silently, same as every
        other field here defaults via .get()."""
        version = int(data.get("version") or 0)
        if version > SAVE_FORMAT_VERSION:
            raise ValueError(
                f"save is format v{version}; this build only supports up to v{SAVE_FORMAT_VERSION}"
            )
        self.character = Character.from_dict(data["character"])
        self.used_slots_today = int(data.get("used_slots_today", 0))
        self.fired_today = set(data.get("fired_today", []))
        self.ambient_today = int(data.get("ambient_today", 0))
        # A save written before A1 Phase 2 has no placement in it. Default to
        # "already answered" rather than re-opening the step, so restoring an
        # old autosave drops the player back into the day it saved instead of
        # into a placement screen for a day that is half spent.
        self.awaiting_placement = bool(data.get("awaiting_placement", False))
        event_state = data.get("event_state", {})
        for e in self.events:
            st = event_state.get(e.id)
            if st:
                e.fire_count = int(st.get("fire_count", 0))
                e.last_fired_day = int(st.get("last_fired_day", -9999))
            else:
                # This may be replacing a live run's fire counts (slot load),
                # not just populating a fresh process, so an event this
                # payload is silent about must be cleared, not left as-is.
                e.fire_count = 0
                e.last_fired_day = -9999
        self.current_slots = self.calculate_slots()
        wanted = data.get("current_event_id")
        self.current_event = next((e for e in self.events if e.id == wanted), None)
        self.last_saved_at = data.get("saved_at")

    def save_state(self) -> None:
        os.makedirs(SAVES_DIR, exist_ok=True)
        payload = self._session_payload()
        with open(AUTOSAVE_PATH, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        self.last_saved_at = payload["saved_at"]

    def load_state(self) -> bool:
        if not os.path.exists(AUTOSAVE_PATH):
            return False
        try:
            with open(AUTOSAVE_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self._apply_session_payload(data)
            if self.current_event is None and not self.character.dead:
                self.advance_event()
            print(f"Restored autosave: Day {self.character.day}, "
                  f"{len(data.get('event_state', {}))} event states.")
            return True
        except (KeyError, ValueError, json.JSONDecodeError, OSError) as err:
            print(f"Autosave restore failed ({err}); starting fresh.")
            return False

    def save_slot(self, name: str) -> dict:
        """Write the current run to a new, opaquely-named slot file. The
        player's display name lives inside the file (slot_meta), never in the
        filename -- see the module-level comment above SLOT_ID_RE."""
        os.makedirs(SAVES_DIR, exist_ok=True)
        slot_id = uuid.uuid4().hex[:12]
        payload = self._session_payload()
        payload["slot_meta"] = {
            "name": (name or f"Day {self.character.day + 1}").strip()[:60] or "Unnamed run",
        }
        with open(_slot_path(slot_id), "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        return {
            "id": slot_id,
            "name": payload["slot_meta"]["name"],
            "saved_at": payload["saved_at"],
            "day": self.character.day,
            "ending": self.character.ending or None,
        }

    def load_slot(self, slot_id: str) -> None:
        """Replace the live session with a manual slot's contents. The caller
        (the /api/saves/load route) is responsible for then calling
        save_state() so the loaded run becomes the new autosave -- loading a
        slot is a real, if sharp, replacement of the in-progress run, and the
        web UI gates it behind an explicit confirm step for that reason."""
        if not SLOT_ID_RE.fullmatch(slot_id or ""):
            raise ValueError("invalid slot id")
        path = _slot_path(slot_id)
        if not os.path.isfile(path):
            raise FileNotFoundError("slot not found")
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        self._apply_session_payload(data)
        self.last_outcome = None
        self.day_report = None
        self.last_day_report = None
        if self.current_event is None and not self.character.dead:
            self.advance_event()

    def advance_event(self):
        self.day_report = None
        self.current_slots = self.calculate_slots()
        ending = check_endings(self.character)
        if ending:
            self.character.ending = ending
            self.character.dead = True
            legacy.record_ending(ending, self.character)
            self.current_event = None
            return

        if self.used_slots_today >= self.current_slots:
            # End of day decay -- snapshot first so the night's work is legible
            stats_before = dict(self.character.stats)
            clocks_before = set(self.character.clocks)
            stress = compute_daily_stress(self.character, self.rng)
            end_of_day_decay(self.character, stress_today=stress)
            self.used_slots_today = 0
            self.fired_today.clear()
            self.ambient_today = 0
            # A new day is a new placement. Yesterday's districts do not carry.
            clear_placements(self.character)
            # A3: and a new day is either a filing day or not. Same day-boundary
            # slot as the placement reset, for the same reason -- one call site
            # per loop, so main.py and this loop cannot drift on per-day state.
            steward.begin_day(self.character)
            self.awaiting_placement = bool(load_districts())
            self.current_slots = self.calculate_slots()
            self.day_report = build_day_report(self.character, stress, stats_before, clocks_before)
            self.last_day_report = self.day_report

            ending = check_endings(self.character)
            if ending:
                self.character.ending = ending
                self.character.dead = True
                legacy.record_ending(ending, self.character)
                self.current_event = None
                return

        # Hold the draw until the morning placement step has been answered: the
        # storylet for a slot depends on where that slot is standing.
        if self.awaiting_placement:
            self.current_event = None
            return

        # Pick the next storylet, skipping any whose choices are all locked
        # (a soft-lock guard; the linter forbids authoring such events).
        skip = set(self.fired_today)
        budget = ambient_budget_for(self.ambient_today)
        district = district_for_slot(self.character, self.used_slots_today)
        for _ in range(8):
            candidate = select_event(
                self.events, self.character, self.character.day, self.rng,
                exclude_ids=skip, ambient_budget=budget, district=district
            )
            if candidate is None or eligible_choices(candidate.choices, self.character):
                self.current_event = candidate
                return
            skip.add(candidate.id)
        self.current_event = None

    def reset(self):
        self.character = create_starter_fixer()
        self.cycles = legacy.apply_legacy_flags(self.character)
        if legacy.apply_legacy_inheritance(self.character):
            print("[The file precedes you. The city has adjusted your terms.]")
        self.used_slots_today = 0
        self.fired_today = set()
        self.ambient_today = 0
        self.awaiting_placement = bool(load_districts())
        self.last_outcome = None
        self.day_report = None
        self.last_day_report = None
        self.last_saved_at = None
        # One-shot storylets must come back for a new run
        for e in self.events:
            e.fire_count = 0
            e.last_fired_day = -9999
        if os.path.exists(AUTOSAVE_PATH):
            try:
                os.remove(AUTOSAVE_PATH)
            except OSError:
                pass
        self.advance_event()

    def get_state_dict(self) -> dict:
        ending_data = None
        if self.character.ending:
            raw = self.endings_db.get(self.character.ending, {
                "title": f"GAME OVER: {self.character.ending}",
                "text": "Your journey in the Grey Utopia has concluded."
            })
            ending_data = {
                "title": raw.get("title"),
                "text": raw.get("text"),
                "epilogue": build_epilogue(raw, self.character),
                "memories": build_run_memories(self.character),
            }

        event_data = None
        if self.current_event and not self.character.dead:
            visible = eligible_choices(self.current_event.choices, self.character)
            event_data = {
                "id": self.current_event.id,
                "title": self.current_event.title,
                "body": self.current_event.compose_body(self.character),
                "tags": self.current_event.tags,
                "choices": [
                    {
                        "id": ch.id,
                        "text": ch.text,
                        "prob": round(choice_probability(ch, self.character) * 100, 1),
                        "unlocked": bool(ch.requires),
                        "boosted": bool(
                            [i for i in ch.boost_items if self.character.has_item(i)]
                        ),
                        # Which stats move these odds, and in which direction --
                        # the quality being tested, never the exact math.
                        "checks": [
                            {"stat": m["stat"], "dir": 1 if float(m.get("coef", 0)) > 0 else -1}
                            for m in (ch.prob or {}).get("mods", [])
                            if m.get("stat") and float(m.get("coef", 0)) != 0
                        ],
                        "gamble": bool(ch.failure),
                    }
                    for ch in visible
                ]
            }

        return {
            "day": self.character.day,
            "cycle": self.cycles + 1,
            "slots_total": self.current_slots,
            "slots_used": self.used_slots_today,
            "edge": round(desperation_edge(self.character) * 100),
            "dead": self.character.dead,
            "ending": self.character.ending,
            "ending_info": ending_data,
            "stats": self.character.stats,
            "flags": sorted(self.character.flags),
            "inventory": self.character.inventory,
            "factions": self.character.factions,
            "clocks": self.character.clocks,
            "relationships": [
                {
                    "name": r.name,
                    "satisfaction": round(r.satisfaction, 1),
                    "strength": round(r.strength, 1)
                }
                for r in self.character.relationships.values()
            ],
            "event": event_data,
            "placement": None if self.character.dead else {
                "awaiting": self.awaiting_placement,
                "slots": self.current_slots,
                # slot index -> district id, as strings so the JSON object round
                # trips; the client echoes this shape straight back to /api/place.
                "assigned": {str(k): v for k, v in self.character.placements.items()},
                "districts": [
                    {
                        "id": d["id"],
                        "name": d["name"],
                        "blurb": d.get("blurb", ""),
                        "hint": district_hint(self.events, self.character, d["id"]),
                    }
                    for d in load_districts()
                ],
            },
            "ambient": None if self.character.dead else {
                "morning_report": morning_report(self.character),
                "ledger_line": steward_ledger_line(self.character, self.last_day_report),
            },
            # A3: the file, for #steward-panel. `open` is the hidden-until-relevant
            # switch, following #clocks-panel / #threads-panel: the panel appears
            # the first time the Steward writes anything down, which for most runs
            # is the first few days. `notice` is None outside the countdown window
            # (steward.NOTICE_LEAD_DAYS), and the panel's countdown row keys off
            # that rather than off `days_until`, so the sidebar says "in 2 days"
            # exactly when the morning line in the terminal front end does.
            "steward": None if self.character.dead else {
                "open": steward.file_weight(self.character) > 0,
                "entries": steward.file_weight(self.character),
                "tier": steward.tier_of(self.character)[0],
                "tier_name": steward.tier_of(self.character)[1],
                "days_until": steward.days_until_filing(self.character.day),
                "notice": steward.filing_notice(self.character),
            },
            "last_outcome": self.last_outcome,
            "day_report": self.day_report,
            "last_saved_at": self.last_saved_at,
        }


session = GameSession()
# One lock around all state-mutating API work: the server is threaded for
# snappy static-file serving, but the game session itself stays serial.
session_lock = threading.Lock()


def load_item_catalog() -> list:
    items_file = os.path.join(DATA_DIR, "items.json")
    if os.path.exists(items_file):
        with open(items_file, "r", encoding="utf-8") as fh:
            return json.load(fh).get("items", [])
    return []


ITEM_CATALOG = load_item_catalog()


class GreyUtopiaRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/state":
            with session_lock:
                st = session.get_state_dict()
                st["catalog"] = ITEM_CATALOG
            self.send_json(st)
            return

        # Serve visual scene assets. basename() keeps this flat: the crops live
        # directly in data/assets and assets/originals/ stays unreachable.
        if parsed.path.startswith("/assets/"):
            asset_name = os.path.basename(parsed.path)
            asset_path = os.path.join(ASSETS_DIR, asset_name)
            if os.path.isfile(asset_path):
                self.send_file(asset_path, IMAGE_TYPES.get(
                    os.path.splitext(asset_name)[1].lower(), "application/octet-stream"))
                return

        # Serve Web UI files
        rel_path = parsed.path.lstrip("/")
        if not rel_path:
            rel_path = "index.html"
        target_file = os.path.join(WEB_DIR, rel_path)

        if os.path.exists(target_file) and os.path.isfile(target_file):
            content_type = "text/html"
            if target_file.endswith(".css"): content_type = "text/css"
            elif target_file.endswith(".js"): content_type = "application/javascript"
            elif target_file.endswith(".png"): content_type = "image/png"
            elif target_file.endswith(".mp3"): content_type = "audio/mpeg"
            elif target_file.endswith(".woff2"): content_type = "font/woff2"
            self.send_file(target_file, content_type)
        else:
            self.send_error(404, "File Not Found")

    def do_POST(self):
        with session_lock:
            self._do_post_locked()

    def _do_post_locked(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/reset":
            session.reset()
            st = session.get_state_dict()
            st["catalog"] = ITEM_CATALOG
            self.send_json(st)
            return

        if parsed.path == "/api/place":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                data = json.loads(body)
                raw = data.get("placements") or {}
                requested = {int(k): v for k, v in raw.items()}
            except (ValueError, TypeError, AttributeError):
                self.send_json({"error": "Invalid payload"}, status=400)
                return

            if session.character.dead:
                self.send_json({"error": "Game over"}, status=400)
                return
            if not session.awaiting_placement:
                self.send_json({"error": "Today's slots are already placed"}, status=400)
                return
            if any(slot < 0 or slot >= session.current_slots for slot in requested):
                self.send_json({"error": "Slot out of range"}, status=400)
                return

            # apply_placements drops any district the registry does not define,
            # so an unknown id degrades to an unplaced slot rather than to a
            # shelf no content can ever reach.
            apply_placements(session.character, requested)
            session.awaiting_placement = False
            session.advance_event()
            session.save_state()
            st = session.get_state_dict()
            st["catalog"] = ITEM_CATALOG
            self.send_json(st)
            return

        if parsed.path == "/api/rest":
            if session.character.dead:
                self.send_json({"error": "Game over"}, status=400)
                return
            if session.used_slots_today >= session.current_slots:
                self.send_json({"error": "No action slots remaining today"}, status=400)
                return
            if session.awaiting_placement:
                self.send_json({"error": "Place today's slots first"}, status=400)
                return
            text = apply_rest(session.character, session.rng)
            session.used_slots_today += 1
            session.last_outcome = {
                "success": True,
                "text": text,
                "deltas": dict(resolver_module.REST_DELTAS),
                "guaranteed": True,
            }
            session.advance_event()
            session.save_state()
            st = session.get_state_dict()
            st["catalog"] = ITEM_CATALOG
            self.send_json(st)
            return

        if parsed.path == "/api/buy_item":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                data = json.loads(body)
                item_id = data.get("item_id")
            except Exception:
                self.send_json({"error": "Invalid payload"}, status=400)
                return

            item = next((i for i in ITEM_CATALOG if i["id"] == item_id), None)
            if not item:
                self.send_json({"error": "Item not found"}, status=400)
                return

            if session.character.get("Wealth") < item["cost"]:
                self.send_json({"error": "Insufficient funds"}, status=400)
                return

            session.character.add("Wealth", -item["cost"])
            session.character.add_item(item_id)
            if "stat_deltas" in item:
                session.character.apply_deltas(item["stat_deltas"])
            for name, delta in item.get("rel_deltas", {}).items():
                session.character.adjust_relationship(name, float(delta))

            session.last_outcome = {
                "success": True,
                "text": f"Acquired {item['name']}.",
                "deltas": item.get("stat_deltas", {})
            }
            session.save_state()
            st = session.get_state_dict()
            st["catalog"] = ITEM_CATALOG
            self.send_json(st)
            return

        if parsed.path == "/api/contact_action":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                data = json.loads(body)
                name = data.get("name")
            except Exception:
                self.send_json({"error": "Invalid payload"}, status=400)
                return

            if session.used_slots_today >= session.current_slots:
                self.send_json({"error": "No action slots remaining today"}, status=400)
                return
            if session.awaiting_placement:
                self.send_json({"error": "Place today's slots first"}, status=400)
                return

            session.character.reinforce(name, amount=25.0)
            session.used_slots_today += 1
            session.last_outcome = {
                "success": True,
                "text": f"Reinforced bond with {name}. Memory retention strengthened.",
                "deltas": {"Meaning": 5.0}
            }
            session.character.add("Meaning", 5.0)
            session.advance_event()
            session.save_state()
            st = session.get_state_dict()
            st["catalog"] = ITEM_CATALOG
            self.send_json(st)
            return

        if parsed.path == "/api/choose":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                data = json.loads(body)
                idx = int(data.get("choice_idx", 0))
            except Exception:
                self.send_json({"error": "Invalid payload"}, status=400)
                return

            if session.character.dead or not session.current_event:
                self.send_json({"error": "Game over or no active event"}, status=400)
                return
            # advance_event never leaves a storylet standing while placement is
            # open, so this is belt-and-braces -- but resolving one here would
            # spend a slot whose district was never decided.
            if session.awaiting_placement:
                self.send_json({"error": "Place today's slots first"}, status=400)
                return

            visible = eligible_choices(session.current_event.choices, session.character)
            if idx < 0 or idx >= len(visible):
                self.send_json({"error": "Choice out of range"}, status=400)
                return

            choice = visible[idx]
            success, branch = resolve_choice(choice, session.character, session.rng)
            roll_info = dict(resolver_module.last_resolution)

            session.current_event.last_fired_day = session.character.day
            session.current_event.fire_count += 1
            session.fired_today.add(session.current_event.id)
            if is_ambient(session.current_event):
                session.ambient_today += 1
            session.used_slots_today += 1

            session.last_outcome = {
                "success": success,
                "text": branch.get("text", "Outcome resolved."),
                "deltas": branch.get("deltas", {}),
                "roll": round(roll_info.get("roll", 0.0) * 100, 1),
                "target": round(roll_info.get("p", 0.0) * 100, 1),
                "guaranteed": bool(roll_info.get("guaranteed", 0.0)),
                "overdose": roll_info.get("overdose", 0.0)
            }

            session.advance_event()
            session.save_state()
            st = session.get_state_dict()
            st["catalog"] = ITEM_CATALOG
            self.send_json(st)
            return

        if parsed.path == "/api/saves":
            self.send_json({"slots": list_slots()})
            return

        if parsed.path == "/api/saves/save":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                data = json.loads(body) if body else {}
                name = str(data.get("name", ""))
            except (json.JSONDecodeError, TypeError, AttributeError):
                self.send_json({"error": "Invalid payload"}, status=400)
                return
            entry = session.save_slot(name)
            self.send_json({"slots": list_slots(), "saved": entry})
            return

        if parsed.path == "/api/saves/load":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                data = json.loads(body)
                slot_id = str(data.get("id", ""))
            except (json.JSONDecodeError, TypeError, AttributeError):
                self.send_json({"error": "Invalid payload"}, status=400)
                return
            try:
                session.load_slot(slot_id)
            except FileNotFoundError:
                self.send_json({"error": "Slot not found."}, status=404)
                return
            except (ValueError, KeyError, TypeError) as err:
                # Covers both a malformed slot and the version-refusal case in
                # _apply_session_payload -- either way the player needs to see
                # this, not just the console.
                self.send_json({"error": f"Could not load that save: {err}"}, status=400)
                return
            # Loading becomes the new current run: it must persist immediately
            # as the autosave, not wait for the player's next action.
            session.save_state()
            st = session.get_state_dict()
            st["catalog"] = ITEM_CATALOG
            self.send_json(st)
            return

        if parsed.path == "/api/saves/delete":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                data = json.loads(body)
                slot_id = str(data.get("id", ""))
            except (json.JSONDecodeError, TypeError, AttributeError):
                self.send_json({"error": "Invalid payload"}, status=400)
                return
            try:
                delete_slot(slot_id)
            except ValueError:
                self.send_json({"error": "Invalid slot id."}, status=400)
                return
            self.send_json({"slots": list_slots()})
            return

        self.send_error(404, "Unknown Endpoint")

    def send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, filepath: str, content_type: str):
        with open(filepath, "rb") as fh:
            data = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def run_server():
    server_address = ("", PORT)
    httpd = ThreadingHTTPServer(server_address, GreyUtopiaRequestHandler)
    print(f"\n================================================================================")
    print(f"  GREY UTOPIA WEB SERVER LAUNCHED")
    print(f"  Open in browser: http://localhost:{PORT}")
    print(f"================================================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer shutting down gracefully.")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
