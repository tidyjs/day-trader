"""Entrypoint for the scheduled morning scan (SPEC 9, M7).

GitHub Actions cron is UTC only and has no DST, so the workflow fires at
13:15 and 14:15 UTC on weekdays (09:15 New York time in summer (EDT) and in
winter (EST) respectively), plus a 15:30 UTC backstop (10:30 EST / 11:30 EDT)
that alerts if no scan exists. This script decides from New York time what
each run does:

  - before 09:15 ET: the off-season entry, exit quietly
  - 09:15 to 10:00 ET: scan (GitHub often starts cron runs late; a start after
    the 09:30 open is still scanned but marked late)
  - after 10:00 ET: too late to be useful; this is the off-season entry, exit
    quietly, unless today's scan never ran, which is a failure alert
  - not a trading day (weekend, holiday): exit quietly
  - today's scan file already exists: exit quietly (idempotent, so a delayed
    off-season run can't scan twice)

Any error after the decision to scan sends a "Scanner failed" alert and exits
non-zero, so silence never means failure.

Usage:
  python -m src.run                         # what the workflow runs
  python -m src.run --now 2026-11-16T09:15  # pretend it's this ET time
  python -m src.run --force-error           # verify the failure alert path
  python -m src.run --mode test_message     # manual: write one test message only
  python -m src.run --mode past_day         # manual: re-run the last completed day
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Callable, Optional

from src import alerts
from src.config import ROOT, load_config, load_env
from src.timeutil import ET

SCAN_START = time(9, 15)
LATE_AFTER = time(9, 30)   # market open
WINDOW_END = time(10, 0)


@dataclass
class Decision:
    action: str            # "scan" | "skip" | "alert"
    reason: str
    late: bool = False


def decide(now_et: datetime, is_trading_day: bool, scan_exists: bool) -> Decision:
    """Pure gating logic; tested for both sides of DST."""
    t = now_et.timetz().replace(tzinfo=None)
    if not is_trading_day:
        return Decision("skip", f"{now_et.date()} is not a trading day")
    if scan_exists:
        return Decision("skip", f"scan for {now_et.date()} already exists")
    if t < SCAN_START:
        return Decision("skip", f"{t:%H:%M} ET is before the {SCAN_START:%H:%M} scan time (off-season cron entry)")
    if t < WINDOW_END:
        return Decision("scan", f"{t:%H:%M} ET is inside the scan window", late=t >= LATE_AFTER)
    # After the window. In the off season this entry fires at ~10:15 ET every day,
    # by which time the in-season entry should have produced today's scan.
    return Decision("alert", f"{t:%H:%M} ET and no scan for {now_et.date()}: the morning scan did not run in time")


def halts_coverage_note() -> str:
    """For the run summary: has the halts feed shown NYSE yet? (SPEC 4.3)"""
    import csv

    p = ROOT / "data" / "halts_markets.csv"
    if not p.exists():
        return "halts feed: no fetches logged yet"
    rows = list(csv.DictReader(p.open()))
    weekday_days = sorted({r["fetched_at"][:10] for r in rows if datetime.fromisoformat(r["fetched_at"]).weekday() < 5})
    nyse = [r["fetched_at"] for r in rows if any(m.split(":")[0] == "NYSE" for m in r["markets"].split())]
    if nyse:
        return f"halts feed: NYSE first seen {nyse[0]}; add NYSE to halts.confirmed_markets"
    return f"halts feed: NYSE not seen yet ({len(weekday_days)} weekday(s) of fetches; markets so far: {rows[-1]['markets'] or 'none'})"


MARKET_CLOSE = time(16, 0)
MODES = ("normal", "test_message", "past_day")


def run_test_message(now: datetime) -> int:
    """Manual mode: write one labelled test message. No scan, no API calls."""
    alerts.send("test", f"Test message {now:%Y-%m-%d %H:%M} ET",
                "This is a **test message** from a manual workflow run (`mode: test_message`).\n\n"
                "It only checks that messages are written to `messages/` and committed back. No scan ran, nothing to act on.", now)
    return 0


def past_trading_day(now: datetime, trading_day_fn: Callable[[date], bool], prior_day_fn: Callable[[date], date]) -> date:
    """The most recent completed trading day: today once the market has closed, else the one before."""
    if trading_day_fn(now.date()) and now.timetz().replace(tzinfo=None) >= MARKET_CLOSE:
        return now.date()
    return prior_day_fn(now.date())


def run_past_day(now: datetime, trading_day_fn, prior_day_fn, past_scan_fn: Optional[Callable[[date], dict]] = None) -> int:
    """Manual mode: re-run the scan for the most recent completed trading day, as of
    its own 09:15 ET cutoff, and write its summary marked as a manual re-run.
    Overwrites that day's saved scan file (re-fetched data)."""
    from src import scan, summary

    try:
        day = past_trading_day(now, trading_day_fn, prior_day_fn)
        print(f"[run] manual past_day: re-running the scan for {day} as of 09:15 ET")
        out = (past_scan_fn or (lambda d: scan.run(d, "09:15")))(day)
        subject, body = summary.subject_and_body(out, halts_note=halts_coverage_note(), rerun_of=day.isoformat())
        alerts.send("scan_summary", subject, body, now)
        return 0
    except Exception as e:
        alerts.send("scanner_failed", f"Scanner failed {now:%Y-%m-%d}: manual past_day re-run",
                    alerts.failure_body(e, "Manual past_day re-run failed."), now)
        return 1


