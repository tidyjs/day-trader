"""Scanner: universe, prior close, gap %, T212 filter (M1) and the SPEC 4.1-4.3
filters and flags (M2), with a per-rule candidate log.

Rule order follows cost. Every name that passes price and gap gets the Alpaca
and EDGAR rules; SIP quotes (spread) and Yahoo (float) are fetched only for
names that pass every cheaper must-pass rule and are not disqualified.

The scan is split in three so any day can be reproduced:

  gather_inputs()  pulls everything from the network, using only data that
                   existed at the data cutoff (as_of minus the SIP delay).
  evaluate()       a pure function of the saved inputs and config. No network,
                   no clock.
  save()           writes data/scans/<day>.json (inputs + outputs) and
                   upserts the day's rows in data/candidates.csv.

`python -m src.scan --replay data/scans/<day>.json` re-runs evaluate() on the
saved inputs and fails if the result differs from the saved output.

Usage:
  python -m src.scan                          # live, now (ET)
  python -m src.scan --date 2026-11-13        # as of the configured scan time
  python -m src.scan --date 2026-11-13 --as-of 09:00
  python -m src.scan --replay data/scans/2026-11-13.json
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from src import rules as R
from src.config import ROOT, load_config, load_env
from src.data import halts
from src.data import t212 as t212mod
from src.timeutil import ET, at_et, bar_complete_before, data_cutoff, parse_ts

SCHEMA = 6

# Must-pass rules (SPEC 4.1), in cost order. Float is checked last (Yahoo).
MUST_PASS = ["rule_price", "rule_gap", "rule_t212", "rule_pm_dollar_volume", "rule_pm_trades", "rule_continuation", "rule_prior_range"]
DISQUALIFIERS = ["dq_offering", "dq_reverse_split", "dq_promo_or_no_catalyst"]

CSV_COLUMNS = [
    "date", "as_of_et", "data_cutoff_et", "symbol", "name",
    "prior_date", "prior_close", "price", "gap_pct",
    "pm_high", "pm_high_last60", "pm_volume", "pm_dollar_volume", "pm_trades", "pm_bars", "last_bar_et",
    # per-rule status: pass / fail / unknown / "" (not checked)
    *MUST_PASS, "rule_float",
    *DISQUALIFIERS,
    # what each rule tested
    "continuation_detail", "prior_range_pos_pct", "float_shares", "float_source",
    "edgar_shares_out", "edgar_shares_asof", "yahoo_shares_out", "spread_pct",
    "catalyst_status", "catalyst_type", "catalyst_quality", "catalyst_summary", "catalyst_forced_none", "catalyst_acquisition_target", "catalyst_votes",
    "news_used", "news_dropped_roundup", "prior_day_volume_multiple",
    "exchange", "halt_status", "dq_reasons", "evidence", "tier", "watch_reason", "eligible",
    # M4: score, provisional levels and sizing per risk profile (Tier A and B only)
    "shortlist_rank", "score", "score_parts", "pm_high_used", "trigger", "stop", "stop_basis", "stop_pct", "risk_per_share",
    "target_1_5r", "levels_status",
    "shares_measure", "position_usd_measure", "risk_usd_measure", "size_note_measure",
    "shares_challenge", "position_usd_challenge", "risk_usd_challenge", "size_note_challenge",
    "warnings", "t212_list", "scan_file",
]


# --------------------------------------------------------------------- universe


def exchanges_of(assets: List[dict], symbols) -> Dict[str, str]:
    ex = {a["symbol"]: a.get("exchange", "") for a in assets}
    return {s: ex.get(s, "") for s in sorted(symbols)}


def common_stock_filter(assets: List[dict], cfg: Dict[str, Any]) -> Dict[str, str]:
    """Heuristic US-listed common stock filter -> {symbol: name}."""
    ex = set(cfg["universe"]["exchanges"])
    words = [w.lower() for w in cfg["universe"]["exclude_name_words"]]
    out = {}
    for a in assets:
        if a.get("exchange") not in ex or not a.get("tradable"):
            continue
        sym, name = a["symbol"], a.get("name") or ""
        if "." in sym or "/" in sym:
            continue
        low = name.lower()
        if any(w in low for w in words) and "common" not in low and "ordinary" not in low:
            continue
        out[sym] = name
    return dict(sorted(out.items()))


def prior_close_band(cfg: Dict[str, Any]) -> tuple:
    s = cfg["scan"]
    return s["prior_close_floor"], s["price_max"] / (1 + s["gap_min_pct"] / 100)


# --------------------------------------------------------------------- evaluate


def premarket_stats(bars: List[dict], start: datetime, cutoff: datetime) -> Optional[dict]:
    """Aggregate 1-min bars from `start` up to the cutoff. Bars that had not
    closed by the cutoff are ignored (no look-ahead), whatever the API sent."""
    use = [b for b in bars if parse_ts(b["t"]) >= start and bar_complete_before(b["t"], cutoff)]
    if not use:
        return None
    use.sort(key=lambda b: b["t"])
    return {
        "price": use[-1]["c"],
        "pm_high": max(b["h"] for b in use),
        # High of the 60 minutes ending at the cutoff (2026-11-16): shown next to the full-session high.
        "pm_high_last60": max(b["h"] for b in use if parse_ts(b["t"]) >= cutoff - timedelta(minutes=60)) if any(
            parse_ts(b["t"]) >= cutoff - timedelta(minutes=60) for b in use) else None,
        "pm_volume": sum(b["v"] for b in use),
        # math.fsum is correctly rounded on every Python version; plain sum() of
        # floats changed in 3.12 and broke byte-identical replays across versions.
        "pm_dollar_volume": round(math.fsum(b["v"] * b.get("vw", b["c"]) for b in use), 2),
        "pm_trades": sum(b.get("n", 0) for b in use),
        "pm_bars": len(use),
        "last_bar_et": parse_ts(use[-1]["t"]).astimezone(ET).strftime("%H:%M"),
    }


def scan_warnings(inp: Dict[str, Any], cfg: Dict[str, Any]) -> List[str]:
    w = []
    t = inp["t212"]
    day = date.fromisoformat(inp["day"])
    list_day = date.fromisoformat(t["as_of"])
    if list_day > day:
        w.append(f"historical run: T212 list is from {list_day} (later than scan day)")
    elif (day - list_day).days > cfg["t212"]["max_age_days"]:
        w.append(f"T212 list is {(day - list_day).days} days old")
    if t.get("refresh_error"):
        w.append(f"T212 refresh failed: {t['refresh_error']}")
    fetched = date.fromisoformat(inp["universe"]["fetched_at"][:10])
    if fetched > day:
        w.append(f"historical run: universe is Alpaca's asset list from {fetched} (no delisted names)")
    return w


def evaluate(inp: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Pure function of saved inputs. Returns candidates and a summary."""
    s = cfg["scan"]
    day = date.fromisoformat(inp["day"])
    start = at_et(day, cfg["schedule"]["premarket_start"])
    cutoff = datetime.fromisoformat(inp["data_cutoff_et"])
    t212 = t212mod.T212List(inp["t212"]["symbols"], date.fromisoformat(inp["t212"]["as_of"]), inp["t212"]["path"], inp["t212"]["sha256"])
    warns = scan_warnings(inp, cfg)
    lo, hi = prior_close_band(cfg)

    cands, checked, with_bars = [], 0, 0
    for sym, pc in sorted(inp["prior_close"].items()):
        if not (lo <= pc <= hi):
            continue
        checked += 1
        st = premarket_stats(inp["premarket_bars"].get(sym, []), start, cutoff)
        if not st:
            continue
        with_bars += 1
        gap = round(100 * (st["price"] / pc - 1), 2)
        if not (s["price_min"] <= st["price"] <= s["price_max"] and gap >= s["gap_min_pct"]):
            continue  # the candidate log starts at the basic price + gap filters
        cands.append(
            {
                "date": inp["day"],
                "as_of_et": inp["as_of_et"],
                "data_cutoff_et": inp["data_cutoff_et"],
                "symbol": sym,
                "name": inp["universe"]["symbols"].get(sym, ""),
                "prior_date": inp["prior_day"],
                "prior_close": pc,
                "gap_pct": gap,
                **st,
                "rule_price": R.PASS,
                "rule_gap": R.PASS,
                "rule_t212": R.PASS if t212.contains(sym) else R.FAIL,
                "t212_list": inp["t212"]["path"],
            }
        )
    for r in cands:
        apply_filters(r, inp, cfg, warns)
    from src import rank
    rank.apply(cands, inp, cfg)
    cands.sort(key=lambda r: (-r["pm_dollar_volume"], r["symbol"]))
    status = lambda col: {k: sum(1 for r in cands if r[col] == k) for k in (R.PASS, R.FAIL, R.UNKNOWN) if any(r[col] == k for r in cands)}
    return {
        "day": inp["day"],
        "summary": {
            "universe": len(inp["universe"]["symbols"]),
            "with_prior_close": len(inp["prior_close"]),
            "prior_close_band": [lo, round(hi, 4)],
            "checked_in_band": checked,
            "with_premarket_bars": with_bars,
            "candidates": len(cands),
            "rules": {c: status(c) for c in MUST_PASS + ["rule_float"] + DISQUALIFIERS},
            "eligible": sum(1 for r in cands if r["eligible"]),
            "tiers": {"A": sum(1 for r in cands if r["tier"] == "A"), "B": sum(1 for r in cands if r["tier"] == "B"),
                      "watch": sum(1 for r in cands if r["watch_reason"])},
            "warnings": warns,
        },
        "candidates": cands,
    }


