"""Dump every classifier input and output from saved scans, for human review.

Usage: python -m src.review_catalyst > docs/m3_classifier_review.md
"""
from __future__ import annotations

import glob
import json
from datetime import date, timedelta

from src.catalyst import prepare_items
from src.config import ROOT, load_config

# claude-haiku-5-5 list price, $/million tokens (prompts under 100K tokens).
PRICE_IN, PRICE_OUT = 0.10, 0.50


def main() -> None:
    cfg = load_config()["catalyst"]
    days = []
    print("# Classifier review: real inputs and outputs\n")
    print(f"Model `{cfg['model']}`, effort `{cfg['effort']}`. Generated from `data/scans/*.json` by `python -m src.review_catalyst`.")
    print("Inputs are exactly what the model saw (roundups with more than 3 tagged symbols removed first).\n")
    for f in sorted(glob.glob(str(ROOT / "data/scans/*.json"))):
        j = json.load(open(f))
        inp = j["inputs"]
        rows = {r["symbol"]: r for r in j["outputs"]["candidates"]}
        tin = tout = calls = 0
        print(f"\n## {inp['day']} (news up to {inp['as_of_et'][11:16]} ET)\n")
        for sym in sorted(inp["catalyst"]):
            rec, row = inp["catalyst"][sym], rows.get(sym, {})
            kept, _ = prepare_items(inp["news"].get(sym, []), cfg["max_symbols_per_item"], cfg["max_items"])
            dropped = [n for n in inp["news"].get(sym, []) if len(n.get("symbols", [])) > cfg["max_symbols_per_item"]]
            since = (date.fromisoformat(inp["day"]) - timedelta(days=5)).isoformat()
            fl = [x for x in (inp["edgar"].get(sym) or {}).get("filings", []) if x["filed"] >= since]
            for a in rec.get("attempts", []):
                tin += a.get("input_tokens", 0)
                tout += a.get("output_tokens", 0)
                calls += 1
            print(f"### {sym} — {row.get('name', '')}\n")
            print(f"- status: `{rec.get('status')}`; attempts: {len(rec.get('attempts', []))}; forced none by name check: {rec.get('forced_none')}")
            print(f"- rule `dq_promo_or_no_catalyst`: **{row.get('dq_promo_or_no_catalyst')}**; prior-day volume multiple: {row.get('prior_day_volume_multiple')}")
            print(f"- **input, news used ({len(kept)}):**")
            for n in kept:
                print(f"  - [{n['created_at'][:16]}] [{n.get('source')}] [tagged: {', '.join(n['symbols'])}] **{n['headline']}**" + (f" — {n['summary']}" if n.get("summary") else ""))
            if not kept:
                print("  - (none)")
            if dropped:
                print(f"- input, roundups dropped ({len(dropped)}): " + "; ".join(f"\"{n['headline']}\" [{len(n['symbols'])} tags]" for n in dropped))
            print(f"- input, filings (5 days): " + ("; ".join(f"{x['form']} {x['filed']} {x.get('desc') or ''} {x.get('items') or ''}".strip() for x in fl) or "(none)"))
            print(f"- **output:** `{json.dumps(rec.get('output'))}`")
            if rec.get("forced_none"):
                print(f"- model's own output before the name check: `{json.dumps(rec.get('model_output'))}`")
            print()
        cost = tin / 1e6 * PRICE_IN + tout / 1e6 * PRICE_OUT
        days.append((inp["day"], len(inp["catalyst"]), calls, tin, tout, cost))
    print("\n## Tokens and cost per scan day\n")
    print("| day | candidates | model calls | input tokens | output tokens | est. cost |\n|---|---|---|---|---|---|")
    for d in days:
        print(f"| {d[0]} | {d[1]} | {d[2]} | {d[3]:,} | {d[4]:,} | ${d[5]:.4f} |")
    n = len(days)
    print(f"| **mean** | {sum(d[1] for d in days) / n:.1f} | {sum(d[2] for d in days) / n:.1f} | {sum(d[3] for d in days) / n:,.0f} | {sum(d[4] for d in days) / n:,.0f} | ${sum(d[5] for d in days) / n:.4f} |")
    print(f"\nPrices used: ${PRICE_IN}/M input, ${PRICE_OUT}/M output (claude-haiku-5-5 list price, prompts under 100K tokens).")


if __name__ == "__main__":
    main()
