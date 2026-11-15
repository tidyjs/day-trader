"""M0 test 6 (the gate): what fraction of Alpaca-detected $1-$2 gappers over the
last week can actually be traded on Trading 212?

Step 1 (Alpaca only) finds gappers for the last N trading days:
  - universe: Alpaca active, tradable, US-listed common stock (heuristic)
  - prior close: SIP daily bar of the previous session
  - premarket price: close of the last SIP 1-min bar before 09:15 ET
  - gapper: 1.00 <= price <= 2.00 and gap >= +10%
  - also records premarket SIP dollar volume and trade count, and marks the
    subset with >= $100k dollar volume (spec 4.1)
  Writes docs/m0_raw/gappers.json (t2, t3, t4, t5, t7 reuse it).

Step 2 compares with the T212 list, from either:
  - data/t212_instruments.json  (raw output of T212 /equity/metadata/instruments)
  - data/t212_instruments.csv   (any CSV with a ticker/symbol column)
  - the T212 API, if T212_API_KEY (and optionally T212_API_SECRET) is set.
    Read-only metadata endpoint; nothing else is called.

Usage:
  python m0/t6_t212_overlap.py            # both steps
  python m0/t6_t212_overlap.py --days 5 --skip-scan   # reuse gappers.json
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
from collections import defaultdict
from pathlib import Path

import requests

from common import (
    ROOT,
    Alpaca,
    common_stock_universe,
    et,
    load_raw,
    md_table,
    parse_ts,
    recent_trading_days,
    save_raw,
)

MIN_GAP = 0.10
MIN_DVOL = 100_000


def find_gappers(alp: Alpaca, ndays: int):
    assets = common_stock_universe(alp.assets())
    syms = sorted(a["symbol"] for a in assets)
    names = {a["symbol"]: a.get("name") for a in assets}
    days = recent_trading_days(alp, ndays + 1)
    scan_days, first = days[1:], days[0]
    daily = alp.bars(syms, "1Day", et(first, 0), et(days[-1], 23, 59), feed="sip", batch=1000)
    closes = defaultdict(dict)
    for s, bs in daily.items():
        for b in bs:
            closes[s][parse_ts(b["t"]).astimezone(et(first, 0).tzinfo).date()] = b["c"]

    gappers, per_day = [], {}
    for i, d in enumerate(scan_days):
        prev = days[i]  # days[i] is the session before scan_days[i]
        # A $1-$2 price after a >=10% gap means prior close in [~0.40, 1.82].
        # Use a wide band; the real check is on the 09:15 price.
        cands = [s for s in syms if 0.4 <= closes[s].get(prev, 0) <= 1.82]
        pm = alp.bars(cands, "1Min", et(d, 4), et(d, 9, 15), feed="sip")
        n = 0
        for s, bs in pm.items():
            if not bs:
                continue
            pc = closes[s][prev]
            px = bs[-1]["c"]
            gap = px / pc - 1
            if not (1.0 <= px <= 2.0 and gap >= MIN_GAP):
                continue
            dvol = sum(b["v"] * b.get("vw", b["c"]) for b in bs)
            n += 1
            gappers.append(
                {
                    "date": d.isoformat(),
                    "symbol": s,
                    "name": names.get(s),
                    "prev_close": pc,
                    "px_0915": px,
                    "gap_pct": round(100 * gap, 1),
                    "pm_dollar_vol": round(dvol),
                    "pm_trades": sum(b.get("n", 0) for b in bs),
                    "pm_bars": len(bs),
                    "passes_dvol_100k": dvol >= MIN_DVOL,
                }
            )
        per_day[d.isoformat()] = {"candidates_checked": len(cands), "gappers": n}
    out = {
        "days": [d.isoformat() for d in scan_days],
        "universe_size": len(syms),
        "per_day": per_day,
        "rules": {"price": "1.00-2.00 at 09:15 ET (last SIP 1-min close)", "gap": ">= +10% vs prior SIP daily close"},
        "gappers": gappers,
    }
    save_raw("gappers", out)
    return out


def norm(t: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", t.upper())


def load_t212():
    data = ROOT / "data"
    j, c = data / "t212_instruments.json", data / "t212_instruments.csv"
    if j.exists():
        return parse_t212_json(json.loads(j.read_text())), str(j.relative_to(ROOT))
    if c.exists():
        with c.open(newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        col = next((k for k in rows[0] if k.strip().lower() in ("ticker", "symbol", "instrument", "shortname")), None)
        if not col:
            raise SystemExit(f"No ticker/symbol column in {c}: {list(rows[0])}")
        tick = set()
        for r in rows:
            v = (r[col] or "").strip()
            if v.upper().endswith("_US_EQ"):
                v = v[:-6]
            if v:
                tick.add(norm(v))
        return tick, str(c.relative_to(ROOT))
    key = os.environ.get("T212_API_KEY")
    if key:
        base = os.environ.get("T212_BASE_URL", "https://demo.trading212.com")
        url = f"{base}/api/v0/equity/metadata/instruments"
        sec = os.environ.get("T212_API_SECRET")
        r = requests.get(url, auth=(key, sec) if sec else None, headers=None if sec else {"Authorization": key}, timeout=60)
        r.raise_for_status()
        raw = r.json()
        data.mkdir(exist_ok=True)
        j.write_text(json.dumps(raw))
        return parse_t212_json(raw), "T212 API (saved to data/t212_instruments.json)"
    return None, None


def parse_t212_json(raw):
    """Match on shortName, the current exchange symbol. T212's internal
    `ticker` keeps the old symbol after a rename (e.g. CRMN is SKBL_US_EQ)."""
    out = set()
    for x in raw:
        t = x.get("ticker", "")
        if t.endswith("_US_EQ") and not t.endswith("WAR_US_EQ") and x.get("type", "STOCK") == "STOCK" and x.get("currencyCode", "USD") == "USD":
            out.add(norm(x.get("shortName") or t[:-6]))
    return out


def main(ndays: int, skip_scan: bool):
    g = load_raw("gappers") if skip_scan else None
    if not g:
        g = find_gappers(Alpaca(), ndays)
    t212, src = load_t212()
    gs = g["gappers"]
    print({"days": g["days"], "per_day": g["per_day"], "gapper_rows": len(gs)})
    if t212 is None:
        print("No T212 list yet. Put it at data/t212_instruments.csv or .json, or set T212_API_KEY.")
        return
    for x in gs:
        x["on_t212"] = norm(x["symbol"]) in t212

    def rate(rows):
        u = {r["symbol"] for r in rows}
        on = {r["symbol"] for r in rows if r["on_t212"]}
        return {
            "rows": len(rows),
            "rows_on_t212": sum(r["on_t212"] for r in rows),
            "row_pct": round(100 * sum(r["on_t212"] for r in rows) / max(1, len(rows)), 1),
            "unique_symbols": len(u),
            "unique_on_t212": len(on),
            "unique_pct": round(100 * len(on) / max(1, len(u)), 1),
        }

    liquid = [x for x in gs if x["passes_dvol_100k"]]
    by_day = {d: rate([x for x in liquid if x["date"] == d]) for d in g["days"]}
    summary = {
        "t212_source": src,
        "t212_us_tickers": len(t212),
        "all_gappers": rate(gs),
        "gappers_with_pm_dvol_100k": rate(liquid),
        "per_day_dvol_100k": by_day,
        "avg_t212_tradable_liquid_gappers_per_day": round(sum(v["rows_on_t212"] for v in by_day.values()) / max(1, len(by_day)), 2),
    }
    save_raw("t6_t212_overlap", {"summary": summary, "gappers": gs})
    print(json.dumps(summary, indent=2))
    print(md_table(sorted(liquid, key=lambda r: (r["date"], -r["gap_pct"])),
                   ["date", "symbol", "px_0915", "gap_pct", "pm_dollar_vol", "pm_trades", "on_t212"]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=5)
    ap.add_argument("--skip-scan", action="store_true")
    a = ap.parse_args()
    main(a.days, a.skip_scan)