# Tier B (pre-declared 2026-11-16, SPEC 4.4b): the Tier A rules without
# continuation and prior range. Do not change after seeing outcomes.
TIER_B_BASE = ["rule_price", "rule_gap", "rule_t212", "rule_pm_dollar_volume", "rule_pm_trades"]


def tier_b_ok(r: dict) -> bool:
    return all(r[c] == R.PASS for c in TIER_B_BASE) and all(r[c] != R.FAIL for c in DISQUALIFIERS)


def tier_a_ok(r: dict) -> bool:
    """Every must-pass rule except float passes, and nothing disqualifies."""
    return tier_b_ok(r) and all(r[c] == R.PASS for c in MUST_PASS)


# Watch (pre-declared 2026-11-16, SPEC 4.4c): never change after seeing outcomes.
def watch_reason(r: dict) -> str:
    """"no_catalyst" | "promo" | "other" for a Watch name, "" if not on Watch.

    Watch = on T212, passes price and gap, premarket dollar volume >= the
    minimum, in no tier. Excluded (not-shown list only): an offering
    disqualifier, or a reverse split whose verdict is pending (dq fail).
    A "possible" split is only a warning, so it does not exclude.
    """
    if r.get("tier"):
        return ""
    if not all(r.get(c) == R.PASS for c in ("rule_price", "rule_gap", "rule_t212", "rule_pm_dollar_volume")):
        return ""
    if r.get("dq_offering") == R.FAIL or r.get("dq_reverse_split") == R.FAIL:
        return ""
    if r.get("dq_promo_or_no_catalyst") == R.FAIL:
        return "promo" if "promo/pump" in (r.get("dq_reasons") or "") else "no_catalyst"
    return "other"


