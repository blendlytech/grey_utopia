"""pargate.py -- parallel front-end for the sim_bot balance regression gate.

`sim_bot.py all --assert` is ~28 minutes single-threaded. Every playout is an
independent, deterministic function of (strategy, seed) -- `load_all_events()`
resets per-run event state on entry -- so fanning the same 1000x4 grid across
processes reproduces the gate's numbers exactly, in a fraction of the time.

Usage:
    python tests/pargate.py                 # the full gate; exit 1 on violation
    python tests/pargate.py -n 200          # smaller N for a quick read
    python tests/pargate.py -j 8            # cap worker processes

Set GU_ROOT to run the gate against a different checkout -- a git worktree
holding a candidate tuning change -- rather than the tree this file lives in:

    GU_ROOT=/path/to/worktree python tests/pargate.py
"""
from __future__ import annotations
import argparse
import importlib.util
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List, Tuple

ITERATIONS = 1000


def gu_root() -> str:
    """The checkout to simulate: GU_ROOT if set, else this file's own tree."""
    env = os.environ.get("GU_ROOT")
    default = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    return os.path.abspath(env or default)


def load_sim_bot(root: str):
    """Import sim_bot by path so GU_ROOT decides which tree's engine/data runs.

    sim_bot puts its own parent on sys.path at import time, so `engine` and
    `data` resolve inside `root` and not in whichever tree launched us.
    """
    path = os.path.join(root, "tests", "sim_bot.py")
    if not os.path.isfile(path):
        raise SystemExit(f"pargate: no tests/sim_bot.py under GU_ROOT={root}")
    spec = importlib.util.spec_from_file_location("gu_sim_bot", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["gu_sim_bot"] = module
    spec.loader.exec_module(module)
    return module


_SIM = None


def _init_worker(root: str) -> None:
    global _SIM
    _SIM = load_sim_bot(root)


def _play(job: Tuple[str, int]) -> Tuple[str, str, int, float]:
    strategy, seed = job
    res = _SIM.run_single_simulation(strategy=strategy, seed=seed)
    return strategy, res["ending"], res["day"], res["wealth"]


def tally(rows: List[Tuple[str, str, int, float]], strategies, iterations: int
          ) -> Dict[str, Dict[str, float]]:
    """Fold raw playouts into the percentage dicts run_monte_carlo returns."""
    results: Dict[str, Dict[str, float]] = {}
    for strategy in strategies:
        mine = [r for r in rows if r[0] == strategy]
        counts: Dict[str, int] = {}
        for _, ending, _day, _wealth in mine:
            counts[ending] = counts.get(ending, 0) + 1
        dist = {e: (c / len(mine)) * 100 for e, c in counts.items()}
        dist["_avg_days"] = sum(r[2] for r in mine) / len(mine)
        dist["_avg_wealth"] = sum(r[3] for r in mine) / len(mine)
        results[strategy] = dist
    return results


def report(results: Dict[str, Dict[str, float]], sim, iterations: int) -> None:
    for strategy, dist in results.items():
        print(f"\n=== Monte Carlo: {iterations} playouts, strategy='{strategy}' ===")
        print(f"  Average Survival: {dist['_avg_days']:.1f} days | "
              f"Average Wealth at end: {dist['_avg_wealth']:,.0f} cr")
        print("  Ending Distribution:")
        endings = {k: v for k, v in dist.items() if not k.startswith("_")}
        for ending, pct in sorted(endings.items(), key=lambda kv: kv[1], reverse=True):
            print(f"    - {ending}: {round(pct * iterations / 100)} ({pct:.1f}%)")
        print(f"  TOTAL_GOOD {sim.total_good(dist):5.1f}%   "
              f"TOTAL_TERMINAL {sim.total_terminal(dist):5.1f}%")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-n", "--iterations", type=int, default=ITERATIONS,
                    help=f"seeds per strategy (default {ITERATIONS})")
    ap.add_argument("-j", "--jobs", type=int, default=os.cpu_count(),
                    help="worker processes (default: all cores)")
    ap.add_argument("--no-assert", action="store_true",
                    help="print the tables but skip the regression gate")
    args = ap.parse_args()

    root = gu_root()
    sim = load_sim_bot(root)
    strategies = sim.STRATEGIES
    jobs = [(s, seed) for s in strategies for seed in range(args.iterations)]

    print(f"pargate: {len(jobs)} playouts "
          f"({args.iterations} seeds x {len(strategies)} strategies) "
          f"on {args.jobs} workers")
    print(f"         root {root}")

    started = time.time()
    rows: List[Tuple[str, str, int, float]] = []
    with ProcessPoolExecutor(max_workers=args.jobs,
                             initializer=_init_worker, initargs=(root,)) as pool:
        for row in pool.map(_play, jobs, chunksize=16):
            rows.append(row)
            if len(rows) % 400 == 0:
                rate = len(rows) / (time.time() - started)
                eta = (len(jobs) - len(rows)) / rate
                print(f"         {len(rows):5d}/{len(jobs)}  "
                      f"{rate:5.1f} runs/s  eta {eta / 60:4.1f}m", flush=True)

    elapsed = time.time() - started
    results = tally(rows, strategies, args.iterations)
    report(results, sim, args.iterations)
    print(f"\npargate: {len(jobs)} playouts in {elapsed / 60:.1f}m "
          f"({len(jobs) / elapsed:.1f} runs/s)")

    if args.no_assert:
        return 0
    return 1 if sim.run_balance_assertions(results) else 0


if __name__ == "__main__":
    sys.exit(main())
