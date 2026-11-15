"""M0 test 2: delayed SIP bars on free keys.

Checks:
  a) feed=sip 1-min bars for a past trading day from 04:00 ET are returned
     (premarket coverage: first bar time, bars per hour).
  b) end = now  -> expected to be refused on the free plan (recent SIP).
  c) end = now - 16 min -> expected to succeed (delayed SIP allowed).
  d) side-by-side IEX vs SIP premarket share volume for the same names.

Symbols: from docs/m0_raw/gappers.json if t6 has run, else the day's $0.80-$2.40
names with the most premarket SIP volume (found here).

Usage: python m0/t2_sip_bars.py [--day YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, timedelta

from common import (
    Alpaca,
    AlpacaError,
    common_stock_universe,
    et,
    load_raw,
    md_table,
    now_et,
    parse_ts,
    recent_trading_days,
    save_raw,
)
from t1_iex_snapshots import sub2_by_prev_close


def try_bars(alp, syms, start, end, feed):
    try:
        b = alp.bars(syms, "1Min", start, end, feed=feed)
        return {"ok": True, "bars": sum(len(v) for v in b.values())}
    except AlpacaError as e:
        return {"ok": False, "status": e.status, "body": e.body[:300]}


def main(day: date):
    alp = Alpaca()
    g = load_raw("gappers")
    if g and g.get("gappers"):
        syms = sorted({x["symbol"] for x in g["gappers"]})[:30]
        source = "t6 gappers"
    else:
        uni = [a["symbol"] for a in common_stock_universe(alp.assets())]
        prevs, _ = sub2_by_prev_close(alp, uni, day)
        sip = alp.bars(sorted(prevs), "1Min", et(day, 4), et(day, 9, 30), feed="sip")
        vol = {s: sum(b["v"] for b in bs) for s, bs in sip.items()}
        syms = [s for s, _ in sorted(vol.items(), key=lambda kv: -kv[1])[:30]]
        source = "top premarket SIP volume, $0.80-$2.40 prior close"

    sip = alp.bars(syms, "1Min", et(day, 4), et(day, 9, 30), feed="sip")
    iex = alp.bars(syms, "1Min", et(day, 4), et(day, 9, 30), feed="iex")
    rows, hours = [], Counter()
    tz = et(day, 4).tzinfo
    for s in syms:
        sb, ib = sip.get(s, []), iex.get(s, [])
        for b in sb:
            hours[parse_ts(b["t"]).astimezone(tz).strftime("%H:00")] += 1
        rows.append(
            {
                "symbol": s,
                "sip_first_et": parse_ts(sb[0]["t"]).astimezone(tz).strftime("%H:%M") if sb else None,
                "sip_bars": len(sb),
                "sip_shares": sum(b["v"] for b in sb),
                "sip_dollar_vol": round(sum(b["v"] * b.get("vw", b["c"]) for b in sb)),
                "iex_bars": len(ib),
                "iex_shares": sum(b["v"] for b in ib),
                "iex_share_of_sip_pct": round(100 * sum(b["v"] for b in ib) / max(1, sum(b["v"] for b in sb)), 1),
            }
        )

    n = now_et()
    probe = syms[:3] or ["AAPL"]
    recent_now = try_bars(alp, probe, n - timedelta(hours=2), n, "sip")
    recent_16 = try_bars(alp, probe, n - timedelta(hours=2), n - timedelta(minutes=16), "sip")
    summary = {
        "day": day.isoformat(),
        "symbols_source": source,
        "symbols": len(syms),
        "symbols_with_sip_bar_before_0500": sum(1 for r in rows if r["sip_first_et"] and r["sip_first_et"] < "05:00"),
        "sip_bars_by_hour_et": dict(sorted(hours.items())),
        "median_iex_share_of_sip_pct": sorted(r["iex_share_of_sip_pct"] for r in rows)[len(rows) // 2] if rows else None,
        "recent_sip_end_now": recent_now,
        "recent_sip_end_now_minus_16min": recent_16,
        "rate_limit_headers": alp.last_headers,
    }
    save_raw(f"t2_sip_{day.isoformat()}", {"summary": summary, "rows": rows})
    print(summary)
    print(md_table(rows, list(rows[0].keys())) if rows else "no rows")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", type=date.fromisoformat)
    a = ap.parse_args()
    main(a.day or recent_trading_days(Alpaca(), 1)[0])
