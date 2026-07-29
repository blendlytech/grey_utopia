"""terminal.py -- Gritty, atmospheric text-based UI renderer for GREY UTOPIA."""
from __future__ import annotations
from typing import Dict, List, Optional
from engine.stats import Character
from engine.events import Event, Choice
from engine.resolver import choice_probability

# ANSI Terminal Color Constants
HEADER = "\033[95m"
BLUE   = "\033[94m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"


def print_banner() -> None:
    banner = f"""
{RED}{BOLD}================================================================================{RESET}
{CYAN}{BOLD}               G R E Y   U T O P I A   --   U N D E R G R O U N D               {RESET}
{RED}{BOLD}================================================================================{RESET}
{DIM}         A gritty Quality-Based Narrative (QBN) life-sim in an AI dystopia       {RESET}
"""
    print(banner)


def render_hud(character: Character) -> None:
    s = character.get
    print(f"{BOLD}--------------------------------------------------------------------------------{RESET}")
    print(
        f"{YELLOW}DAY {character.day}{RESET} | "
        f"{GREEN}Wealth:{RESET} {s('Wealth'):.0f} cr | "
        f"{CYAN}Fame:{RESET} {s('Fame'):.1f} | "
        f"{RED}Heat:{RESET} {s('Heat'):.1f}% | "
        f"{BLUE}Meaning:{RESET} {s('Meaning'):.1f}%"
    )
    print(
        f"{HEADER}Mental Decay:{RESET} {s('Mental_Decay'):.1f}% | "
        f"{GREEN}Body Integrity:{RESET} {s('Physical_Integrity'):.1f}% | "
        f"{RED}Substance Reliance:{RESET} {s('Substance_Reliance'):.1f}% | "
        f"Tolerance: {s('Tolerance'):.2f}"
    )
    
    # Render key relationships if present
    if character.relationships:
        rel_str = " | ".join(
            f"{r.name}: {r.satisfaction:.0f}% (S={r.strength:.1f})"
            for r in character.relationships.values()
        )
        print(f"{DIM}Contacts: {rel_str}{RESET}")

    # Running deadline clocks -- the undercity's ledgers always balance
    if character.clocks:
        clock_str = " | ".join(
            f"{name.replace('_', ' ').upper()}: {days} day{'s' if days != 1 else ''}"
            for name, days in character.clocks.items()
        )
        print(f"{RED}{BOLD}DEADLINES >> {clock_str}{RESET}")
    print(f"{BOLD}--------------------------------------------------------------------------------{RESET}")


def render_ambient(morning_lines: List[str], ledger_line: str,
                   filing_notice: Optional[str] = None) -> None:
    """Print the morning's ambient report, Steward ledger line and -- when the
    Steward is about to file -- the filing notice, before the day's first event.

    The notice is A3's "one line the player sees coming". It rides this call
    rather than getting a surface of its own because `steward.filing_notice` is
    written in the same register as `ambient.steward_ledger_line` and belongs
    beside it; it is bold rather than dim because unlike the ledger it is about
    something that has not happened yet. None outside the notice window.
    """
    for line in morning_lines:
        print(f"{DIM}{line}{RESET}")
    if ledger_line:
        print(f"{CYAN}{ledger_line}{RESET}")
    if filing_notice:
        print(f"{BOLD}{YELLOW}{filing_notice}{RESET}")
    if morning_lines or ledger_line or filing_notice:
        print()


def prompt_placement(slots: int, districts: List[dict], hints: List[str]) -> Dict[int, str]:
    """The morning placement step: commit each of the day's slots to a district.

    Placement is free (A1_DESIGN §4) -- the cost of standing in the Archive is
    the districts you are not standing in, not a slot spent travelling. Empty
    input leaves a slot in the Row at large, so a player who does not want to
    engage with the map presses Enter three times and gets the pre-A1 game.
    """
    if not districts:
        return {}
    print(f"\n{BOLD}--- MORNING: WHERE WILL YOU WORK? ---{RESET}")
    for idx, (district, hint) in enumerate(zip(districts, hints), 1):
        print(f"  {BOLD}[{idx}]{RESET} {CYAN}{district['name']}{RESET}")
        print(f"      {DIM}{hint}{RESET}")
    print(f"  {BOLD}[0]{RESET} {DIM}The Row at large -- take whatever the city hands you{RESET}")

    placements: Dict[int, str] = {}
    for slot in range(slots):
        while True:
            try:
                val = input(f"{BOLD}Slot {slot + 1} "
                            f"{DIM}[0-{len(districts)}, Enter = the Row]{RESET}{BOLD}: {RESET}").strip()
            except EOFError:
                return placements
            if not val or val == "0":
                break
            if val.isdigit() and 1 <= int(val) <= len(districts):
                placements[slot] = districts[int(val) - 1]["id"]
                break
            print(f"{RED}Pick 0-{len(districts)}, or press Enter to stay in the Row.{RESET}")
    return placements


