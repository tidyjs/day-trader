"""M1 scanner: universe, prior close, gap %, T212 filter, candidate log.

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
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import ROOT, load_config, load_env
from src.data import t212 as t212mod
from src.timeutil import ET, at_et, bar_complete_before, data_cutoff, parse_ts

SCHEMA = 1

CSV_COLUMNS = [
    "date", "as_of_et", "data_cutoff_et", "symbol", "name",
    "prior_date", "prior_close", "price", "gap_pct",
    "pm_high", "pm_volume", "pm_dollar_volume", "pm_trades", "pm_bars", "last_bar_et",
    "rule_price", "rule_gap", "rule_t212",
    "passes_m1", "warnings", "t212_list", "scan_file",
]


# --------------------------------------------------------------------- universe


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
        "pm_volume": sum(b["v"] for b in use),
        "pm_dollar_volume": round(sum(b["v"] * b.get("vw", b["c"]) for b in use), 2),
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
        rule_price = s["price_min"] <= st["price"] <= s["price_max"]
        rule_gap = gap >= s["gap_min_pct"]
        if not (rule_price and rule_gap):
            continue  # the candidate log starts at the basic price + gap filters
        rule_t212 = t212.contains(sym)
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
                "rule_price": rule_price,
                "rule_gap": rule_gap,
                "rule_t212": rule_t212,
                "passes_m1": rule_price and rule_gap and rule_t212,
                "warnings": "; ".join(warns),
                "t212_list": inp["t212"]["path"],
            }
        )
    cands.sort(key=lambda r: (-r["pm_dollar_volume"], r["symbol"]))
    return {
        "summary": {
            "universe": len(inp["universe"]["symbols"]),
            "with_prior_close": len(inp["prior_close"]),
            "prior_close_band": [lo, round(hi, 4)],
            "checked_in_band": checked,
            "with_premarket_bars": with_bars,
            "candidates": len(cands),
            "passes_m1": sum(r["passes_m1"] for r in cands),
            "warnings": warns,
        },
        "candidates": cands,
    }


# --------------------------------------------------------------------- gather


def trading_days(alp, day: date) -> tuple:
    """(is_trading_day, prior_trading_day)."""
    cal = alp.calendar(day - timedelta(days=12), day)
    days = [date.fromisoformat(c["date"]) for c in cal]
    prior = [d for d in days if d < day]
    if not prior:
        raise RuntimeError(f"No prior trading day found before {day}")
    return day in days, prior[-1]


def gather_inputs(alp, cfg: Dict[str, Any], day: date, as_of: datetime, t212: "t212mod.T212List", now: datetime) -> Dict[str, Any]:
    cutoff = data_cutoff(as_of, cfg["schedule"]["sip_delay_minutes"])
    is_td, prior = trading_days(alp, day)
    if not is_td:
        raise RuntimeError(f"{day} is not a trading day")
    universe = common_stock_filter(alp.assets(), cfg)
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
    return {
        "schema": SCHEMA,
        "day": day.isoformat(),
        "as_of_et": as_of.astimezone(ET).isoformat(),
        "data_cutoff_et": cutoff.astimezone(ET).isoformat(),
        "prior_day": prior.isoformat(),
        "universe": {"source": "alpaca /v2/assets, common-stock heuristic", "fetched_at": now.astimezone(ET).isoformat(), "symbols": universe},
        "prior_close": dict(sorted(prior_close.items())),
        "premarket_bars": {k: pm[k] for k in sorted(pm)},
        "t212": {
            "path": t212.path,
            "as_of": t212.as_of.isoformat(),
            "sha256": t212.sha256,
            "refresh_error": t212.refresh_error,
            "symbols": t212.symbols,
        },
    }


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
    if "symbols" not in inp["t212"]:
        lst = t212mod.load_file(ROOT / inp["t212"]["path"], ROOT)
        if lst.sha256 != inp["t212"]["sha256"]:
            raise RuntimeError(f"T212 list {inp['t212']['path']} changed since the scan (hash mismatch)")
        inp["t212"]["symbols"] = lst.symbols
    return inp, j["outputs"]


def replay(path: Path, cfg: Dict[str, Any]) -> bool:
    inp, saved = load_scan_inputs(path)
    got = evaluate(inp, cfg)
    strip = lambda o: [{k: v for k, v in r.items() if k != "scan_file"} for r in o["candidates"]]
    same = strip(got) == strip(saved) and got["summary"] == saved["summary"]
    print(f"{path.name}: {'identical' if same else 'DIFFERENT'} "
          f"({got['summary']['candidates']} candidates, {got['summary']['passes_m1']} pass M1)")
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
    alp = Alpaca()
    inp = gather_inputs(alp, cfg, day, as_of, t212, now)
    out = evaluate(inp, cfg)
    path = scan_path(cfg, day, as_of)
    save(cfg, inp, out, path)
    print(json.dumps(out["summary"], indent=1))
    for r in out["candidates"]:
        print(f"  {r['symbol']:6} {r['price']:>7} gap {r['gap_pct']:>6}%  pm$ {r['pm_dollar_volume']:>12,.0f}  "
              f"trades {r['pm_trades']:>6}  T212 {'yes' if r['rule_t212'] else 'no '}")
    print(f"saved {path.relative_to(ROOT)} ({alp.calls} Alpaca calls)")
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", type=date.fromisoformat)
    ap.add_argument("--as-of", help="HH:MM ET, default the configured scan time")
    ap.add_argument("--replay", type=Path)
    ap.add_argument("--no-t212-refresh", action="store_true")
    a = ap.parse_args(argv)
    if a.replay:
        return 0 if replay(a.replay, load_config()) else 1
    run(a.date, a.as_of, refresh_t212=not a.no_t212_refresh)
    return 0


if __name__ == "__main__":
    sys.exit(main())
