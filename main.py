"""main.py -- Main entry point for GREY UTOPIA (Underground Fixer QBN Engine)."""
from __future__ import annotations
import os
import sys
import glob
import json
import random
from typing import List, Dict

from engine.stats import create_starter_fixer, Character
from engine.events import Event, load_events
from engine.selector import select_event, is_ambient, ambient_budget_for, district_for_slot
from engine.resolver import (
    resolve_choice, check_endings, eligible_choices, build_epilogue,
    build_run_memories, last_resolution, apply_rest
)
from engine.decay import end_of_day_decay, compute_daily_stress, build_day_report
from engine.ambient import morning_report, steward_ledger_line
from engine.districts import (
    apply_placements, auto_placement, clear_placements, district_hint,
    district_name, load_districts
)
from engine import items as item_catalog
from engine import legacy
from engine import paths
from ui.terminal import (
    print_banner, render_hud, render_event, render_choices,
    prompt_choice, prompt_from_list, render_resolution,
    render_end_of_day_summary, render_ending_screen, render_ambient,
    prompt_placement, render_placement_summary,
    RED, GREEN, DIM, BOLD, RESET
)

DATA_DIR = os.path.join(paths.app_root(), "data")


def load_all_events() -> List[Event]:
    events_dir = os.path.join(DATA_DIR, "events")
    all_events: List[Event] = []

    # Load all json files except endings.json
    for filepath in glob.glob(os.path.join(events_dir, "*.json")):
        if os.path.basename(filepath) == "endings.json":
            continue
        all_events.extend(load_events(filepath))

    return all_events


def load_endings() -> Dict[str, dict]:
    endings_file = os.path.join(DATA_DIR, "events", "endings.json")
    if os.path.exists(endings_file):
        with open(endings_file, "r", encoding="utf-8") as fh:
            return json.load(fh).get("endings", {})
    return {}


def calculate_daily_action_slots(character: Character) -> int:
    slots = 3
    if character.get("Physical_Integrity") < 30.0 or character.get("Mental_Decay") > 80.0:
        slots -= 1
    return max(1, slots)


def run_contacts_menu(character: Character) -> bool:
    """Spend an action slot reconnecting with a contact. Returns True if the slot was used."""
    names = list(character.relationships.keys())
    labels = [
        f"{r.name} -- bond {r.satisfaction:.0f}%, memory strength {r.strength:.1f} days"
        for r in character.relationships.values()
    ]
    idx = prompt_from_list("Reach out to whom?", labels)
    if idx is None:
        return False
    name = names[idx]
    character.reinforce(name, amount=25.0)
    character.add("Meaning", 5.0)
    print(f"\n{GREEN}You spend real hours with {name}. The bond holds a little longer against the forgetting.{RESET}")
    return True


def run_market_menu(character: Character) -> None:
    """Browse and buy from the black-market catalog. Does not consume an action slot."""
    catalog = list(item_catalog.get_catalog().values())
    if not catalog:
        print(f"{DIM}The market shelves are bare tonight.{RESET}")
        return
    while True:
        labels = []
        for it in catalog:
            owned = " [OWNED]" if character.has_item(it["id"]) else ""
            labels.append(f"{it['name']} -- {it['cost']:.0f} cr{owned} :: {it['description']}")
        idx = prompt_from_list(
            f"Black Market (Wealth: {character.get('Wealth'):.0f} cr)", labels)
        if idx is None:
            return
        item = catalog[idx]
        if character.get("Wealth") < item["cost"]:
            print(f"{RED}You can't cover {item['cost']:.0f} cr.{RESET}")
            continue
        character.add("Wealth", -item["cost"])
        character.add_item(item["id"])
        if "stat_deltas" in item:
            character.apply_deltas(item["stat_deltas"])
        for name, delta in item.get("rel_deltas", {}).items():
            character.adjust_relationship(name, float(delta))
        print(f"{GREEN}Acquired {item['name']}.{RESET}")


def run_placement_step(character: Character, all_events: List[Event], slots: int,
                       auto_play: bool, rng: random.Random) -> None:
    """The morning placement: commit each of the day's slots to a district.

    Placement rides on the character rather than on a local, so this loop,
    `server.py` and the harness all read it back through the same
    `district_for_slot`, and `server.py` gets save/load persistence for free.
    """
    clear_placements(character)
    districts = load_districts()
    if not districts:
        return
    if auto_play:
        apply_placements(character, auto_placement(rng, character, slots))
        return
    hints = [district_hint(all_events, character, d["id"]) for d in districts]
    apply_placements(character, prompt_placement(slots, districts, hints))
    render_placement_summary(character.placements, slots, district_name)


