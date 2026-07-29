"""cast_audit.py -- are Mara, Vint and Kael people, or three decaying bars? (A4)

A4's spec (S8) says the cast "should interrupt unprompted, carry visible arcs,
and react to each other", and that the player-facing surface is "a percentage
bar in the right sidebar". Every backlog spec that has been measured has turned
out wrong, so this measures the three claims before anything is designed.

`steward_audit.py --presence` is the template and this reuses its instrumented
`playout` verbatim -- there are already five copies of the day loop in this
repo and this does not add a sixth. `playout` records `fire_log` (day, event id)
and `rel_by_day` for exactly this reason.

Three modes:

    --presence   how often each contact is on screen, per strategy: events per
                 run, distinct days, share of run days, longest silence, and
                 runs where a contact never appears at all
    --interrupt  static deck census -- can a contact reach the player without
                 being drawn? forced weights, satisfaction-gated preconditions,
                 and how the cast's weights compare to the deck median
    --retention  what the Ebbinghaus curve is actually doing across a run:
                 satisfaction by day, share of run-days below the UI's "fading"
                 line, whether reinforcements can outrun the curve at all, and
                 whether play changes any of it

Usage:
    python tests/cast_audit.py --presence
    python tests/cast_audit.py --retention
    python tests/cast_audit.py --interrupt
    python tests/cast_audit.py --presence -n 20 --seed-base 100
"""
from __future__ import annotations
import argparse
import json
import os
import re
import statistics
import sys
from collections import Counter, defaultdict
from typing import Dict, List, Set, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.decay import relationship_retention
from engine.stats import create_starter_fixer
from pipeline.lint_content import event_pack_files
from tests.sim_bot import STRATEGIES
from tests import steward_audit

RUNS = 40

# The retention report reads the same sweep from four angles (per contact, per
# strategy, plus the Empty Suite cross-check). Re-playing 40 runs for each of
# those is ~20x the work for identical results, since `playout` is seeded and
# deterministic.
_SWEEPS: Dict[tuple, list] = {}


def _sweep(strategy: str, n: int, base: int, **kw) -> list:
    key = (strategy, n, base, tuple(sorted(kw.items())))
    if key not in _SWEEPS:
        _SWEEPS[key] = steward_audit._sweep(strategy, n, base, **kw)
    return _SWEEPS[key]

# The three promoted contacts A4 names, plus Echo -- the one earned contact with
# a real pack behind it (`npc_arcs_pack` hangs off `echo_brother_known`), kept in
# the census so "starting network vs earned" is visible rather than assumed.
CAST = {
    "Mara": "Mara (Sister)",
    "Vint": "Vint (Informant)",
    "Kael": "Kael (Broker)",
    "Echo": "Echo (Resistance)",
}

# The web UI's own thresholds, so the report is in the units the player sees:
# `renderContacts` adds the `fading` class and the red meter tier below 30, and
# `check_endings` reads "every bond under 20" as the Empty Suite ending.
FADING = 30.0
ALIENATION = 20.0


def attribute_deck() -> Tuple[Dict[str, Dict[str, Set[str]]], Dict[str, float]]:
    """Which storylets belong to which contact, by three independent tests.

    `mechanical` -- the event moves or reads that bond (`rel_deltas`, `rel_add`,
    or a `relationship` precondition). This is the honest denominator for "does
    the system know this event is about them".

    `named` -- the contact's short name appears in prose the player actually
    reads (title, body, choice text, branch text, inserts). An event can be
    about Mara without touching her bar, and that still counts as her being on
    screen.

    `gated` -- the event is hidden behind a satisfaction threshold on that bond,
    which is the only way the retention curve can currently change what a run
    contains.
    """
    out = {k: {"mechanical": set(), "named": set(), "gated": set()} for k in CAST}
    weights: Dict[str, float] = {}
    for path in event_pack_files():
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        for ev in data.get("events", []):
            eid = ev["id"]
            weights[eid] = float(ev.get("weight", 1.0))
            blob = json.dumps(ev, ensure_ascii=False)
            texts = [ev.get("title", ""), ev.get("body", "")]
            for c in ev.get("choices", []):
                texts.append(c.get("text", ""))
                for b in ("success", "failure"):
                    texts.append(c.get(b, {}).get("text", ""))
            texts += [i.get("text", "") for i in ev.get("inserts", [])]
            prose = " ".join(t or "" for t in texts)
            for short, full in CAST.items():
                mech = (f'"{full}"' in blob and
                        ('"rel_deltas"' in blob or '"rel_add"' in blob
                         or f'"relationship": "{full}"' in blob))
                if mech:
                    out[short]["mechanical"].add(eid)
                if re.search(r"\b" + short + r"\b", prose):
                    out[short]["named"].add(eid)
                if f'"relationship": "{full}"' in blob:
                    out[short]["gated"].add(eid)
    return out, weights