def render_placement_summary(placements: Dict[int, str], slots: int, name_for) -> None:
    """One line confirming where the day's slots are standing."""
    if not placements:
        return
    where = ", ".join(
        f"slot {i + 1}: {name_for(placements[i])}" for i in sorted(placements) if i < slots
    )
    if where:
        print(f"{CYAN}You set out. {where}.{RESET}")


def render_event(event: Event, character: Character) -> None:
    print(f"\n{YELLOW}{BOLD}>>> {event.title} <<<{RESET}")
    print(f"{DIM}[Tags: {', '.join(event.tags)}]{RESET}")
    print(f"\n{event.compose_body(character)}\n")


def render_choices(choices: List[Choice], character: Character) -> None:
    print(f"{BOLD}Select your action:{RESET}")
    for idx, ch in enumerate(choices, 1):
        p = choice_probability(ch, character)
        prob_str = f"{GREEN}{p*100:.0f}% success{RESET}" if p >= 0.5 else f"{RED}{p*100:.0f}% success{RESET}"
        unlock = f" {CYAN}[UNLOCKED]{RESET}" if ch.requires else ""
        print(f"  {BOLD}[{idx}]{RESET} {ch.text} ({prob_str}){unlock}")
    print(f"  {DIM}[C] Reach out to a contact (uses this action slot)   [M] Black market{RESET}")


def prompt_choice(choice_count: int) -> "int | str":
    """Returns a 0-based choice index, or 'contacts' / 'market' / 'rest' meta-commands."""
    while True:
        try:
            val = input(f"\n{BOLD}Your Choice (1-{choice_count}, C, M, R=lie low): {RESET}").strip().lower()
            if val == "c":
                return "contacts"
            if val == "m":
                return "market"
            if val == "r":
                return "rest"
            num = int(val)
            if 1 <= num <= choice_count:
                return num - 1
            print(f"{RED}Invalid choice. Enter a number between 1 and {choice_count}.{RESET}")
        except ValueError:
            print(f"{RED}Please enter a valid number, or C / M / R.{RESET}")
        except EOFError:
            raise SystemExit(0)


def prompt_from_list(title: str, labels: List[str]) -> Optional[int]:
    """Simple numbered submenu; returns 0-based index or None if cancelled."""
    print(f"\n{BOLD}{title}{RESET}")
    for idx, label in enumerate(labels, 1):
        print(f"  {BOLD}[{idx}]{RESET} {label}")
    print(f"  {DIM}[0] Back{RESET}")
    while True:
        try:
            val = input(f"{BOLD}Select (0-{len(labels)}): {RESET}").strip()
            num = int(val)
            if num == 0:
                return None
            if 1 <= num <= len(labels):
                return num - 1
        except ValueError:
            pass
        except EOFError:
            return None
        print(f"{RED}Invalid selection.{RESET}")


def render_resolution(success: bool, branch_text: str) -> None:
    status_tag = f"{GREEN}{BOLD}[SUCCESS]{RESET}" if success else f"{RED}{BOLD}[FAILURE]{RESET}"
    print(f"\n{status_tag} {branch_text}")


def render_end_of_day_summary(
    day: int,
    stress: float,
    character: Character,
    ending: Optional[str] = None
) -> None:
    print(f"\n{DIM}--- End of Day {day} Resolution ---{RESET}")
    print(f"Stress inflow: {stress:.1f} | Mental Decay (EMA): {character.get('Mental_Decay'):.1f}%")
    if ending:
        print(f"\n{RED}{BOLD}CRITICAL SYSTEM ALERT: Game Concluded ({ending}){RESET}")


def render_ending_screen(
    ending_id: str,
    ending_data: dict,
    epilogue_lines: Optional[List[str]] = None,
    memories: Optional[List[str]] = None,
) -> None:
    title = ending_data.get("title", f"GAME OVER: {ending_id}")
    text = ending_data.get("text", "Your journey in the Grey Utopia has ended.")
    print(f"\n{RED}{BOLD}{'='*80}{RESET}")
    print(f"{YELLOW}{BOLD}                     {title}                     {RESET}")
    print(f"{RED}{BOLD}{'='*80}{RESET}\n")
    print(f"{text}\n")
    for line in epilogue_lines or []:
        print(f"{DIM}{line}{RESET}\n")
    if memories:
        print(f"{CYAN}{BOLD}--- THE CYCLE REMEMBERS ---{RESET}")
        for line in memories:
            print(f"{CYAN}  * {line}{RESET}")
        print()
    print(f"{DIM}Press Enter to exit...{RESET}")