def passes_cheap(r: dict) -> bool:
    """Who gets SIP quotes (spread) and a Yahoo call (float): every Tier B
    name, so all rules run for Tier B too, not only Tier A survivors."""
    return tier_b_ok(r)


def apply_filters(r: dict, inp: Dict[str, Any], cfg: Dict[str, Any], scan_warns: List[str]) -> None:
    """Fill the M2 rule columns for one candidate row, in place."""
    f, wc, ec = cfg["filters"], cfg["warnings"], cfg["edgar"]
    sym = r["symbol"]
    day = date.fromisoformat(inp["day"])
    prior = date.fromisoformat(inp["prior_day"])
    warns: List[str] = []

    # 4.1, cheapest first: premarket liquidity from the bars already in hand
    r["rule_pm_dollar_volume"] = R.threshold(r["pm_dollar_volume"], f["min_pm_dollar_volume"])
    r["rule_pm_trades"] = R.threshold(r["pm_trades"], f["min_pm_trades"])

    # 4.1 history rules (Alpaca daily bars)
    daily = inp.get("history", {}).get(sym)
    if daily is None:
        r["rule_continuation"], r["continuation_detail"] = R.UNKNOWN, "history not fetched"
        r["rule_prior_range"], r["prior_range_pos_pct"] = R.UNKNOWN, None
    else:
        r["rule_continuation"], r["continuation_detail"] = R.continuation(daily, prior, f["continuation"])
        pbar = next((b for b in daily if parse_ts(b["t"]).astimezone(ET).date() == prior), None)
        r["rule_prior_range"], r["prior_range_pos_pct"] = R.prior_range(pbar, f["prior_range_top_pct"])
    if r["rule_continuation"] == R.UNKNOWN:
        warns.append(f"continuation unknown: {r['continuation_detail']}")

    # 4.2 / 4.3 from EDGAR
    # 4.3 halt at scan time (warning only; unknown is a warning, never silent)
    exch = inp["universe"].get("exchanges", {}).get(sym)
    r["exchange"] = exch or ""
    r["halt_status"] = halts.status(inp.get("halts"), sym, day, datetime.fromisoformat(inp["as_of_et"]),
                                    exch, cfg["halts"]["confirmed_markets"]) or "not halted"
    if r["halt_status"] != "not halted":
        warns.append(r["halt_status"])

    ed = inp.get("edgar", {}).get(sym)
    dq_reasons: List[str] = []
    evidence: List[dict] = []
    so = None
    if not ed or ed.get("cik") is None:
        r["dq_offering"] = r["dq_reverse_split"] = R.UNKNOWN
        warns.append("EDGAR: no CIK for this ticker, filings not checked" if ed else "EDGAR not fetched")
    else:
        fl = ed.get("filings", [])
        r["dq_offering"], dq, maybe, ev1 = R.offering(fl, day, ec["offering_lookback_days"])
        r["dq_reverse_split"], rs, rs_warn, ev2 = R.reverse_split(fl, day, ec["reverse_split_lookback_days"])
        evidence += ev1 + ev2
        dq_reasons += dq + rs
        warns += maybe + rs_warn
        warns += R.deficiency(fl, day, ec["deficiency_lookback_days"])
        am = R.amended_filings(fl, day, ec["deficiency_lookback_days"], ec.get("amended_min", 2))
        if am:
            warns.append(am)
        if ed.get("errors"):
            r["dq_offering"] = R.UNKNOWN if r["dq_offering"] == R.PASS else r["dq_offering"]
            warns += [f"EDGAR error: {e}" for e in ed["errors"]]
        if ed.get("docs_capped"):
            warns.append(f"EDGAR: {ed['docs_capped']} older filings not read (cap)")
        so = R.edgar_shares(ed.get("shares_points", []), day)
        if not so:
            warns.append("EDGAR shares outstanding missing")
        elif (day - date.fromisoformat(so["end"])).days > wc["shares_stale_days"]:
            warns.append(f"EDGAR shares outstanding stale (as of {so['end']})")
    r["edgar_shares_out"] = so["val"] if so else None
    r["edgar_shares_asof"] = so["end"] if so else None
    # 4.2 catalyst (M3): classifier output saved in the inputs; never re-called on replay.
    cat = inp.get("catalyst", {}).get(sym)
    surge = R.prior_day_volume_multiple(daily or [], prior, f["continuation"])
    r["prior_day_volume_multiple"] = surge
    r["dq_promo_or_no_catalyst"], why, cw = R.catalyst_rule(cat, surge, f["continuation"]["volume_multiple"])
    if why:
        dq_reasons.append(why)
    warns += cw
    out = (cat or {}).get("output") or {}
    r["catalyst_status"] = (cat or {}).get("status", "")
    r["catalyst_type"] = out.get("catalyst_type", "")
    r["catalyst_quality"] = out.get("quality")
    r["catalyst_summary"] = out.get("one_line_summary", "")
    r["catalyst_forced_none"] = (cat or {}).get("forced_none", False)
    v = (cat or {}).get("votes") or {}
    r["catalyst_votes"] = (f"{v.get('types', {}).get(out.get('catalyst_type'), 0)}/{v['valid_runs']} runs agree"
                           if v.get("valid_runs", 0) > 1 and out.get("catalyst_type") not in (None, "unclear") else
                           (f"runs disagree: {v.get('types')}" if out.get("catalyst_type") == "unclear" else ""))
    r["news_used"] = (cat or {}).get("items_used")
    r["news_dropped_roundup"] = (cat or {}).get("items_dropped_roundup")
    # Pre-declared 2026-11-16 (SPEC 4.3): a warning only, never a disqualifier.
    if out.get("catalyst_type") == "merger" and out.get("acquisition_target"):
        warns.append("merger target: price likely pinned to deal terms")
    r["catalyst_acquisition_target"] = out.get("acquisition_target")
    if out.get("dilution_language") and r.get("dq_offering") == R.PASS and not any(w.startswith(("possible offering", "resale registration")) for w in warns):
        warns.append("classifier: dilution language in news, no offering filing found")

    # Only names that survive everything cheaper get quotes and Yahoo.
    if passes_cheap(r):
        sp = R.spread_pct(inp.get("quotes", {}).get(sym, []), datetime.fromisoformat(inp["data_cutoff_et"]), wc["spread_max_quotes"])
        r["spread_pct"] = sp
        if sp is None:
            warns.append("spread unknown (no SIP quotes before cutoff)")
        elif sp > wc["spread_warn_pct"]:
            warns.append(f"spread {sp:.1f}%")
        y = inp.get("yahoo", {}).get(sym)
        r["rule_float"], r["float_shares"], r["float_source"], fw = R.float_rule(y, so, f)
        warns += fw
        if r["float_shares"] and r["float_shares"] > f["float_max"]:
            warns.append(f"above {f['float_max'] / 1e6:.0f}M float ({r['float_shares'] / 1e6:.1f}M, {r['float_source']})")
        if y and y.get("error"):
            warns.append(f"Yahoo error: {y['error']}")
        r["yahoo_shares_out"] = (y or {}).get("sharesOutstanding")
        mm = R.shares_mismatch(y, so, wc["shares_mismatch_pct"])
        if mm:
            warns.append(mm)
        if y and date.fromisoformat(y["fetched_at"][:10]) > day:
            warns.append("historical run: float is today's Yahoo value")
    else:
        r["rule_float"], r["float_shares"], r["float_source"] = R.NOT_CHECKED, None, ""
        r["spread_pct"] = r["yahoo_shares_out"] = None

    r["dq_reasons"] = "; ".join(dq_reasons)
    # Audit trail: every offering / reverse-split match with its sentence and URL.
    r["evidence"] = " || ".join(f"[{e['rule']}:{e['result']}] {e['filing']} | \"{e['sentence']}\" | {e['url']}" for e in evidence)
    r["eligible"] = tier_a_ok(r) and r["rule_float"] in (R.PASS, R.UNKNOWN)   # Tier A
    r["tier"] = "A" if r["eligible"] else ("B" if tier_b_ok(r) else "")
    r["watch_reason"] = watch_reason(r)
    r["warnings"] = "; ".join(scan_warns + warns)