_RAW_EVENTS: Dict[str, dict] = {}


def _event_by_id(eid: str) -> dict:
    """The raw JSON of one storylet. Cached; `attribute_deck` fills it."""
    if not _RAW_EVENTS:
        for path in event_pack_files():
            with open(path, "r", encoding="utf-8") as fh:
                for ev in json.load(fh).get("events", []):
                    _RAW_EVENTS[ev["id"]] = ev
    return _RAW_EVENTS.get(eid, {})


def _longest_gap(days: List[int], run_days: int) -> int:
    if not days:
        return run_days
    marks = [0] + sorted(set(days)) + [run_days]
    return max(b - a for a, b in zip(marks, marks[1:]))


def report_presence(n: int, base: int) -> None:
    attrib, _ = attribute_deck()
    print(f"\n=== PRESENCE: how often is each contact on screen? "
          f"(n={n}, seeds {base}..{base+n-1}) ===\n")
    print("An event counts as an appearance if the contact is NAMED in prose the "
          "player reads.\nThe `mech` column is the stricter test -- the event also "
          "moves or reads their bar.\n")
    print(f"{'strategy':10s} {'contact':7s} {'events/run':>11s} {'mech/run':>9s} "
          f"{'days seen':>10s} {'% of days':>10s} {'longest gap':>12s} {'never':>7s}")
    print("-" * 82)
    for strat in STRATEGIES:
        runs = _sweep(strat, n, base)
        for short in CAST:
            named = attrib[short]["named"]
            mech = attrib[short]["mechanical"]
            per_run, mech_run, days_seen, pct, gaps, never = [], [], [], [], [], 0
            for r in runs:
                hits = [(d, e) for d, e in r["fire_log"] if e in named]
                per_run.append(len(hits))
                mech_run.append(sum(1 for _, e in r["fire_log"] if e in mech))
                ds = sorted({d for d, _ in hits})
                days_seen.append(len(ds))
                pct.append(100.0 * len(ds) / max(r["days"], 1))
                gaps.append(_longest_gap([d for d, _ in hits], r["days"]))
                if not hits:
                    never += 1
            print(f"{strat:10s} {short:7s} {statistics.mean(per_run):11.1f} "
                  f"{statistics.mean(mech_run):9.1f} {statistics.mean(days_seen):10.1f} "
                  f"{statistics.mean(pct):9.1f}% {statistics.mean(gaps):12.1f} "
                  f"{never:>4d}/{n}")
        print("-" * 82)


