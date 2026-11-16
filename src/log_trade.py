"""Append one of your decisions to data/trades_actual.csv (the decision log).

M6 reports these next to the simulated results, so log every shortlisted
name you looked at, including the ones you skipped.

Examples:
  python -m src.log_trade --date 2026-11-17 --ticker ABCD --tier A --decision skipped \
      --gut 2 --reason "spread too wide at the open"
  python -m src.log_trade --date 2026-11-17 --ticker ABCD --tier A --decision traded --gut 4 \
      --reason "clean break of premarket high" --entry 1.32 --stop 1.24 --shares 30 \
      --exit 1.44 --exit-reason "1.5R partial then trail"

pnl is computed from entry, exit and shares when not given. Fill in the exit
later by logging the same trade again with --update (it replaces that
date + ticker row).
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path
from typing import List, Optional

from src.config import ROOT

COLUMNS = ["date", "ticker", "tier", "decision", "gut_confidence", "reason", "entry", "stop", "shares", "exit", "exit_reason", "pnl"]
PATH = ROOT / "data" / "trades_actual.csv"


def build_row(a: argparse.Namespace) -> dict:
    date.fromisoformat(a.date)  # validates the format
    if a.decision == "traded":
        missing = [n for n in ("entry", "stop", "shares") if getattr(a, n) is None]
        if missing:
            raise SystemExit(f"a traded row needs --{', --'.join(missing)}")
        if a.stop >= a.entry:
            raise SystemExit("--stop must be below --entry (long trades only)")
    pnl = a.pnl
    if pnl is None and a.decision == "traded" and a.exit is not None:
        pnl = round((a.exit - a.entry) * a.shares, 2)
    fmt = lambda x: "" if x is None else (f"{x:g}" if isinstance(x, float) else str(x))  # noqa: E731
    return {
        "date": a.date, "ticker": a.ticker.upper(), "tier": a.tier, "decision": a.decision,
        "gut_confidence": a.gut, "reason": a.reason or "",
        "entry": fmt(a.entry), "stop": fmt(a.stop), "shares": fmt(a.shares), "exit": fmt(a.exit),
        "exit_reason": a.exit_reason or "", "pnl": fmt(pnl),
    }


def append(row: dict, path: Path = PATH, update: bool = False) -> None:
    rows: List[dict] = []
    if path.exists():
        with path.open(newline="") as f:
            rows = list(csv.DictReader(f))
    key = (row["date"], row["ticker"])
    exists = any((r["date"], r["ticker"]) == key for r in rows)
    if exists and not update:
        raise SystemExit(f"{key[0]} {key[1]} is already logged; use --update to replace it")
    rows = [r for r in rows if (r["date"], r["ticker"]) != key] + [row]
    rows.sort(key=lambda r: (r["date"], r["ticker"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)


def main(argv: Optional[List[str]] = None, path: Path = PATH) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True, help="YYYY-MM-DD (the trading day)")
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--tier", required=True, choices=["A", "B", "none"], help="the tier the shortlist showed")
    ap.add_argument("--decision", required=True, choices=["traded", "skipped"])
    ap.add_argument("--gut", required=True, type=int, choices=range(1, 6), metavar="1-5", help="gut confidence, 1 to 5")
    ap.add_argument("--reason", required=True)
    ap.add_argument("--entry", type=float)
    ap.add_argument("--stop", type=float)
    ap.add_argument("--shares", type=float)
    ap.add_argument("--exit", type=float)
    ap.add_argument("--exit-reason", dest="exit_reason")
    ap.add_argument("--pnl", type=float, help="defaults to (exit - entry) x shares")
    ap.add_argument("--update", action="store_true", help="replace an existing date + ticker row")
    a = ap.parse_args(argv)
    row = build_row(a)
    append(row, path, a.update)
    print("logged:", ", ".join(f"{k}={v}" for k, v in row.items() if v != ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