# --------------------------------------------------------------------- gather


def trading_days(alp, day: date) -> tuple:
    """(is_trading_day, prior_trading_day)."""
    cal = alp.calendar(day - timedelta(days=12), day)
    days = [date.fromisoformat(c["date"]) for c in cal]
    prior = [d for d in days if d < day]
    if not prior:
        raise RuntimeError(f"No prior trading day found before {day}")
    return day in days, prior[-1]


def gather_inputs(alp, edgar, cfg: Dict[str, Any], day: date, as_of: datetime, t212: "t212mod.T212List", now: datetime, llm=None) -> Dict[str, Any]:
    cutoff = data_cutoff(as_of, cfg["schedule"]["sip_delay_minutes"])
    is_td, prior = trading_days(alp, day)
    if not is_td:
        raise RuntimeError(f"{day} is not a trading day")
    assets = alp.assets()
    universe = common_stock_filter(assets, cfg)
    daily = alp.bars(list(universe), "1Day", at_et(prior, "00:00"), at_et(prior, "23:59"), feed="sip", batch=1000)
    prior_close = {}
    for sym, bs in daily.items():
        for b in bs:
            if parse_ts(b["t"]).astimezone(ET).date() == prior:
                prior_close[sym] = b["c"]
    lo, hi = prior_close_band(cfg)
    want = sorted(s for s, c in prior_close.items() if lo <= c <= hi)
    start = at_et(day, cfg["schedule"]["premarket_start"])
    pm = alp.bars(want, "1Min", start, cutoff, feed="sip") if want else {}
    # The API's end is inclusive of the bar *starting* at the cutoff, which
    # closes after it. Drop such bars so saved inputs never pass the cutoff.
    pm = {s: [b for b in bs if bar_complete_before(b["t"], cutoff)] for s, bs in pm.items()}
    pm = {s: bs for s, bs in pm.items() if bs}
    inp = {
        "schema": SCHEMA,
        "day": day.isoformat(),
        "as_of_et": as_of.astimezone(ET).isoformat(),
        "data_cutoff_et": cutoff.astimezone(ET).isoformat(),
        "prior_day": prior.isoformat(),
        "universe": {"source": "alpaca /v2/assets, common-stock heuristic", "fetched_at": now.astimezone(ET).isoformat(), "symbols": universe,
                     "exchanges": exchanges_of(assets, universe)},
        "prior_close": dict(sorted(prior_close.items())),
        "premarket_bars": {k: pm[k] for k in sorted(pm)},
        "t212": {
            "path": t212.path,
            "as_of": t212.as_of.isoformat(),
            "sha256": t212.sha256,
            "refresh_error": t212.refresh_error,
            "symbols": t212.symbols,
        },
        "history": {},
        "edgar": {},
        "quotes": {},
        "yahoo": {},
        "news": {},
        "catalyst": {},
    }
    return gather_filter_inputs(alp, edgar, cfg, inp, as_of, cutoff, now, llm)


