"""Interim "scan summary" message, written after every successful scan so a
scan day is never silent (SPEC 8). M5 replaces it with the real morning
shortlist and "No trade today" messages once M4 computes levels and sizing.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.scan import DISQUALIFIERS, MUST_PASS

NOT_YET = ("**Levels not shown yet:** trigger, stop, share count and 1.5R target are computed (M4) but held back "
           "until you have reviewed them. This list is for checking the scanner only. Do not trade from it.")


def _fmt_int(x) -> str:
    try:
        return f"{float(x):,.0f}"
    except (TypeError, ValueError):
        return "-"


def subject_and_body(out: Dict[str, Any], late: bool = False, halts_note: str = "", rerun_of: Optional[str] = None) -> Tuple[str, str]:
    s = out["summary"]
    cands: List[dict] = out["candidates"]
    elig = [r for r in cands if r.get("eligible")]
    day = cands[0]["date"] if cands else (rerun_of or out.get("day", ""))
    cutoff = cands[0]["data_cutoff_et"][11:16] if cands else ""
    short = sorted((r for r in cands if r.get("shortlist_rank")), key=lambda r: r["shortlist_rank"])
    n_a = sum(1 for r in short if r.get("tier") == "A")
    n_b = len(short) - n_a
    subject = (f"Scan summary: {n_a} Tier A, {n_b} Tier B" if short else "Scan summary: no names passed")
    if rerun_of:
        subject = f"Manual re-run for {rerun_of}: " + subject[len("Scan summary: "):]
    lines = []
    if rerun_of:
        lines += [f"**Manual re-run** (`mode: past_day`) of the {rerun_of} scan, as of 09:15 ET that day, run after the fact. "
                  "It uses today's asset list, T212 list and float, so it is a check, not the original morning result.", ""]
    if late:
        lines += ["**Late start:** the workflow began after the 09:30 open. The scan still used data up to the normal cutoff.", ""]
    tiers = s.get("tiers", {})
    lines += [
        NOT_YET, "",
        f"Levels use data up to about {cutoff or '09:00'} ET. Re-check the live premarket high at the open.", "",
        f"- candidates (price and gap passed): {s['candidates']}",
        f"- Tier A (every rule): {tiers.get('A', s.get('eligible', 0))}; Tier B (no continuation or prior-range rule): {tiers.get('B', 0)}",
        f"- shown below: {len(short)} (at most 5, Tier A first)",
    ]

    def table(rows: List[dict], title: str) -> List[str]:
        if not rows:
            return []
        out = ["", f"## {title}", "", "| # | ticker | score | price | gap % | premarket $ vol | catalyst | warnings |", "|---|---|---|---|---|---|---|---|"]
        for r in rows:
            cat = f"{r.get('catalyst_type') or '-'} q{r.get('catalyst_quality') if r.get('catalyst_quality') is not None else '-'}: {r.get('catalyst_summary') or ''}"
            warns = (r.get("warnings") or "-").replace("; ", "<br>")
            out.append(f"| {r['shortlist_rank']} | {r['symbol']} | {r.get('score')} | {r['price']} | {r['gap_pct']} | {_fmt_int(r['pm_dollar_volume'])} "
                       f"| {cat.replace('|', '/')} | {warns.replace('|', '/')} |")
        return out

    lines += table([r for r in short if r.get("tier") == "A"], "Tier A: passed every rule")
    lines += table([r for r in short if r.get("tier") == "B"], "Tier B: same rules without continuation and prior range (pre-declared 2026-11-16)")
    if not short:
        lines += ["", "No name passed Tier A or Tier B today."]
    held = [r for r in cands if r.get("tier") and not r.get("shortlist_rank")]
    if held:
        lines += ["", "## Tier names not shown", ""] + [
            f"- {r['symbol']} (Tier {r['tier']}): {r.get('levels_status') if r.get('levels_status') != 'ok' else 'beyond the 5-name limit'}" for r in held]
    # Where the other candidates stopped, in cost order (first failing rule).
    order = MUST_PASS + DISQUALIFIERS + ["rule_float"]
    stopped: Dict[str, List[str]] = {}
    for r in cands:
        if r.get("tier"):
            continue
        first = next((c for c in order if r.get(c) == "fail"), "unknown/other")
        stopped.setdefault(first, []).append(r["symbol"])
    if stopped:
        lines += ["", "## Where the other candidates stopped (first failing rule)", ""]
        for c in order + ["unknown/other"]:
            if c in stopped:
                lines.append(f"- {c}: {', '.join(stopped[c])}")
    if s.get("warnings"):
        lines += ["", "## Scan-level warnings", ""] + [f"- {w}" for w in s["warnings"]]
    if halts_note:
        lines += ["", f"_{halts_note}_"]
    lines += ["", f"Full detail: `data/scans/{day}.json` and `data/candidates.csv`."]
    return subject, "\n".join(lines)
