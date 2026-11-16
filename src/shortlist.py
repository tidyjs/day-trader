"""M5 messages (SPEC 8): the morning shortlist, "No names today", and the
failure message. Markdown, written to messages/ and opened as a GitHub Issue.

Shortlist order (at most account.max_shortlist names in total):
  Tier A   every rule passed; by score
  Tier B   Tier A rules without continuation and prior range; by score
  Watch    pre-declared 2026-11-16 (SPEC 4.4c): on T212, price and gap passed,
           premarket $ volume >= the minimum, in no tier; never a name with an
           offering disqualifier or a pending reverse split. By premarket $ volume,
           each with its reason (no_catalyst / promo / other) shown prominently.

Never shown: trigger, stop, share counts or targets (2026-11-16). Those live in
candidates.csv for M6's background reference trade only.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.scan import DISQUALIFIERS, MUST_PASS

CUTOFF_NOTE = "Levels use data up to about {cutoff} ET. Re-check the live premarket high at the open."
SYMBOL = {"pass": "✓", "fail": "✗", "unknown": "?", "": "–"}
WATCH_BANNER = {
    "no_catalyst": "> **WATCH: NO VERIFIABLE CATALYST** (and no prior-day volume surge)",
    "promo": "> **WATCH: PROMO / PUMP FLAGGED** by at least 2 of 3 classifier runs",
    "other": "> **WATCH: in no tier** (see the rules line)",
}
RULE_LABELS = [
    ("rule_price", "price"), ("rule_gap", "gap"), ("rule_t212", "T212"), ("rule_pm_dollar_volume", "$ vol"),
    ("rule_pm_trades", "trades"), ("rule_continuation", "continuation"), ("rule_prior_range", "prior range"),
    ("rule_float", "float"), ("dq_offering", "no offering"), ("dq_reverse_split", "no pending split"),
    ("dq_promo_or_no_catalyst", "catalyst"),
]


def _n(x, digits=0) -> str:
    try:
        return f"{float(x):,.{digits}f}"
    except (TypeError, ValueError):
        return "–"


def _m(x) -> str:
    try:
        return f"{float(x) / 1e6:.1f}M"
    except (TypeError, ValueError):
        return "unknown"


def groups(cands: List[dict], cfg: Dict[str, Any]) -> Tuple[List[dict], List[dict], List[dict]]:
    """(Tier A, Tier B, Watch), together at most max_shortlist names."""
    cap = cfg["account"]["max_shortlist"]
    a = sorted((r for r in cands if r.get("tier") == "A"), key=lambda r: (r.get("shortlist_rank") or 99))
    b = sorted((r for r in cands if r.get("tier") == "B"), key=lambda r: (r.get("shortlist_rank") or 99))
    # Watch membership is decided by the scanner (scan.watch_reason, pre-declared 2026-11-16).
    watch = sorted((r for r in cands if r.get("watch_reason")), key=lambda r: (-float(r.get("pm_dollar_volume") or 0), r["symbol"]))
    a = a[:cap]
    b = b[:cap - len(a)]
    watch = watch[:cap - len(a) - len(b)]
    return a, b, watch


def banners(r: dict) -> List[str]:
    out = []
    ev = [e for e in (r.get("evidence") or "").split(" || ") if e.startswith("[reverse_split:")]
    split_ev = [e for e in ev if e.startswith(("[reverse_split:possible]", "[reverse_split:disqualify]"))]
    if r.get("dq_reverse_split") == "fail" or split_ev:
        links = []
        for e in split_ev:
            parts = e.split(" | ")
            links.append(f"[{parts[0].split('] ', 1)[-1]}]({parts[-1].strip()})" if len(parts) >= 3 else parts[0])
        out.append("> **⚠️ REVERSE SPLIT POSSIBLY PENDING**" + (f": {'; '.join(links)}" if links else ""))
    if "merger target: price likely pinned to deal terms" in (r.get("warnings") or ""):
        out.append("> **⚠️ MERGER TARGET: price likely pinned to deal terms**")
    return out


def rules_line(r: dict) -> str:
    return " · ".join(f"{label} {SYMBOL.get(r.get(col, ''), '?')}" for col, label in RULE_LABELS)


def why_not_tiered(r: dict) -> str:
    fails = [label for col, label in RULE_LABELS if r.get(col) == "fail"]
    reasons = r.get("dq_reasons") or ""
    return "fails " + ", ".join(fails) + (f" ({reasons})" if reasons else "") if fails else "no tier (see rules)"


def name_block(r: dict, n: int, kind: str, scan_warnings: Optional[List[str]] = None) -> List[str]:
    title = r.get("name") or ""
    for cut in (" Common Stock", " Ordinary Shares", " Class A"):
        title = title.split(cut)[0]
    score = f" · score {r['score']}" if r.get("score") not in (None, "") else ""
    out = [f"### {n}. {r['symbol']}: {title}{score}", ""]
    if kind == "watch":
        out.append(WATCH_BANNER.get(r.get("watch_reason"), WATCH_BANNER["other"]))
    out += banners(r)
    if out[-1] != "":
        out.append("")
    votes = r.get("catalyst_votes") or ""
    out += [
        f"- **price** {r.get('price', '–')} · **gap** {_n(r.get('gap_pct'), 1)}% vs prior close {r.get('prior_close', '–')}",
        f"- **premarket high** {r.get('pm_high', '–')} full session · {r.get('pm_high_last60') or '–'} in the 60 minutes to the cutoff",
        f"- **premarket** ${_n(r.get('pm_dollar_volume'))} traded · {_n(r.get('pm_trades'))} trades",
        f"- **float** {_m(r.get('float_shares'))}" + (f" ({r['float_source']})" if r.get("float_source") else " (not checked)"),
        f"- **catalyst** {r.get('catalyst_type') or '–'}, quality {r.get('catalyst_quality') if r.get('catalyst_quality') not in (None, '') else '–'}/5"
        + (f" ({votes})" if votes else "") + (f": {r['catalyst_summary']}" if r.get("catalyst_summary") else ""),
        f"- **rules** {rules_line(r)}",
    ]
    if kind == "watch":
        out.append(f"- **not tiered:** {why_not_tiered(r)}")
    skip = set(scan_warnings or [])  # listed once under "Scan warnings", not under every name
    warns = [w for w in (r.get("warnings") or "").split("; ")
             if w and w not in skip and "merger target" not in w and not w.startswith("possible reverse split")]
    if warns:
        out.append("- **warnings:**")
        out += [f"  - {w}" for w in warns]
    return out + [""]


def build(out: Dict[str, Any], cfg: Dict[str, Any], late: bool = False, halts_note: str = "",
          rerun_of: Optional[str] = None) -> Tuple[str, str, str]:
    """(kind, subject, body): kind is "shortlist" or "no_trade"."""
    s, cands = out["summary"], out["candidates"]
    day = cands[0]["date"] if cands else (rerun_of or out.get("day", ""))
    cutoff = cands[0]["data_cutoff_et"][11:16] if cands else "08:59"
    a, b, w = groups(cands, cfg)
    kind = "shortlist" if (a or b or w) else "no_trade"
    head = f"Shortlist {day}: {len(a)} Tier A, {len(b)} Tier B, {len(w)} Watch" if kind == "shortlist" else f"No names today ({day})"
    if rerun_of:
        head = f"Manual re-run: {head}"
    lines: List[str] = [f"> {CUTOFF_NOTE.format(cutoff=cutoff)}", ">",
                        "> Rules output only: names, rule results and warnings.", ""]
    if rerun_of:
        lines += [f"**Manual re-run** of the {rerun_of} scan, as of 09:15 ET that day, run after the fact with today's asset list, T212 list and float.", ""]
    if late:
        lines += ["**Late start:** the workflow began after the 09:30 open; the scan still used data up to the normal cutoff.", ""]
    tiers = s.get("tiers", {})
    lines += [f"Candidates (price and gap passed): {s['candidates']} · Tier A {tiers.get('A', 0)} · Tier B {tiers.get('B', 0)} · Watch {tiers.get('watch', len(w))}"
              f" · shown {len(a) + len(b) + len(w)} of at most {cfg['account']['max_shortlist']}", ""]
    n = 0
    for title, rows, k in (("Tier A: passed every rule", a, "a"),
                           ("Tier B: Tier A rules without continuation and prior range", b, "b"),
                           ("Watch: liquid and on T212, but in no tier", w, "watch")):
        if not rows:
            continue
        lines += [f"## {title}", ""]
        for r in rows:
            n += 1
            lines += name_block(r, n, k, s.get("warnings"))
    if kind == "no_trade":
        lines += ["No name reached Tier A, Tier B or Watch today.", ""]
    shown = {r["symbol"] for r in a + b + w}
    order = MUST_PASS + DISQUALIFIERS + ["rule_float"]
    stopped: Dict[str, List[str]] = {}
    for r in cands:
        if r["symbol"] in shown:
            continue
        if r.get("tier") or r.get("watch_reason"):
            first = "beyond the 5-name limit"
        elif (r.get("dq_offering") == "fail" or r.get("dq_reverse_split") == "fail") and all(
                r.get(c) == "pass" for c in ("rule_price", "rule_gap", "rule_t212", "rule_pm_dollar_volume")):
            # only names that meet every other Watch condition are "excluded from Watch"
            first = "excluded from Watch: " + ("offering disqualifier" if r.get("dq_offering") == "fail" else "pending reverse split")
        else:
            first = next((c for c in order if r.get(c) == "fail"), "other")
        stopped.setdefault(first, []).append(r["symbol"])
    if stopped:
        lines += ["## Not shown (first failing rule)", ""]
        lines += [f"- {k}: {', '.join(v)}" for k, v in stopped.items()]
        lines.append("")
    if s.get("warnings"):
        lines += ["## Scan warnings", ""] + [f"- {x}" for x in s["warnings"]] + [""]
    if halts_note:
        lines += [f"_{halts_note}_", ""]
    lines += [f"Detail: `data/scans/{day}.json`, `data/candidates.csv`."]
    return kind, head, "\n".join(lines)


def failure(subject_day: str, what: str, details: str) -> Tuple[str, str, str]:
    """(kind, subject, body) for "Scanner failed"."""
    body = "\n".join([
        f"> **No shortlist today.** {what}", ">",
        "> Do not use an earlier shortlist: its data is from another day.", "",
        "What to check: the failed run in the repo's **Actions** tab, and `data/` for a partial scan.", "",
        "<details><summary>Error details</summary>", "", details.strip(), "", "</details>",
    ])
    return "scanner_failed", f"Scanner failed {subject_day}", body
