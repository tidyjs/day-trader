"""M0 test 5: Yahoo floatShares vs EDGAR shares outstanding, for ~10 gappers.

Reads tickers from docs/m0_raw/gappers.json (written by t6) unless --tickers is
given. One request per ticker with a pause between, because Yahoo is
unofficial. EDGAR numbers come from docs/m0_raw/t4_edgar.json when present,
otherwise t4 is called for the same tickers.

Flags: float > shares outstanding (impossible, so one source is stale), float
missing, and float < 15% under the 50M cap (spec: never hard-fail there).

Usage: python m0/t5_yahoo_float.py [--tickers A,B]
"""
from __future__ import annotations

import argparse
import time

import yfinance as yf

from common import load_raw, md_table, save_raw

CAP = 50_000_000


def main(tickers):
    ed = {r["ticker"]: r for r in (load_raw("t4_edgar") or {}).get("rows", [])}
    if not all(t in ed for t in tickers):
        import t4_edgar

        t4_edgar.main(tickers, 5)
        ed = {r["ticker"]: r for r in (load_raw("t4_edgar") or {}).get("rows", [])}
    rows = []
    for t in tickers:
        row = {"ticker": t}
        try:
            info = yf.Ticker(t).get_info()
            row["yahoo_float"] = info.get("floatShares")
            row["yahoo_shares_out"] = info.get("sharesOutstanding")
            row["yahoo_implied_so"] = info.get("impliedSharesOutstanding")
        except Exception as e:  # unofficial endpoint, record and move on
            row["error"] = f"{type(e).__name__}: {str(e)[:80]}"
        so = ed.get(t, {}).get("shares_out")
        row["edgar_shares_out"] = so
        row["edgar_asof"] = ed.get(t, {}).get("shares_out_asof")
        fl = row.get("yahoo_float")
        flags = []
        if not fl:
            flags.append("float_missing")
        if fl and so and fl > so * 1.02:
            flags.append("float>EDGAR_SO")
        if fl and CAP * 0.85 <= fl <= CAP * 1.15:
            flags.append("near_50M_cap")
        row["float_pct_of_so"] = round(100 * fl / so, 1) if fl and so else None
        row["passes_lt_50M"] = (fl < CAP) if fl else None
        row["flags"] = ",".join(flags) or "-"
        rows.append(row)
        time.sleep(1.5)
    summary = {
        "tested": len(rows),
        "yahoo_float_present": sum(1 for r in rows if r.get("yahoo_float")),
        "edgar_so_present": sum(1 for r in rows if r.get("edgar_shares_out")),
        "float_gt_so": sum(1 for r in rows if "float>EDGAR_SO" in r["flags"]),
        "errors": sum(1 for r in rows if r.get("error")),
    }
    save_raw("t5_yahoo_float", {"summary": summary, "rows": rows})
    print(summary)
    print(md_table(rows, ["ticker", "yahoo_float", "yahoo_shares_out", "edgar_shares_out", "edgar_asof", "float_pct_of_so", "passes_lt_50M", "flags", "error"]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers")
    a = ap.parse_args()
    if a.tickers:
        tk = a.tickers.split(",")
    else:
        g = load_raw("gappers") or {}
        tk = sorted({x["symbol"] for x in g.get("gappers", [])})[:10]
        if not tk:
            raise SystemExit("No gappers.json yet: run t6 first or pass --tickers")
    main(tk)
