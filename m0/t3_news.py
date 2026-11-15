"""M0 test 3: Alpaca news on free keys, and the rate limit actually reported.

  a) One call for a few symbols over 48h: status, item count, fields present.
  b) A short burst (default 25 calls) recording X-RateLimit-* after each,
     to compare the observed limit with the documented 200/min free tier.
     The burst stops early if Remaining drops below 20, so it never trips 429.

Usage: python m0/t3_news.py [--symbols A,B,C] [--burst 25]
"""
from __future__ import annotations

import argparse
import time
from datetime import timedelta

from common import DATA_URL, Alpaca, load_raw, now_et, iso, save_raw


def main(symbols, burst):
    alp = Alpaca()
    end = now_et()
    start = end - timedelta(hours=48)
    t0 = time.time()
    r = alp.get(f"{DATA_URL}/v1beta1/news", {"symbols": ",".join(symbols), "start": iso(start), "end": iso(end), "limit": 50})
    first = {
        "status": r.status_code,
        "latency_ms": round(1000 * (time.time() - t0)),
        "headers": alp.last_headers,
        "items": len(r.json().get("news", [])) if r.ok else None,
        "fields": sorted(r.json()["news"][0].keys()) if r.ok and r.json().get("news") else None,
        "body_if_error": None if r.ok else r.text[:300],
        "sample": [
            {"t": n["created_at"], "symbols": n["symbols"], "headline": n["headline"], "source": n.get("source")}
            for n in (r.json().get("news", [])[:5] if r.ok else [])
        ],
    }
    trace = []
    for i in range(burst):
        rr = alp.get(f"{DATA_URL}/v1beta1/news", {"symbols": symbols[0], "limit": 1})
        h = alp.last_headers
        trace.append({"i": i, "status": rr.status_code, **h})
        if int(h.get("x-ratelimit-remaining", "999") or 999) < 20:
            break
    limits = {t.get("x-ratelimit-limit") for t in trace}
    summary = {
        "symbols": symbols,
        "first_call": {k: v for k, v in first.items() if k != "sample"},
        "burst_calls": len(trace),
        "observed_X-RateLimit-Limit": sorted(x for x in limits if x),
        "documented_free_limit_per_min": 200,
        "any_429": any(t["status"] == 429 for t in trace),
    }
    save_raw("t3_news", {"summary": summary, "sample": first["sample"], "trace": trace})
    print(summary)
    for s in first["sample"]:
        print("-", s["t"], s["symbols"], s["headline"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols")
    ap.add_argument("--burst", type=int, default=25)
    a = ap.parse_args()
    if a.symbols:
        syms = a.symbols.split(",")
    else:
        g = load_raw("gappers") or {}
        syms = sorted({x["symbol"] for x in g.get("gappers", [])})[:10] or ["AAPL", "TSLA", "NVDA"]
    main(syms, a.burst)