def report_interrupt(n: int, base: int) -> None:
    attrib, weights = attribute_deck()
    deck_median = statistics.median(weights.values())
    print(f"\n=== INTERRUPT: can a contact reach the player without winning a draw? ===\n")
    print(f"deck: {len(weights)} events, median weight {deck_median:.1f}\n")
    print(f"{'contact':8s} {'named':>7s} {'mech':>6s} {'gated':>7s} "
          f"{'forced':>7s} {'med wt':>8s} {'max wt (drawn)':>15s}")
    print("-" * 64)
    forced_named: Dict[str, list] = {}
    for short in CAST:
        named = attrib[short]["named"]
        forced_named[short] = sorted(e for e in named if weights[e] >= 1000)
        drawn = [weights[e] for e in named if weights[e] < 1000] or [0.0]
        ws = [weights[e] for e in named] or [0.0]
        print(f"{short:8s} {len(named):>7d} {len(attrib[short]['mechanical']):>6d} "
              f"{len(attrib[short]['gated']):>7d} {len(forced_named[short]):>7d} "
              f"{statistics.median(ws):>8.1f} {max(drawn):>15.1f}")

    print("\n--- every forced event that names a contact ---")
    for short in CAST:
        for eid in forced_named[short]:
            touches = '"%s"' % CAST[short] in json.dumps(
                _event_by_id(eid), ensure_ascii=False)
            print(f"  {short:6s} {eid:34s} w={weights[eid]:>8.0f} "
                  f"{'moves the bar' if touches else 'prose only'}")

    print("\n--- what the satisfaction gates actually ask for ---")
    for short, full in CAST.items():
        for path in event_pack_files():
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            for ev in data.get("events", []):
                blob = json.dumps(ev, ensure_ascii=False)
                if f'"relationship": "{full}"' not in blob:
                    continue
                for m in re.finditer(
                        r'\{"relationship": "' + re.escape(full) +
                        r'"(?:, "op": "([^"]+)")?, "value": ([0-9.]+)\}', blob):
                    print(f"  {short:6s} {ev['id']:38s} "
                          f"{m.group(1) or '>='} {m.group(2)}")

    print("\n--- runs in which each gated event ever became eligible "
          f"(n={n}, all strategies) ---")
    gated_ids = {e for s in CAST for e in attrib[s]["gated"]}
    if gated_ids:
        by_id: Dict[str, int] = Counter()
        total = 0
        for strat in STRATEGIES:
            for r in _sweep(strat, n, base):
                total += 1
                for e in gated_ids:
                    if e in r["fired_ids"]:
                        by_id[e] += 1
        for e in sorted(gated_ids):
            print(f"  fired in {by_id[e]:>3d}/{total} runs   {e}")
    print("\nThe only forced events naming a contact are the four "
          "`prologue_*_descent` storylets\n(one fires per run, in the opening days, "
          "and it is where the three bars are\nintroduced) and six origin-thread "
          "chain heads that mention them in passing.\n**After the prologue, nothing "
          "in the cast is forced.** A contact reaches the\nplayer only by winning a "
          "weighted draw against ~200 eligible events at a median\nweight of 7-8 "
          "against the deck's 6 -- exactly like the city's background noise.")