def main(argv=None, scan_fn: Optional[Callable] = None, trading_day_fn: Optional[Callable[[date], bool]] = None,
         prior_day_fn: Optional[Callable[[date], date]] = None, past_scan_fn: Optional[Callable[[date], dict]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--now", help="pretend time, ET, e.g. 2026-11-16T09:15")
    ap.add_argument("--force-error", action="store_true", help="raise inside the scan to verify the failure alert")
    ap.add_argument("--mode", choices=MODES, default="normal",
                    help="normal: time-gated morning scan; test_message: write a test message only; "
                         "past_day: re-run the last completed trading day's scan and write its summary")
    a = ap.parse_args(argv)
    load_env()
    cfg = load_config()
    now = datetime.fromisoformat(a.now).replace(tzinfo=ET) if a.now else datetime.now(tz=ET)
    from src import scan

    if a.mode == "test_message":
        return run_test_message(now)
    if a.mode == "past_day":
        if trading_day_fn is None or prior_day_fn is None:
            from src.data.alpaca import Alpaca

            alp = Alpaca()
            trading_day_fn = trading_day_fn or (lambda d: scan.trading_days(alp, d)[0])
            prior_day_fn = prior_day_fn or (lambda d: scan.trading_days(alp, d)[1])
        return run_past_day(now, trading_day_fn, prior_day_fn, past_scan_fn)

    try:
        if trading_day_fn is None:
            from src.data.alpaca import Alpaca

            trading_day_fn = lambda d: scan.trading_days(Alpaca(), d)[0]  # noqa: E731
        is_td = trading_day_fn(now.date())
    except Exception as e:  # can't even tell whether to scan: that is a failure too
        alerts.send("scanner_failed", f"Scanner failed {now:%Y-%m-%d}: calendar check", alerts.failure_body(e, "Trading-calendar check failed."), now)
        return 1
    exists = scan.scan_path(cfg, now.date(), datetime.combine(now.date(), SCAN_START, tzinfo=ET)).exists()
    d = decide(now, is_td, exists)
    print(f"[run] {now:%Y-%m-%d %H:%M} ET: {d.action} ({d.reason})")
    if d.action == "skip":
        return 0
    if d.action == "alert":
        if alerts.already_sent_today("scanner_failed", now):
            print("[run] failure already alerted today")
            return 1
        alerts.send("scanner_failed", f"Scanner failed {now:%Y-%m-%d}: no morning scan", d.reason, now)
        return 1
    try:
        if a.force_error:
            raise RuntimeError("forced error (--force-error) to verify the failure alert")
        # Scan as of the scheduled 09:15 ET, never later, so a late start sees the same data
        # cutoff as an on-time one (no look-ahead from the delay).
        as_of = "09:15"
        out = (scan_fn or (lambda: scan.run(now.date(), as_of)))()
        s = out["summary"]
        print(f"[run] scan done: {s['candidates']} candidates, {s['eligible']} eligible{' (LATE START)' if d.late else ''}")
        note = halts_coverage_note()
        print(f"[run] {note}")
        # Every scan day leaves a message, so silence is never ambiguous (SPEC 8).
        from src import summary
        subject, body = summary.subject_and_body(out, late=d.late, halts_note=note)
        alerts.send("scan_summary", subject, body, now)
        return 0
    except Exception as e:
        alerts.send("scanner_failed", f"Scanner failed {now:%Y-%m-%d}", alerts.failure_body(e, f"Morning scan failed ({d.reason})."), now)
        return 1


if __name__ == "__main__":
    sys.exit(main())
