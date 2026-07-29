"""events.py -- Storylet schema definitions, precondition matcher, and JSON library validator."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
import json
from engine.stats import Character, STAT_SPEC
from engine import steward

VALID_OPS = {">=", "<=", ">", "<", "==", "!="}


def compare_op(op: str, val_a: float, val_b: float) -> bool:
    if op == ">=": return val_a >= val_b
    if op == "<=": return val_a <= val_b
    if op == ">":  return val_a > val_b
    if op == "<":  return val_a < val_b
    if op == "==": return val_a == val_b
    if op == "!=": return val_a != val_b
    raise ValueError(f"Invalid comparison operator: {op}")


@dataclass
class Choice:
    id: str
    text: str
    prob: Dict[str, Any]
    success: Dict[str, Any] = field(default_factory=dict)
    failure: Dict[str, Any] = field(default_factory=dict)
    requires: Dict[str, Any] = field(default_factory=dict)   # precondition dict; hides choice when unmet
    boost_items: List[str] = field(default_factory=list)     # inventory items that raise success odds

    def available(self, character: Character) -> bool:
        return eval_conditions(self.requires, character)


@dataclass
class Insert:
    text: str
    when: Dict[str, Any] = field(default_factory=dict)   # precondition dict; same grammar as Event.preconditions

    def active(self, character: Character) -> bool:
        return eval_conditions(self.when, character)


@dataclass
class Event:
    id: str
    title: str
    body: str
    weight: float = 1.0
    cooldown: int = 0
    max_fires: int = 0  # 0 = unlimited
    tags: List[str] = field(default_factory=list)
    preconditions: Dict[str, Any] = field(default_factory=dict)
    choices: List[Choice] = field(default_factory=list)
    inserts: List[Insert] = field(default_factory=list)
    # Which district's shelf this storylet lives on (A1). None means
    # district-neutral: drawable from any unplaced slot, exactly as every event
    # behaved before districts existed. Absent-means-neutral is what lets the
    # deck migrate a pack at a time. See docs/A1_DESIGN.md §1.
    district: Optional[str] = None
    # Whether this storylet is content the player is walking a thread toward, as
    # opposed to the city's background noise. Purely a *classification*: nothing
    # in the engine reads it, and it is deliberately a top-level flag rather than
    # a tag so that it cannot leak into `effective_weight`, which multiplies
    # weight off `tags`. `tests/coverage_audit.py` is the only consumer.
    #
    # It exists because tags cannot answer the question and two windows were
    # blocked by that. The audit's tag-based classifier scores `ambitions_pack`
    # (three 8-link chains) and `cast_expansion_pack` (five character threads) at
    # 0.0% arc, because they happen to be tagged existential/undercity/job. Since
    # MIN_ARC_SHARE is a standing gate, shelving real arc content pushed the gate
    # the *wrong* way -- a future window could have turned a red gate green by
    # un-shelving the very content A1 exists to rescue. See BACKLOG_HANDOFF §5.
    arc: bool = False
    last_fired_day: int = -9999
    fire_count: int = 0

    def eligible(self, character: Character, day: int) -> bool:
        if self.max_fires > 0 and self.fire_count >= self.max_fires:
            return False
        if day - self.last_fired_day < self.cooldown:
            return False
        return self.check_preconditions(character)

    def check_preconditions(self, character: Character) -> bool:
        return eval_conditions(self.preconditions, character)

    def compose_body(self, character: Character) -> str:
        """Body text with any state-matched inserts appended, in authoring order."""
        parts = [self.body] + [ins.text for ins in self.inserts if ins.active(character)]
        return "\n\n".join(parts)


def eval_conditions(pre: Dict[str, Any], character: Character) -> bool:
    """Evaluate an all/any/none precondition dict against a character."""
    pre = pre or {}

    # 'all' requirements must ALL be met
    for cond in pre.get("all", []):
        if not eval_single_cond(cond, character):
            return False

    # 'any' requirements: AT LEAST ONE must be met if present
    any_conds = pre.get("any", [])
    if any_conds and not any(eval_single_cond(c, character) for c in any_conds):
        return False

    # 'none' requirements: NONE can be met
    for cond in pre.get("none", []):
        if eval_single_cond(cond, character):
            return False

    return True


def eval_single_cond(cond: Dict[str, Any], character: Character) -> bool:
    if "flag" in cond:
        has_flag = cond["flag"] in character.flags
        target = cond.get("value", True)
        return has_flag == target

    if "day" in cond:
        op = cond.get("op", ">=")
        return compare_op(op, float(character.day), float(cond["day"]))

    if "stat" in cond:
        stat_name = cond["stat"]
        op = cond.get("op", ">=")
        val = float(cond.get("value", 0.0))
        return compare_op(op, character.get(stat_name), val)

    if "steward_tier" in cond:
        # A3: the Steward's file band, 0..4. Deliberately its own condition kind
        # rather than a `stat`, for the same reason `steward_file` is a counter on
        # Character and not an entry in STAT_SPEC: a stat can be written by any
        # branch's `deltas`, clamped by `set`, and multiplied into
        # `selector.effective_weight`. The file must be none of those -- it is a
        # record, and content is not allowed to edit the record. See
        # engine/steward.py and docs/A3_DESIGN.md §1.4.
        op = cond.get("op", ">=")
        return compare_op(op, float(steward.tier_of(character)[0]),
                          float(cond["steward_tier"]))

    if "item" in cond:
        has = character.has_item(cond["item"])
        target = cond.get("value", True)
        return has == target

    if "faction" in cond:
        op = cond.get("op", ">=")
        val = float(cond.get("value", 0.0))
        standing = character.factions.get(cond["faction"], 0.0)
        return compare_op(op, standing, val)

    if "relationship" in cond:
        rel = character.relationships.get(cond["relationship"])
        sat = rel.satisfaction if rel else 0.0
        op = cond.get("op", ">=")
        val = float(cond.get("value", 0.0))
        return compare_op(op, sat, val)

    if "clock" in cond:
        # Compares days remaining on a running clock; a stopped clock fails
        # unless the condition explicitly targets 'running': false.
        name = cond["clock"]
        if "running" in cond:
            return (name in character.clocks) == bool(cond["running"])
        if name not in character.clocks:
            return False
        op = cond.get("op", "<=")
        val = float(cond.get("value", 0.0))
        return compare_op(op, float(character.clocks[name]), val)

    return True


def validate_choice(event_id: str, choice_dict: dict) -> None:
    assert "id" in choice_dict, f"Choice in event '{event_id}' missing 'id'"
    assert "text" in choice_dict, f"Choice in event '{event_id}' missing 'text'"
    
    # Check probability spec
    prob_spec = choice_dict.get("prob", {})
    assert "base" in prob_spec, f"Choice '{choice_dict['id']}' in '{event_id}' missing prob.base"
    for mod in prob_spec.get("mods", []):
        stat = mod.get("stat")
        assert stat in STAT_SPEC, f"Choice '{choice_dict['id']}' in '{event_id}' uses unknown mod stat '{stat}'"
        assert "coef" in mod, f"Choice '{choice_dict['id']}' in '{event_id}' missing mod coef"

    # Check deltas and branch effect payload types
    for branch in ("success", "failure"):
        branch_data = choice_dict.get(branch, {})
        deltas = branch_data.get("deltas", {})
        for stat in deltas:
            assert stat in STAT_SPEC, f"Choice '{choice_dict['id']}' in '{event_id}' uses unknown delta stat '{stat}'"
        dose = branch_data.get("dose", 0.0)
        assert isinstance(dose, (int, float)) and dose >= 0, \
            f"Choice '{choice_dict['id']}' in '{event_id}' has invalid dose '{dose}'"
        for name, days in branch_data.get("clocks_start", {}).items():
            assert isinstance(days, int) and days > 0, \
                f"Choice '{choice_dict['id']}' in '{event_id}' starts clock '{name}' with invalid days '{days}'"


def validate_insert(event_id: str, index: int, insert_dict: dict) -> None:
    assert "text" in insert_dict, f"Insert #{index} in event '{event_id}' missing 'text'"
    text = insert_dict["text"]
    assert isinstance(text, str) and text.strip(), \
        f"Insert #{index} in event '{event_id}' has empty or non-string 'text'"

    when = insert_dict.get("when", {})
    assert isinstance(when, dict), f"Insert #{index} in event '{event_id}': 'when' must be a dict"
    for grp in ("all", "any", "none"):
        conds = when.get(grp, [])
        assert isinstance(conds, list), f"Insert #{index} in event '{event_id}': when.{grp} must be a list"
        for cond in conds:
            assert isinstance(cond, dict), \
                f"Insert #{index} in event '{event_id}': when.{grp} entries must be dicts"
            op = cond.get("op")
            if op is not None:
                assert op in VALID_OPS, \
                    f"Insert #{index} in event '{event_id}' uses invalid op '{op}' -- valid: {sorted(VALID_OPS)}"
            if "day" in cond:
                assert isinstance(cond["day"], (int, float)), \
                    f"Insert #{index} in event '{event_id}': 'day' condition must be numeric"


def load_events(payload: Union[str, list, dict]) -> List[Event]:
    """Load and validate events from a JSON string, file path, dict, or list."""
    if isinstance(payload, str):
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            with open(payload, "r", encoding="utf-8") as fh:
                data = json.load(fh)
    else:
        data = payload

    if isinstance(data, dict):
        data = data.get("events", [])

    events: List[Event] = []
    for e in data:
        ev_id = e.get("id", "unknown")
        assert "title" in e and "body" in e, f"Event '{ev_id}' missing title or body"
        raw_choices = e.get("choices", [])
        assert len(raw_choices) >= 3, f"Event '{ev_id}' must have >= 3 choices (found {len(raw_choices)})"

        choices: List[Choice] = []
        for c in raw_choices:
            validate_choice(ev_id, c)
            choices.append(Choice(
                id=c["id"],
                text=c["text"],
                prob=c["prob"],
                success=c.get("success", {}),
                failure=c.get("failure", {}),
                requires=c.get("requires", {}),
                boost_items=list(c.get("boost_items", []))
            ))

        raw_inserts = e.get("inserts", [])
        inserts: List[Insert] = []
        for idx, ins in enumerate(raw_inserts):
            validate_insert(ev_id, idx, ins)
            inserts.append(Insert(text=ins["text"], when=ins.get("when", {})))

        events.append(Event(
            id=e["id"],
            title=e["title"],
            body=e["body"],
            weight=float(e.get("weight", 1.0)),
            cooldown=int(e.get("cooldown", 0)),
            max_fires=int(e.get("max_fires", 0)),
            tags=list(e.get("tags", [])),
            preconditions=e.get("preconditions", {}),
            choices=choices,
            inserts=inserts,
            district=e.get("district"),
            arc=bool(e.get("arc", False))
        ))
    return events