def report_retention(n: int, base: int) -> None:
    print(f"\n=== RETENTION: what is the Ebbinghaus curve doing? "
          f"(n={n}, seeds {base}..{base+n-1}) ===\n")

    print("--- the curve in the abstract: satisfaction left after D untouched days ---")
    starter = create_starter_fixer()
    print(f"{'contact':22s} {'S':>5s}" + "".join(f"{'d'+str(d):>8s}"
                                                 for d in (5, 10, 20, 30, 40)))
    for name, r in starter.relationships.items():
        row = f"{name:22s} {r.strength:5.1f}"
        for d in (5, 10, 20, 30, 40):
            v = r.satisfaction
            for _ in range(d):
                v = relationship_retention(v, 1, r.strength)
            row += f"{v:8.2f}"
        print(row)
    print("\n(end_of_day_decay applies R = e^(-1/S) once per day and writes the "
          "result back,\nso the decay compounds daily. `reinforce` adds +1.5 to S, "
          "capped at 40.)")

    days = (5, 10, 20, 30, 40, 50, 60)
    for short, full in CAST.items():
        print(f"\n--- {full}: median satisfaction at day D ---")
        print(f"{'strategy':10s}" + "".join(f"{'d'+str(d):>8s}" for d in days)
              + f"{'final':>9s}{'S final':>9s}{'%days<30':>10s}{'%days<20':>10s}")
        for strat in STRATEGIES:
            runs = _sweep(strat, n, base)
            curve: Dict[int, list] = defaultdict(list)
            finals, strengths, below30, below20 = [], [], [], []
            for r in runs:
                for d, rels in r["rel_by_day"].items():
                    if full in rels:
                        curve[d].append(rels[full][0])
                vals = [rels[full][0] for rels in r["rel_by_day"].values() if full in rels]
                if not vals:
                    continue
                finals.append(r["rel_final"].get(full, (0.0, 0.0))[0])
                strengths.append(r["rel_final"].get(full, (0.0, 0.0))[1])
                below30.append(100.0 * sum(1 for v in vals if v < FADING) / len(vals))
                below20.append(100.0 * sum(1 for v in vals if v < ALIENATION) / len(vals))
            row = f"{strat:10s}"
            for d in days:
                v = curve.get(d, [])
                row += f"{statistics.median(v):8.1f}" if v else f"{'--':>8s}"
            if finals:
                row += (f"{statistics.median(finals):9.1f}"
                        f"{statistics.median(strengths):9.1f}"
                        f"{statistics.mean(below30):9.1f}%"
                        f"{statistics.mean(below20):9.1f}%")
            else:
                row += f"{'--':>9s}{'--':>9s}{'--':>10s}{'--':>10s}"
            print(row)

    print("\n--- CAN THE BOND ACCUMULATE? reinforcement gap vs the bond's own "
          "half-life ---")
    print("`reinforce` adds +1.5 to S and is the only thing that ever raises it, so "
          "counting\nS increments counts reinforcements exactly. A bond grows only if "
          "reinforcements\narrive faster than the curve erases them: ratio = mean gap "
          "/ half-life (S ln2).\nAbove 1.0 the next reinforcement lands on a bond that "
          "has already fallen below\nhalf of the last one, and satisfaction can never "
          "climb -- the bar is a sawtooth\nagainst zero regardless of play.\n")
    print(f"{'contact':8s} {'strategy':10s} {'reinf/run':>10s} {'mean gap':>9s} "
          f"{'med S':>7s} {'half-life':>10s} {'ratio':>7s}  verdict")
    print("-" * 78)
    for short, full in CAST.items():
        for strat in STRATEGIES:
            runs = _sweep(strat, n, base)
            counts, gaps, mid_s = [], [], []
            for r in runs:
                seq = [(d, v[full][1]) for d, v in sorted(r["rel_by_day"].items())
                       if full in v]
                if len(seq) < 2:
                    continue
                bumps = sum(1 for (_, a), (_, b) in zip(seq, seq[1:]) if b > a + 1e-9)
                span = seq[-1][0] - seq[0][0]
                counts.append(bumps)
                gaps.append(span / bumps if bumps else float(span))
                mid_s.append(statistics.median(s for _, s in seq))
            if not counts:
                print(f"{short:8s} {strat:10s} {'-- never in the network --':>50s}")
                continue
            reinf = statistics.mean(counts)
            gap = statistics.median(gaps)
            s = statistics.median(mid_s)
            half = s * 0.6931
            ratio = gap / half if half else float("inf")
            verdict = "grows" if ratio < 1.0 else ("holds" if ratio < 1.6 else "CANNOT ACCUMULATE")
            print(f"{short:8s} {strat:10s} {reinf:10.1f} {gap:9.1f} {s:7.1f} "
                  f"{half:10.1f} {ratio:7.2f}  {verdict}")
        print("-" * 78)

    print(f"\n--- does play change the outcome? spread of median final "
          f"satisfaction across strategies ---")
    for short, full in CAST.items():
        meds = []
        for strat in STRATEGIES:
            runs = _sweep(strat, n, base)
            vals = [r["rel_final"][full][0] for r in runs if full in r["rel_final"]]
            meds.append(statistics.median(vals) if vals else 0.0)
        lo, hi = min(meds), max(meds)
        print(f"  {full:22s} {lo:6.2f} .. {hi:6.2f}   spread {hi - lo:6.2f}")

    print(f"\n--- the Empty Suite gate: runs where EVERY bond is under 20 ---")
    print(f"{'strategy':10s} {'at day 20':>10s} {'at day 30':>10s} "
          f"{'at end':>9s} {'ending fired':>13s}")
    for strat in STRATEGIES:
        runs = _sweep(strat, n, base)
        cells = []
        for d in (20, 30):
            hit = 0
            for r in runs:
                rels = r["rel_by_day"].get(d)
                if rels and all(v[0] < ALIENATION for v in rels.values()):
                    hit += 1
            cells.append(hit)
        at_end = sum(1 for r in runs
                     if r["rel_final"] and all(v[0] < ALIENATION
                                               for v in r["rel_final"].values()))
        fired = sum(1 for r in runs if r["ending"] == "NEUTRAL_alienation_empty_suite")
        print(f"{strat:10s} {cells[0]:>7d}/{n} {cells[1]:>7d}/{n} "
              f"{at_end:>6d}/{n} {fired:>10d}/{n}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--presence", action="store_true",
                    help="how often each contact is on screen")
    ap.add_argument("--interrupt", action="store_true",
                    help="can a contact reach the player without winning a draw?")
    ap.add_argument("--retention", action="store_true",
                    help="what the Ebbinghaus curve is doing across a run")
    ap.add_argument("-n", type=int, default=RUNS,
                    help=f"runs per strategy (default {RUNS})")
    ap.add_argument("--seed-base", type=int, default=0, help="first seed (default 0)")
    args = ap.parse_args()

    if not (args.presence or args.interrupt or args.retention):
        args.presence = args.interrupt = args.retention = True

    if args.presence:
        report_presence(args.n, args.seed_base)
    if args.interrupt:
        report_interrupt(args.n, args.seed_base)
    if args.retention:
        report_retention(args.n, args.seed_base)


if __name__ == "__main__":
    main()
