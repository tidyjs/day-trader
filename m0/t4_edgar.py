"""M0 test 4: SEC EDGAR access.

  a) company_tickers.json downloads with our User-Agent; ticker -> CIK map size.
  b) companyfacts: latest dei:EntityCommonStockSharesOutstanding (with its
     period end and filing date), and EntityPublicFloat (a $ value, shown only
     to make the staleness visible).
  c) submissions: filings in the last N days, flagged if the form is an
     offering-type form (424B*, S-1, S-3, F-1, F-3 and amendments) or an 8-K.
     8-K items 1.01 / 3.02 / 8.01 are recorded since 3.02 means unregistered
     equity sales. Reading 8-K text for offering language is left to M2.

Needs no API key, only SEC_USER_AGENT ("Name email").

Usage: python m0/t4_edgar.py [--tickers A,B] [--days 5]
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta

from common import load_raw, md_table, save_raw, sec_get, sec_session

OFFERING_PREFIXES = ("424B", "S-1", "S-3", "F-1", "F-3")


def latest_fact(facts, ns, name, unit):
    try:
        pts = facts["facts"][ns][name]["units"][unit]
    except KeyError:
        return None
    pts = sorted(pts, key=lambda p: (p.get("end", ""), p.get("filed", "")))
    p = pts[-1]
    return {"val": p["val"], "end": p.get("end"), "filed": p.get("filed"), "form": p.get("form")}


def main(tickers, days):
    s = sec_session()
    r = sec_get(s, "https://www.sec.gov/files/company_tickers.json")
    ua_ok = r.status_code == 200
    tmap = {v["ticker"].upper(): v for v in r.json().values()} if ua_ok else {}
    since = date.today() - timedelta(days=days)
    rows = []
    for t in tickers:
        row = {"ticker": t}
        m = tmap.get(t.upper())
        if not m:
            row["note"] = "not in company_tickers.json"
            rows.append(row)
            continue
        cik = f"{int(m['cik_str']):010d}"
        row["cik"] = cik
        f = sec_get(s, f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json")
        if f.status_code == 200:
            fj = f.json()
            so = latest_fact(fj, "dei", "EntityCommonStockSharesOutstanding", "shares")
            pf = latest_fact(fj, "dei", "EntityPublicFloat", "USD")
            row["shares_out"] = so["val"] if so else None
            row["shares_out_asof"] = so["end"] if so else None
            row["public_float_usd"] = pf["val"] if pf else None
            row["public_float_asof"] = pf["end"] if pf else None
        else:
            row["facts_status"] = f.status_code
        sub = sec_get(s, f"https://data.sec.gov/submissions/CIK{cik}.json")
        if sub.status_code == 200:
            rec = sub.json()["filings"]["recent"]
            recent = []
            for i, form in enumerate(rec["form"]):
                fd = date.fromisoformat(rec["filingDate"][i])
                if fd < since:
                    continue
                recent.append(
                    {
                        "form": form,
                        "date": rec["filingDate"][i],
                        "items": rec.get("items", [""] * len(rec["form"]))[i],
                        "offering_form": form.upper().startswith(OFFERING_PREFIXES),
                    }
                )
            row["filings_last_n_days"] = len(recent)
            row["offering_forms"] = ",".join(sorted({x["form"] for x in recent if x["offering_form"]})) or "-"
            row["8k_items"] = ";".join(x["items"] for x in recent if x["form"].startswith("8-K") and x["items"]) or "-"
            row["_recent"] = recent
        else:
            row["subs_status"] = sub.status_code
        rows.append(row)
    summary = {
        "user_agent_accepted": ua_ok,
        "company_tickers_status": r.status_code,
        "tickers_in_map": len(tmap),
        "lookback_days": days,
        "tested": len(tickers),
        "mapped": sum(1 for x in rows if x.get("cik")),
        "with_shares_outstanding": sum(1 for x in rows if x.get("shares_out")),
    }
    save_raw("t4_edgar", {"summary": summary, "rows": rows})
    print(summary)
    print(md_table(rows, ["ticker", "cik", "shares_out", "shares_out_asof", "public_float_asof", "filings_last_n_days", "offering_forms", "8k_items", "note"]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers")
    ap.add_argument("--days", type=int, default=5)
    a = ap.parse_args()
    if a.tickers:
        tk = a.tickers.split(",")
    else:
        g = load_raw("gappers") or {}
        tk = sorted({x["symbol"] for x in g.get("gappers", [])})[:15] or ["AAPL", "SNDL", "PLUG"]
    main(tk, a.days)
