"""server.py -- Lightweight REST API Server & Web UI host for GREY UTOPIA.
Hooks directly into the Python QBN engine (engine/).
"""
from __future__ import annotations
import os
import json
import random
import glob
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

from engine.stats import create_starter_fixer, Character
from engine.events import Event, load_events
from engine.selector import select_event
from engine.resolver import (
    choice_probability, resolve_choice, check_endings,
    eligible_choices, build_epilogue, build_run_memories,
    desperation_edge, apply_rest
)
from engine import resolver as resolver_module
from engine import legacy
from engine import paths
from engine.decay import end_of_day_decay, compute_daily_stress, build_day_report
from engine.ambient import morning_report, steward_ledger_line

PORT = 8000
BASE_DIR = paths.app_root()
DATA_DIR = os.path.join(BASE_DIR, "data")
WEB_DIR = os.path.join(BASE_DIR, "web")
ASSETS_DIR = os.path.join(DATA_DIR, "assets")
SAVES_DIR = os.path.join(paths.user_data_dir(), "saves")
AUTOSAVE_PATH = os.path.join(SAVES_DIR, "autosave.json")

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
        self.last_outcome: dict | None = None
        self.day_report: dict | None = None
        self.last_day_report: dict | None = None
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

    def save_state(self) -> None:
        os.makedirs(SAVES_DIR, exist_ok=True)
        payload = {
            "character": json.loads(self.character.to_json()),
            "used_slots_today": self.used_slots_today,
            "fired_today": sorted(self.fired_today),
            "event_state": {
                e.id: {"fire_count": e.fire_count, "last_fired_day": e.last_fired_day}
                for e in self.events if e.fire_count > 0 or e.last_fired_day > -9999
            },
            "current_event_id": self.current_event.id if self.current_event else None,
        }
        with open(AUTOSAVE_PATH, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)

    def load_state(self) -> bool:
        if not os.path.exists(AUTOSAVE_PATH):
            return False
        try:
            with open(AUTOSAVE_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self.character = Character.from_dict(data["character"])
            self.used_slots_today = int(data.get("used_slots_today", 0))
            self.fired_today = set(data.get("fired_today", []))
            event_state = data.get("event_state", {})
            for e in self.events:
                st = event_state.get(e.id)
                if st:
                    e.fire_count = int(st.get("fire_count", 0))
                    e.last_fired_day = int(st.get("last_fired_day", -9999))
            self.current_slots = self.calculate_slots()
            wanted = data.get("current_event_id")
            self.current_event = next((e for e in self.events if e.id == wanted), None)
            if self.current_event is None and not self.character.dead:
                self.advance_event()
            print(f"Restored autosave: Day {self.character.day}, {len(event_state)} event states.")
            return True
        except (KeyError, ValueError, json.JSONDecodeError, OSError) as err:
            print(f"Autosave restore failed ({err}); starting fresh.")
            return False

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

        # Pick the next storylet, skipping any whose choices are all locked
        # (a soft-lock guard; the linter forbids authoring such events).
        skip = set(self.fired_today)
        for _ in range(8):
            candidate = select_event(
                self.events, self.character, self.character.day, self.rng,
                exclude_ids=skip
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
        self.last_outcome = None
        self.day_report = None
        self.last_day_report = None
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
            "ambient": None if self.character.dead else {
                "morning_report": morning_report(self.character),
                "ledger_line": steward_ledger_line(self.character, self.last_day_report),
            },
            "last_outcome": self.last_outcome,
            "day_report": self.day_report
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

        # Serve visual scene assets
        if parsed.path.startswith("/assets/"):
            asset_name = os.path.basename(parsed.path)
            asset_path = os.path.join(ASSETS_DIR, asset_name)
            if os.path.exists(asset_path):
                self.send_file(asset_path, "image/png")
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

        if parsed.path == "/api/rest":
            if session.character.dead:
                self.send_json({"error": "Game over"}, status=400)
                return
            if session.used_slots_today >= session.current_slots:
                self.send_json({"error": "No action slots remaining today"}, status=400)
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