def run_game_loop(auto_play: bool = False, max_days: int = 30) -> None:
    rng = random.Random()
    character = create_starter_fixer()
    cycles = legacy.apply_legacy_flags(character)
    inheritance = legacy.apply_legacy_inheritance(character)
    all_events = load_all_events()
    endings_db = load_endings()
    last_day_report: dict | None = None

    if not auto_play:
        print_banner()
        if cycles:
            print(f"[Cycle {cycles + 1}. The city remembers the previous arcs. So, apparently, does the Steward.]")
        if inheritance:
            print("[The file precedes you. The city has adjusted your terms.]")

    print(f"Loaded {len(all_events)} static storylets from library.")

    while not character.dead:
        ending = check_endings(character)
        if ending:
            character.ending = ending
            character.dead = True
            if not auto_play:   # bot runs don't write player legacy
                legacy.record_ending(ending, character)
            ending_info = endings_db.get(ending, {})
            if not auto_play:
                epilogue = build_epilogue(ending_info, character)
                memories = build_run_memories(character)
                render_ending_screen(ending, ending_info, epilogue, memories)
            else:
                print(f"=== GAME CONCLUDED ON DAY {character.day}: {ending} ===")
            break

        slots = calculate_daily_action_slots(character)

        if not auto_play:
            render_hud(character)
            print(f"{"\n" if character.day > 0 else ""}{'='*40} DAY {character.day} ({slots} Action Slots Available) {'='*40}")
            render_ambient(morning_report(character), steward_ledger_line(character, last_day_report))

        run_placement_step(character, all_events, slots, auto_play, rng)

        # Execute daily action slots
        fired_today: set[str] = set()
        ambient_today = 0
        slot = 0
        while slot < slots:
            ev = select_event(all_events, character, character.day, rng, exclude_ids=fired_today,
                              ambient_budget=ambient_budget_for(ambient_today),
                              district=district_for_slot(character, slot))
            if not ev:
                if not auto_play:
                    print("\n[No eligible events available today. Resting...]")
                break

            choices = eligible_choices(ev.choices, character)
            if not choices:
                fired_today.add(ev.id)
                continue

            if not auto_play:
                render_event(ev, character)
                render_choices(choices, character)
                picked = prompt_choice(len(choices))
                if picked == "contacts":
                    if run_contacts_menu(character):
                        slot += 1
                    continue
                if picked == "market":
                    run_market_menu(character)
                    continue
                if picked == "rest":
                    flavor = apply_rest(character, rng)
                    print(f"\n{DIM}{flavor}{RESET}")
                    slot += 1
                    continue
                choice_idx = picked
            else:
                choice_idx = rng.randrange(len(choices))

            chosen_choice = choices[choice_idx]
            success, branch = resolve_choice(chosen_choice, character, rng)

            ev.last_fired_day = character.day
            ev.fire_count += 1
            fired_today.add(ev.id)
            if is_ambient(ev):
                ambient_today += 1
            slot += 1

            if not auto_play:
                render_resolution(success, branch.get("text", "Outcome resolved."))
                od = last_resolution.get("overdose")
                if od == 0.5:
                    print(f"\n{RED}{BOLD}Your heart stutters. The world goes white at the edges -- you come back "
                          f"on the floor, hours later, breathing wrong. The next one will not be a warning.{RESET}")

            # Endings that trigger mid-day (overdose, The Crossing) end the run now
            if check_endings(character):
                break

        if character.dead or check_endings(character):
            continue

        # End of day decay step (stress derived from the life you are living)
        stats_before = dict(character.stats)
        clocks_before = set(character.clocks)
        stress_today = compute_daily_stress(character, rng)
        end_of_day_decay(character, stress_today=stress_today)
        last_day_report = build_day_report(character, stress_today, stats_before, clocks_before)

        if not auto_play:
            render_end_of_day_summary(character.day, stress_today, character)

        if auto_play and character.day >= max_days:
            print(f"Auto-play reached maximum day limit ({max_days}).")
            break


if __name__ == "__main__":
    is_auto = "--auto" in sys.argv
    run_game_loop(auto_play=is_auto)
