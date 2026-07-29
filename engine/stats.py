"""stats.py -- Core statistical model and Character representation for GREY UTOPIA."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional
import json

STAT_SPEC: Dict[str, tuple[float, float, float]] = {
    "Wealth":              (0.0,   1e9, 500.0),
    "Fame":                (0.0, 100.0,  10.0),
    "Recklessness":        (0.0, 100.0,  30.0),
    "Mental_Decay":        (0.0, 100.0,  20.0),
    "Family_Friction":     (0.0, 100.0,  40.0),
    "Substance_Reliance":  (0.0, 100.0,   5.0),
    "Heat":                (0.0, 100.0,   0.0),
    "Physical_Integrity":  (0.0, 100.0,  90.0),
    "Social_Capital":      (0.0, 100.0,  25.0),
    "Meaning":             (0.0, 100.0,  30.0),
    "Tolerance":           (0.0,  10.0,   0.0),
}


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


# F7: how much memory strength an adversarial contact builds, against the 1.5 a
# warm one builds in `Character.reinforce`. See `Character.strain`.
K_STRAIN = 1.0


@dataclass
class Relationship:
    name: str
    satisfaction: float = 60.0   # 0..100
    strength: float = 8.0        # S in Ebbinghaus forgetting curve (days)
    last_reinforced_day: int = 0
    # F7: a monotonic count of warm contacts. Until F7, `strength` was raised by
    # `reinforce` alone, so counting S increments counted reinforcements exactly
    # and tests/cast_audit.py did precisely that. F7 made `strain` raise S too,
    # which severs that identity -- so the count is kept explicitly rather than
    # inferred, or the accumulation gate would score adversarial contact as
    # affection and grade its own change.
    reinforcements: int = 0
    flags: set[str] = field(default_factory=set)


@dataclass
class Character:
    day: int = 0
    stats: Dict[str, float] = field(default_factory=dict)
    flags: set[str] = field(default_factory=set)
    relationships: Dict[str, Relationship] = field(default_factory=dict)
    days_since_use: int = 0
    md_high_streak: int = 0      # consecutive days Mental_Decay >= 90
    inventory: list[str] = field(default_factory=list)
    factions: Dict[str, float] = field(default_factory=dict) # Undercity, Steward, Resistance (-100..100)
    clocks: Dict[str, int] = field(default_factory=dict)  # deadline name -> days remaining
    # A1 placement: where today's action slots are standing. slot index ->
    # district id, absent meaning the slot is unplaced and draws the whole deck.
    # Cleared at every day rollover by engine.districts.clear_placements.
    placements: Dict[int, str] = field(default_factory=dict)
    # district id -> the day a slot was last placed there. Feeds the placement
    # screen's hint line; it is the map's memory, so it survives the day.
    last_visited: Dict[str, int] = field(default_factory=dict)
    pending_dose: float = 0.0    # substance dose taken today, consumed by end_of_day_decay
    fail_streak: int = 0         # consecutive genuinely-failed rolls; fuels the desperation edge
    # A3: how many lines the Steward has written about this run. Monotonic and
    # never cools, which is the whole point -- Heat is a stock that K_COOL
    # drains to zero for any careful player (measured: cautious runs spend 0.0%
    # of their days at Heat >= 25), so the file reads its integral instead.
    # Written by engine.steward.note_resolution. See engine/steward.py.
    steward_file: int = 0
    dead: bool = False
    ending: str = ""

    def __post_init__(self):
        if not self.stats:
            self.stats = {k: spec[2] for k, spec in STAT_SPEC.items()}
        else:
            # Clamp initial values
            for k in list(self.stats.keys()):
                if k in STAT_SPEC:
                    lo, hi, _ = STAT_SPEC[k]
                    self.stats[k] = clamp(self.stats[k], lo, hi)
        if not self.factions:
            self.factions = {"Undercity": 10.0, "Steward": -10.0, "Resistance": 0.0}

    def get(self, key: str) -> float:
        return self.stats.get(key, 0.0)

    def set(self, key: str, value: float) -> None:
        lo, hi, _ = STAT_SPEC.get(key, (float("-inf"), float("inf"), 0.0))
        self.stats[key] = clamp(value, lo, hi)

    def add(self, key: str, delta: float) -> None:
        self.set(key, self.get(key) + delta)

    def apply_deltas(self, deltas: Dict[str, float]) -> None:
        for k, v in deltas.items():
            if k in STAT_SPEC:
                self.add(k, v)

    def add_item(self, item_id: str) -> None:
        self.inventory.append(item_id)

    def has_item(self, item_id: str) -> bool:
        return item_id in self.inventory

    def remove_item(self, item_id: str) -> bool:
        if item_id in self.inventory:
            self.inventory.remove(item_id)
            return True
        return False

    def add_faction(self, faction: str, delta: float) -> None:
        curr = self.factions.get(faction, 0.0)
        self.factions[faction] = clamp(curr + delta, -100.0, 100.0)

    def add_relationship(self, name: str, satisfaction: float = 60.0, strength: float = 8.0) -> None:
        self.relationships[name] = Relationship(
            name=name,
            satisfaction=clamp(satisfaction, 0.0, 100.0),
            strength=max(1.0, strength),
            last_reinforced_day=self.day
        )

    def reinforce(self, name: str, amount: float = 15.0) -> None:
        r = self.relationships.get(name)
        if not r:
            return
        r.satisfaction = clamp(r.satisfaction + amount, 0.0, 100.0)
        r.last_reinforced_day = self.day
        r.reinforcements += 1
        r.strength = min(r.strength + 1.5, 40.0)   # Spacing effect increases memory strength

    def strain(self, name: str, amount: float) -> None:
        """Damage a bond's satisfaction, while still deepening the memory of it.

        S in the Ebbinghaus curve is memorability, not affection: a broker you
        keep crossing remembers you vividly, and the next thing you do lands on
        someone who has not forgotten. Before F7, `strain` moved satisfaction and
        left S alone, so the contacts whose content runs half-adversarial -- Vint
        and Kael -- never built the strength that lets a warm contact survive to
        the next one, and their bars sat under 4% on ~90% of run-days.

        Strain builds strength more slowly than warmth does (`K_STRAIN` against
        `reinforce`'s 1.5): being crossed is memorable, but it is not the habit
        that warm contact is, and if the two were equal then burning a contact
        would be a way to make them durable.
        """
        r = self.relationships.get(name)
        if not r:
            return
        r.satisfaction = clamp(r.satisfaction - amount, 0.0, 100.0)
        r.strength = min(r.strength + K_STRAIN, 40.0)

    def adjust_relationship(self, name: str, delta: float) -> None:
        """Route an event's relationship delta: positive deltas reinforce, negative strain."""
        if delta >= 0:
            self.reinforce(name, delta)
        else:
            self.strain(name, -delta)

    def start_clock(self, name: str, days: int) -> None:
        self.clocks[name] = max(1, int(days))

    def stop_clock(self, name: str) -> None:
        self.clocks.pop(name, None)
        self.flags.discard(f"clock_{name}_expired")

    def to_json(self) -> str:
        d = {
            "day": self.day,
            "stats": self.stats,
            "flags": sorted(self.flags),
            "inventory": self.inventory,
            "factions": self.factions,
            "clocks": self.clocks,
            # JSON object keys are strings; from_dict casts the slot index back.
            "placements": {str(k): v for k, v in self.placements.items()},
            "last_visited": self.last_visited,
            "pending_dose": self.pending_dose,
            "fail_streak": self.fail_streak,
            "steward_file": self.steward_file,
            "days_since_use": self.days_since_use,
            "md_high_streak": self.md_high_streak,
            "dead": self.dead,
            "ending": self.ending,
            "relationships": {
                n: {**asdict(r), "flags": sorted(r.flags)}
                for n, r in self.relationships.items()
            },
        }
        return json.dumps(d, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Character:
        c = cls(
            day=data.get("day", 0),
            stats=data.get("stats", {}),
            flags=set(data.get("flags", [])),
            inventory=list(data.get("inventory", [])),
            factions=dict(data.get("factions", {"Undercity": 10.0, "Steward": -10.0, "Resistance": 0.0})),
            clocks={k: int(v) for k, v in data.get("clocks", {}).items()},
            # Absent in saves written before A1 Phase 2; an old save simply
            # reloads with every slot unplaced, which is what it was playing.
            placements={int(k): v for k, v in data.get("placements", {}).items()},
            last_visited={k: int(v) for k, v in data.get("last_visited", {}).items()},
            pending_dose=float(data.get("pending_dose", 0.0)),
            fail_streak=int(data.get("fail_streak", 0)),
            # Absent in saves written before A3; an old save reloads with an
            # empty file, which is exactly what it was playing.
            steward_file=int(data.get("steward_file", 0)),
            days_since_use=data.get("days_since_use", 0),
            md_high_streak=data.get("md_high_streak", 0),
            dead=data.get("dead", False),
            ending=data.get("ending", "")
        )
        rels = data.get("relationships", {})
        for name, rdata in rels.items():
            c.relationships[name] = Relationship(
                name=rdata["name"],
                satisfaction=rdata.get("satisfaction", 60.0),
                strength=rdata.get("strength", 8.0),
                last_reinforced_day=rdata.get("last_reinforced_day", 0),
                # Absent in saves written before F7; an old save reloads with an
                # uncounted history, which costs it nothing -- the field is read
                # by the audit, never by play.
                reinforcements=int(rdata.get("reinforcements", 0)),
                flags=set(rdata.get("flags", []))
            )
        return c


def create_starter_fixer() -> Character:
    """The three bonds a run opens with.

    These numbers are duplicated in `data/cast.json`, which the linter and the
    legacy-inheritance path read; **this** function is what play actually starts
    from, so editing cast.json alone changes nothing. Keep the two in step.

    F7 raised the two starting strengths. S in the Ebbinghaus curve is
    memorability, not affection, and both of these characters are defined by
    remembering: Kael keeps the ledger the whole Row is filed in ("he doesn't say
    anything -- he just remembers"), and Vint is the archivist who never throws a
    drive away. Their old values had them forgetting you faster than your sister
    does, which inverted all three characterizations at once.
    """
    c = Character()
    c.add_relationship("Mara (Sister)", satisfaction=75.0, strength=12.0)
    c.add_relationship("Vint (Informant)", satisfaction=50.0, strength=10.0)
    c.add_relationship("Kael (Broker)", satisfaction=40.0, strength=14.0)
    return c
