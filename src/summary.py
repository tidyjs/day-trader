"""Interim "scan summary" message, written after every successful scan so a
scan day is never silent (SPEC 8). M5 replaces it with the real morning
shortlist and "No trade today" messages once M4 computes levels and sizing.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Tuple

from src.scan import DISQUALIFIERS, MUST_PASS

NOT_YET = ("**Not computed yet (M4):** trigger, stop, share count and 1.5R target. "
           "This list is for checking the scanner only. Do not trade from it.")


def _fmt_int(x) -> str:
    try:
        return f"{float(x):,.0f}"
    except (TypeError, ValueError):
        return "-"


def subject_and_body(out: Dict[str, Any], late: bool = False, halts_note: str = "") -> Tuple[str, str]:
    s = out["summary"]
    cands: List[dict] = out["candidates"]
    elig = [r for r in cands if r.get("eligible")]
    day = cands[0]["date"] if cands else ""
    cutoff = cands[0]["data_cutoff_et"][11:16] if cands else ""
    subject = (f"Scan summary: {len(elig)} name(s) passed all rules" if elig else "Scan summary: no names passed all rules")
    lines = []
    if late:
        lines += ["**Late start:** the workflow began after the 09:30 open. The scan still used data up to the normal cutoff.", ""]
    lines += [
        NOT_YET, "",
        f"Prices and gaps use delayed SIP data up to about {cutoff or '09:00'} ET. Re-check the live premarket high at the open.", "",
        f"- candidates (price and gap passed): {s['candidates']}",
        f"- passed every rule: {s['eligible']}",
    ]
    if elig:
        lines += ["", "## Passed every rule", "",
                  "| ticker | price | gap % | premarket $ vol | catalyst | warnings |", "|---|---|---|---|---|---|"]
        for r in elig:
            cat = f"{r.get('catalyst_type') or '-'} q{r.get('catalyst_quality') if r.get('catalyst_quality') is not None else '-'}: {r.get('catalyst_summary') or ''}"
            warns = (r.get("warnings") or "-").replace("; ", "<br>")
            lines.append(f"| {r['symbol']} | {r['price']} | {r['gap_pct']} | {_fmt_int(r['pm_dollar_volume'])} | {cat.replace('|', '/')} | {warns.replace('|', '/')} |")
    else:
        lines += ["", "No name passed every rule today."]
    # Where the other candidates stopped, in cost order (first failing rule).
    order = MUST_PASS + DISQUALIFIERS + ["rule_float"]
    stopped: Dict[str, List[str]] = {}
    for r in cands:
        if r.get("eligible"):
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