def gather_filter_inputs(alp, edgar, cfg: Dict[str, Any], inp: Dict[str, Any], as_of: datetime, cutoff: datetime, now: datetime, llm=None) -> Dict[str, Any]:
    """M2 inputs, fetched in cost order (SPEC 4.1-4.3)."""
    from src.data import edgar as edgarmod
    from src.data import yahoo as yahoomod

    day, prior = date.fromisoformat(inp["day"]), date.fromisoformat(inp["prior_day"])
    # The halts feed keeps no history, so its contents are saved at every scan.
    inp["halts"] = halts.fetch(now)
    halts.log_markets(inp["halts"], ROOT / "data" / "halts_markets.csv")
    syms = [r["symbol"] for r in evaluate(inp, cfg)["candidates"]]
    if not syms:
        return inp
    # Alpaca daily history up to and including the prior session only.
    days = cfg["filters"]["continuation"]["history_calendar_days"]
    hist = alp.bars(syms, "1Day", at_et(prior - timedelta(days=days), "00:00"), at_et(prior, "23:59"), feed="sip")
    inp["history"] = {s: hist.get(s, []) for s in syms}
    # EDGAR is official and allows 10 req/s; checked for every candidate.
    inp["edgar"] = edgarmod.gather(edgar, syms, day, as_of, cfg["edgar"], ROOT / cfg["paths"]["cache"], now.date())
    # Classifier: one call per candidate company (about $0.0002 each on Haiku).
    from src import catalyst as catmod
    cands = [r for r in evaluate(inp, cfg)["candidates"]]
    inp["news"], inp["catalyst"] = catmod.gather(alp, llm, cands, inp["edgar"], as_of, cfg["catalyst"])
    # Quotes and Yahoo only for names that pass every cheaper rule.
    survivors = [r["symbol"] for r in evaluate(inp, cfg)["candidates"] if passes_cheap(r)]
    if survivors:
        w = cfg["warnings"]["spread_window_minutes"]
        q = alp.quotes(survivors, cutoff - timedelta(minutes=w), cutoff, feed="sip")
        keep = cfg["warnings"]["spread_max_quotes"]
        inp["quotes"] = {
            s: [{"t": x["t"], "bp": x["bp"], "ap": x["ap"]} for x in sorted(q.get(s, []), key=lambda x: x["t"]) if parse_ts(x["t"]) < cutoff][-keep:]
            for s in survivors
        }
        inp["yahoo"] = yahoomod.gather(survivors, now)
    return inp


