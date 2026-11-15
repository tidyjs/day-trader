"""M0 test 1: are Alpaca IEX snapshots for sub-$2 names real premarket prints
or a stale prior close?

Two modes:
  live        (default) take a snapshot now. Run at ~04:00, ~08:00 and ~09:15 ET
              on a trading day; each run is saved under its ET time label.
  --historical YYYY-MM-DD
              proxy that can run any time: pull IEX 1-min bars 04:00-09:30 ET
              for that day's $1-$2 names and count how many have any IEX print
              by 04:30, 08:00 and 09:15 ET.

Usage:
  python m0/t1_iex_snapshots.py
  python m0/t1_iex_snapshots.py --historical 2026-11-13
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta

from common import (
    Alpaca,
    common_stock_universe,
    et,
    md_table,
    now_et,
    parse_ts,
    recent_trading_days,
    save_raw,
)


def sub2_by_prev_close(alp: Alpaca, syms, day: date):
    """Symbols whose prior regular-session close (SIP daily bar) was $0.80-$2.40.
    Wider than $1-$2 so names gapping into range are kept."""
    prev = recent_trading_days(alp, 1, before=day)[0]
    bars = alp.bars(syms, "1Day", et(prev, 0), et(prev, 23, 59), feed="sip", batch=1000)
    return {s: b[-1]["c"] for s, b in bars.items() if b and 0.8 <= b[-1]["c"] <= 2.4}, prev


def live(alp: Alpaca):
    t = now_et()
    today = t.date()
    syms = [a["symbol"] for a in common_stock_universe(alp.assets())]
    snaps = alp.snapshots(syms, feed="iex")
    rows = []
    for sym, s in snaps.items():
        prev = (s.get("prevDailyBar") or {}).get("c")
        if not prev or not (0.8 <= prev <= 2.4):
            continue
        lt = s.get("latestTrade") or {}
        lt_t = parse_ts(lt["t"]).astimezone(t.tzinfo) if lt.get("t") else None
        mb = s.get("minuteBar") or {}
        mb_t = parse_ts(mb["t"]).astimezone(t.tzinfo) if mb.get("t") else None
        fresh = bool(lt_t and lt_t.date() == today and lt_t >= et(today, 4))
        price = lt.get("p")
        rows.append(
            {
                "symbol": sym,
                "prev_close": prev,
                "last_trade_p": price,
                "last_trade_size": lt.get("s"),
                "last_trade_et": lt_t.strftime("%m-%d %H:%M:%S") if lt_t else None,
                "fresh_today": fresh,
                "minute_bar_et": mb_t.strftime("%m-%d %H:%M") if mb_t else None,
                "minute_bar_v": mb.get("v"),
                "minute_bar_n": mb.get("n"),
                "gap_pct": round((price / prev - 1) * 100, 1) if (fresh and price) else None,
            }
        )
    fresh = [r for r in rows if r["fresh_today"]]
    gappers = [r for r in fresh if r["gap_pct"] is not None and r["gap_pct"] >= 10 and 1 <= r["last_trade_p"] <= 2]
    tiny = [r for r in gappers if (r["last_trade_size"] or 0) < 100]
    label = t.strftime("%Y-%m-%d_%H%M")
    summary = {
        "mode": "live",
        "et_time": t.isoformat(),
        "universe_symbols": len(syms),
        "sub2_by_prev_close": len(rows),
        "with_fresh_iex_print_today": len(fresh),
        "fresh_pct": round(100 * len(fresh) / max(1, len(rows)), 1),
        "iex_gappers_ge10pct_in_1_2": len(gappers),
        "gappers_where_last_print_lt_100_shares": len(tiny),
    }
    save_raw(f"t1_live_{label}", {"summary": summary, "rows": rows})
    print(summary)
    print(md_table(sorted(gappers, key=lambda r: -r["gap_pct"])[:20],
                   ["symbol", "prev_close", "last_trade_p", "gap_pct", "last_trade_size", "last_trade_et", "minute_bar_v"]))


def historical(alp: Alpaca, day: date):
    syms = [a["symbol"] for a in common_stock_universe(alp.assets())]
    prevs, prev_day = sub2_by_prev_close(alp, syms, day)
    cands = sorted(prevs)
    iex = alp.bars(cands, "1Min", et(day, 4), et(day, 9, 30), feed="iex")
    checkpoints = {"04:30": et(day, 4, 30), "08:00": et(day, 8), "09:15": et(day, 9, 15)}
    counts = {k: 0 for k in checkpoints}
    first_bar = {}
    per_sym = []
    for sym in cands:
        bs = iex.get(sym, [])
        ts = [parse_ts(b["t"]) for b in bs]
        if ts:
            first_bar[sym] = ts[0]
        for k, cp in checkpoints.items():
            if any(x < cp for x in ts):
                counts[k] += 1
        pre915 = [b for b, x in zip(bs, ts) if x < checkpoints["09:15"]]
        per_sym.append(
            {
                "symbol": sym,
                "prev_close": prevs[sym],
                "iex_bars_before_0915": len(pre915),
                "iex_shares_before_0915": sum(b["v"] for b in pre915),
                "iex_trades_before_0915": sum(b.get("n", 0) for b in pre915),
                "first_iex_bar_et": ts[0].astimezone(checkpoints["08:00"].tzinfo).strftime("%H:%M") if ts else None,
            }
        )
    summary = {
        "mode": "historical",
        "day": day.isoformat(),
        "prev_day": prev_day.isoformat(),
        "sub2_candidates": len(cands),
        "with_any_iex_print_by": counts,
        "pct_with_any_iex_print_by": {k: round(100 * v / max(1, len(cands)), 1) for k, v in counts.items()},
    }
    save_raw(f"t1_hist_{day.isoformat()}", {"summary": summary, "rows": per_sym})
    print(summary)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--historical", type=date.fromisoformat)
    a = ap.parse_args()
    alp = Alpaca()
    historical(alp, a.historical) if a.historical else live(alp)
