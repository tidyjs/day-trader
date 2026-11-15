"""M0 test 7: Haiku catalyst classifier on ~20 real headlines, for eyeballing.

Headlines come from Alpaca news for the t6 gappers (the 48h before each
gap day's 09:15 ET), or from --file (JSON list of {"symbol","headline","summary"}).
Each headline is classified on its own using the section 6 contract, via
structured outputs, then validated in code (quality 0-5) with one retry.

The LLM output here is only printed for review. Nothing selects names.

Usage: python m0/t7_classifier.py [--n 20] [--file headlines.json]
"""
from __future__ import annotations

import argparse
import json
from datetime import date, timedelta

import anthropic

from common import Alpaca, et, load_raw, md_table, need, save_raw

MODEL = "claude-haiku-5-5"
TYPES = ["earnings", "contract", "fda", "merger", "offering", "promo", "other", "none"]
SCHEMA = {
    "type": "object",
    "properties": {
        "catalyst_type": {"type": "string", "enum": TYPES},
        "quality": {"type": "integer"},
        "promo_or_pump_flag": {"type": "boolean"},
        "dilution_language": {"type": "boolean"},
        "one_line_summary": {"type": "string"},
    },
    "required": ["catalyst_type", "quality", "promo_or_pump_flag", "dilution_language", "one_line_summary"],
    "additionalProperties": False,
}
SYSTEM = """You classify news about a small-cap US stock that is gapping up premarket.
Return only the JSON object described by the schema.

catalyst_type: the main driver in the text. "offering" covers any equity raise,
registered direct, ATM, warrant inducement or shelf takedown. "promo" covers paid
promotion, newsletter hype or vague "strategic" press releases with no concrete
event. "none" if the text describes no event.
quality: 0-5 integer. 5 = concrete, material, verifiable (signed contract with a
named counterparty and dollar value, FDA approval, definitive merger agreement,
earnings with numbers). 0 = no catalyst or pure hype.
promo_or_pump_flag: true if the text reads like promotion rather than news.
dilution_language: true if the text mentions offerings, warrants, ATM, shelf,
convertible notes, or share issuance, even in passing.
one_line_summary: at most 20 words, factual."""


def valid(d):
    return (
        isinstance(d, dict)
        and d.get("catalyst_type") in TYPES
        and isinstance(d.get("quality"), int)
        and 0 <= d["quality"] <= 5
        and isinstance(d.get("promo_or_pump_flag"), bool)
        and isinstance(d.get("dilution_language"), bool)
        and isinstance(d.get("one_line_summary"), str)
    )


def classify(client, item):
    text = f"Ticker: {item['symbol']}\nHeadline: {item['headline']}\nSummary: {item.get('summary') or '(none)'}"
    for attempt in range(2):
        try:
            r = client.messages.create(
                model=MODEL,
                max_tokens=4000,
                system=SYSTEM,
                messages=[{"role": "user", "content": text}],
                output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
            )
            if r.stop_reason == "refusal":
                continue
            out = json.loads(next(b.text for b in r.content if b.type == "text"))
            if valid(out):
                return out, attempt, r.usage
        except (json.JSONDecodeError, StopIteration, anthropic.APIStatusError, anthropic.APIConnectionError):
            pass
    return {"catalyst_type": "classifier unavailable"}, 2, None


def headlines_from_gappers(n):
    g = load_raw("gappers") or {}
    rows = sorted(g.get("gappers", []), key=lambda r: -r["pm_dollar_vol"])
    alp = Alpaca()
    items, seen = [], set()
    for r in rows:
        d = date.fromisoformat(r["date"])
        end = et(d, 9, 15)
        for nws in alp.news([r["symbol"]], end - timedelta(hours=48), end, limit=5)[:3]:
            if nws["headline"] in seen:
                continue
            seen.add(nws["headline"])
            items.append({"symbol": r["symbol"], "date": r["date"], "headline": nws["headline"], "summary": nws.get("summary", "")})
        if len(items) >= n:
            break
    return items[:n]


def main(n, path):
    need("ANTHROPIC_API_KEY")
    items = json.loads(open(path).read()) if path else headlines_from_gappers(n)
    if not items:
        raise SystemExit("No headlines found (run t6 first, or pass --file)")
    client = anthropic.Anthropic()
    rows, tin, tout = [], 0, 0
    for it in items:
        out, retries, usage = classify(client, it)
        if usage:
            tin += usage.input_tokens
            tout += usage.output_tokens
        rows.append({**it, **out, "retries": retries, "headline": it["headline"][:90]})
    summary = {
        "model": MODEL,
        "headlines": len(rows),
        "unavailable": sum(1 for r in rows if r["catalyst_type"] == "classifier unavailable"),
        "needed_retry": sum(1 for r in rows if r["retries"] == 1),
        "input_tokens": tin,
        "output_tokens": tout,
    }
    save_raw("t7_classifier", {"summary": summary, "rows": rows})
    print(summary)
    print(md_table(rows, ["symbol", "headline", "catalyst_type", "quality", "promo_or_pump_flag", "dilution_language", "one_line_summary"]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--file")
    a = ap.parse_args()
    main(a.n, a.file)