def trim_inputs(inp: Dict[str, Any], out: Dict[str, Any]) -> Dict[str, Any]:
    """Keep full premarket bars only for candidates; for every other symbol keep
    just its last bar before the cutoff, which is all evaluate() needs to
    reproduce that it failed price or gap. Keeps scan files small."""
    keep = {r["symbol"] for r in out["candidates"]}
    cutoff = datetime.fromisoformat(inp["data_cutoff_et"])
    bars = {}
    for sym, bs in inp["premarket_bars"].items():
        if sym in keep:
            bars[sym] = bs
        else:
            done = sorted((b for b in bs if bar_complete_before(b["t"], cutoff)), key=lambda b: b["t"])
            if done:
                bars[sym] = done[-1:]
    t = dict(inp, premarket_bars=bars)
    # The T212 symbols live in the committed daily file; keep only the reference.
    t["t212"] = {k: v for k, v in inp["t212"].items() if k != "symbols"}
    return t


# --------------------------------------------------------------------- save


def scan_path(cfg: Dict[str, Any], day: date, as_of: datetime) -> Path:
    folder = ROOT / cfg["paths"]["scans"]
    hhmm = as_of.astimezone(ET).strftime("%H%M")
    name = day.isoformat() if hhmm == cfg["schedule"]["scan_time"].replace(":", "") else f"{day.isoformat()}_{hhmm}"
    return folder / f"{name}.json"


