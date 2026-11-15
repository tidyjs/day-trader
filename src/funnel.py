"""Funnel report from data/candidates.csv. Per rule, in cost order (the order
the scanner applies them):
  failed            names that failed it
  failed only this  names that failed it and no other rule
  reached           names that passed (or were unknown on) every earlier rule
  failed at step    of those reached, how many it removed
Read-only; it never changes thresholds.

Usage: python -m src.funnel [--from 2026-11-09] [--to 2026-11-13]
"""
from __future__ import annotations

import argparse
import csv
from typing import Dict, List

from src.config import ROOT, load_config
from src.scan import DISQUALIFIERS, MUST_PASS

# Cost order: bar rules, daily history, EDGAR, classifier, then Yahoo float last.
RULES = MUST_PASS + DISQUALIFIERS + ["rule_float"]


def funnel(rows: List[dict]) -> List[Dict[str, object]]:
    out = []
    for i, rule in enumerate(RULES):
        failed = [r for r in rows if r.get(rule) == "fail"]
        only = [r for r in failed if all(r.get(o) != "fail" for o in RULES if o != rule)]
        reached = [r for r in rows if all(r.get(o) != "fail" for o in RULES[:i])]
        out.append({
            "rule": rule,
            "fail": len(failed),
            "fail_only_this": len(only),
            "reached": len(reached),
            "fail_at_step": sum(1 for r in reached if r.get(rule) == "fail"),
            "unknown": sum(1 for r in rows if r.get(rule) == "unknown"),
            "not_checked": sum(1 for r in rows if r.get(rule, "") == ""),
            "only_this_symbols": " ".join(f"{r['symbol']}({r['date'][5:]})" for r in only),
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start")
    ap.add_argument("--to", dest="end")
    a = ap.parse_args()
    path = ROOT / load_config()["paths"]["candidates"]
    rows = [r for r in csv.DictReader(path.open()) if (not a.start or r["date"] >= a.start) and (not a.end or r["date"] <= a.end)]
    days = sorted({r["date"] for r in rows})
    print(f"{len(rows)} candidates over {len(days)} days ({days[0]} to {days[-1]}); eligible: {sum(r['eligible'] == 'True' for r in rows)}\n")
    print("| # | rule (cost order) | failed | failed only this | reached (passed all earlier) | failed at this step | unknown | not checked | only-this names |")
    print("|---|---|---|---|---|---|---|---|---|")
    for i, f in enumerate(funnel(rows), 1):
        print(f"| {i} | {f['rule']} | {f['fail']} | {f['fail_only_this']} | {f['reached']} | {f['fail_at_step']} | {f['unknown']} | {f['not_checked']} | {f['only_this_symbols']} |")


if __name__ == "__main__":
    main()