def save(cfg: Dict[str, Any], inp: Dict[str, Any], out: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rel = str(path.relative_to(ROOT))
    for r in out["candidates"]:
        r["scan_file"] = rel
    path.write_text(json.dumps({"inputs": trim_inputs(inp, out), "outputs": out}, indent=1, sort_keys=True))
    upsert_candidates(ROOT / cfg["paths"]["candidates"], out["candidates"], inp["day"], inp["as_of_et"])


def upsert_candidates(path: Path, rows: List[dict], day: str, as_of: str) -> None:
    """Replace this (day, as_of) in candidates.csv so re-running a day is idempotent."""
    old = []
    if path.exists():
        with path.open(newline="") as f:
            old = [r for r in csv.DictReader(f) if not (r["date"] == day and r["as_of_et"] == as_of)]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in sorted(old + rows, key=lambda r: (r["date"], r["as_of_et"], r["symbol"])):
            w.writerow(r)


# --------------------------------------------------------------------- replay


def load_scan_inputs(path: Path) -> tuple:
    j = json.loads(path.read_text())
    inp = j["inputs"]
    if inp.get("schema") != SCHEMA:
        raise RuntimeError(f"{path.name} is schema {inp.get('schema')}, this code is schema {SCHEMA}: re-run the scan for that day")
    if "symbols" not in inp["t212"]:
        lst = t212mod.load_file(ROOT / inp["t212"]["path"], ROOT)
        if lst.sha256 != inp["t212"]["sha256"]:
            raise RuntimeError(f"T212 list {inp['t212']['path']} changed since the scan (hash mismatch)")
        inp["t212"]["symbols"] = lst.symbols
    return inp, j["outputs"]


def _load_for_refresh(path: Path) -> tuple:
    load_env()
    path = path.resolve()
    j = json.loads(path.read_text())
    inp = j["inputs"]
    if inp.get("schema") not in (SCHEMA - 1, SCHEMA):
        raise RuntimeError(f"{path.name} is schema {inp.get('schema')}; refresh supports {SCHEMA - 1}-{SCHEMA}")
    if "symbols" not in inp["t212"]:
        inp["t212"]["symbols"] = t212mod.load_file(ROOT / inp["t212"]["path"], ROOT).symbols
    inp["schema"] = SCHEMA
    return path, inp


def _fill_new_survivors(inp: Dict[str, Any], cfg: Dict[str, Any]) -> int:
    """SIP quotes and Yahoo for names that newly pass every cheaper rule."""
    from src.data import yahoo as yahoomod
    from src.data.alpaca import Alpaca

    new = [r["symbol"] for r in evaluate(inp, cfg)["candidates"] if passes_cheap(r) and r["symbol"] not in inp.get("yahoo", {})]
    if new:
        cutoff, now = datetime.fromisoformat(inp["data_cutoff_et"]), datetime.now(tz=ET)
        w, keep = cfg["warnings"]["spread_window_minutes"], cfg["warnings"]["spread_max_quotes"]
        q = Alpaca().quotes(new, cutoff - timedelta(minutes=w), cutoff, feed="sip")
        for s_ in new:
            inp["quotes"][s_] = [{"t": x["t"], "bp": x["bp"], "ap": x["ap"]} for x in sorted(q.get(s_, []), key=lambda x: x["t"]) if parse_ts(x["t"]) < cutoff][-keep:]
        inp["yahoo"].update(yahoomod.gather(new, now))
    return len(new)


def reclassify(path: Path, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Re-run the classifier on a saved scan's own news and filings (as saved at
    scan time, so no look-ahead). Only the model is called again."""
    import anthropic
    from src import catalyst as catmod

    path, inp = _load_for_refresh(path)
    llm = anthropic.Anthropic()
    as_of = datetime.fromisoformat(inp["as_of_et"])
    since = (as_of.date() - timedelta(days=5)).isoformat()
    for r in evaluate(inp, cfg)["candidates"]:
        sym = r["symbol"]
        fl = [f for f in (inp["edgar"].get(sym) or {}).get("filings", []) if f["filed"] >= since]
        inp["catalyst"][sym] = catmod.classify(llm, sym, r["name"], inp["news"].get(sym, []), fl, cfg["catalyst"])
    n_new = _fill_new_survivors(inp, cfg)
    out = evaluate(inp, cfg)
    save(cfg, inp, out, path)
    print(f"{path.name}: reclassified {len(inp['catalyst'])} names, {n_new} new survivors, {out['summary']['eligible']} eligible")
    return out


def refresh_edgar(path: Path, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Re-fetch only the EDGAR inputs of a saved scan, as of its original scan
    time (no look-ahead), keeping bars, news and classifier outputs as saved.
    Names that newly survive get SIP quotes and Yahoo, as in a normal scan."""
    from src.data import edgar as edgarmod
    from src.data import yahoo as yahoomod
    from src.data.alpaca import Alpaca

    load_env()
    path = path.resolve()
    j = json.loads(path.read_text())
    inp = j["inputs"]
    if inp.get("schema") not in (SCHEMA - 1, SCHEMA):
        raise RuntimeError(f"{path.name} is schema {inp.get('schema')}; refresh supports {SCHEMA - 1}-{SCHEMA}")
    if "symbols" not in inp["t212"]:
        inp["t212"]["symbols"] = t212mod.load_file(ROOT / inp["t212"]["path"], ROOT).symbols
    inp["schema"] = SCHEMA
    day, as_of = date.fromisoformat(inp["day"]), datetime.fromisoformat(inp["as_of_et"])
    cutoff, now = datetime.fromisoformat(inp["data_cutoff_et"]), datetime.now(tz=ET)
    syms = [r["symbol"] for r in evaluate(inp, cfg)["candidates"]]
    ed = edgarmod.Edgar()
    inp["edgar"] = edgarmod.gather(ed, syms, day, as_of, cfg["edgar"], ROOT / cfg["paths"]["cache"], now.date())
    new = [r["symbol"] for r in evaluate(inp, cfg)["candidates"] if passes_cheap(r) and r["symbol"] not in inp.get("yahoo", {})]
    if new:
        alp = Alpaca()
        w, keep = cfg["warnings"]["spread_window_minutes"], cfg["warnings"]["spread_max_quotes"]
        q = alp.quotes(new, cutoff - timedelta(minutes=w), cutoff, feed="sip")
        for s_ in new:
            inp["quotes"][s_] = [{"t": x["t"], "bp": x["bp"], "ap": x["ap"]} for x in sorted(q.get(s_, []), key=lambda x: x["t"]) if parse_ts(x["t"]) < cutoff][-keep:]
        inp["yahoo"].update(yahoomod.gather(new, now))
    out = evaluate(inp, cfg)
    save(cfg, inp, out, path)
    print(f"{path.name}: EDGAR refreshed ({ed.calls} calls), {len(new)} new survivors, {out['summary']['eligible']} eligible")
    return out


def rescore(path: Path, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Recompute and save a scan's outputs from its saved inputs. No network."""
    path = path.resolve()
    j = json.loads(path.read_text())
    inp, _ = load_scan_inputs(path)
    out = evaluate(inp, cfg)
    rel = str(path.relative_to(ROOT))
    for r in out["candidates"]:
        r["scan_file"] = rel
    j["outputs"] = out
    path.write_text(json.dumps(j, indent=1, sort_keys=True))
    upsert_candidates(ROOT / cfg["paths"]["candidates"], out["candidates"], inp["day"], inp["as_of_et"])
    return out


def replay(path: Path, cfg: Dict[str, Any]) -> bool:
    inp, saved = load_scan_inputs(path)
    got = evaluate(inp, cfg)
    strip = lambda o: [{k: v for k, v in r.items() if k != "scan_file"} for r in o["candidates"]]
    same = strip(got) == strip(saved) and got["summary"] == saved["summary"]
    print(f"{path.name}: {'identical' if same else 'DIFFERENT'} "
          f"({got['summary']['candidates']} candidates, {got['summary']['eligible']} eligible)")
    return same


# --------------------------------------------------------------------- CLI


def run(day: Optional[date], as_of_hhmm: Optional[str], refresh_t212: bool = True) -> Dict[str, Any]:
    from src.data.alpaca import Alpaca
    import os

    load_env()
    cfg = load_config()
    now = datetime.now(tz=ET)
    if day is None:
        day, as_of = now.date(), now
    else:
        as_of = at_et(day, as_of_hhmm or cfg["schedule"]["scan_time"])
        if as_of > now:
            raise SystemExit(f"as-of {as_of} is in the future")
    base = os.environ.get(cfg["t212"]["base_url_env"]) or cfg["t212"]["default_base_url"]
    t212 = t212mod.get_list(now.date(), ROOT / cfg["paths"]["t212"], ROOT, base, refresh=refresh_t212)
    from src.data.edgar import Edgar

    import anthropic

    alp, ed, llm = Alpaca(), Edgar(), anthropic.Anthropic()
    inp = gather_inputs(alp, ed, cfg, day, as_of, t212, now, llm)
    out = evaluate(inp, cfg)
    path = scan_path(cfg, day, as_of)
    save(cfg, inp, out, path)
    print(json.dumps(out["summary"], indent=1))
    short = {R.PASS: "+", R.FAIL: "x", R.UNKNOWN: "?", R.NOT_CHECKED: "."}
    cols = MUST_PASS[2:] + ["rule_float"] + DISQUALIFIERS
    print("  rules: " + " ".join(c.replace("rule_", "").replace("dq_", "dq:") for c in cols) + "   (+ pass, x fail, ? unknown, . not checked)")
    for r in out["candidates"]:
        flags = "".join(short[r[c]] for c in cols)
        print(f"  {r['symbol']:6} {r['price']:>7} gap {r['gap_pct']:>6}%  pm$ {r['pm_dollar_volume']:>12,.0f}  {flags}  "
              f"{'ELIGIBLE' if r['eligible'] else ''}  {r['dq_reasons'][:70]}")
    print(f"saved {path.relative_to(ROOT)} ({alp.calls} Alpaca, {ed.calls} EDGAR calls)")
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", type=date.fromisoformat)
    ap.add_argument("--as-of", help="HH:MM ET, default the configured scan time")
    ap.add_argument("--replay", type=Path)
    ap.add_argument("--rescore", type=Path, help="recompute outputs from a saved scan's inputs (no network)")
    ap.add_argument("--refresh-edgar", type=Path, help="re-fetch a saved scan's EDGAR inputs as of its scan time")
    ap.add_argument("--reclassify", type=Path, help="re-run the classifier on a saved scan's own news")
    ap.add_argument("--no-t212-refresh", action="store_true")
    a = ap.parse_args(argv)
    if a.replay:
        return 0 if replay(a.replay, load_config()) else 1
    if a.reclassify:
        reclassify(a.reclassify, load_config())
        return 0
    if a.refresh_edgar:
        refresh_edgar(a.refresh_edgar, load_config())
        return 0
    if a.rescore:
        out = rescore(a.rescore, load_config())
        print(f"{a.rescore.name}: rescored ({out['summary']['candidates']} candidates, {out['summary']['eligible']} eligible)")
        return 0
    run(a.date, a.as_of, refresh_t212=not a.no_t212_refresh)
    return 0


if __name__ == "__main__":
    sys.exit(main())
