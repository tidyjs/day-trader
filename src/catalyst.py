"""M3 catalyst classifier (SPEC 6).

One call per company, not per headline:
  1. Drop news items tagged with more than N symbols ("stocks moving" roundups).
  2. Ask claude-haiku-5-5 for the section 6 JSON, about that company only.
     The output is validated in code, with one retry; on failure the name is
     "classifier unavailable" (a warning, never a pass).
  3. Deterministic check: if no remaining item mentions the company name or
     ticker, catalyst_type is forced to "none" with quality 0.

The LLM never selects names, sets levels or sizes. Its output is one input to
the deterministic rules and score. Each classification is saved in the
scan's inputs, so replays don't call the model and reproduce exactly.

Eval on the fixed test set (includes wrong-company headlines):
  python -m src.catalyst --eval
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

TYPES = ["earnings", "contract", "fda", "merger", "offering", "promo", "other", "none"]
OUTPUT_SCHEMA = {
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
NONE_RESULT = {"catalyst_type": "none", "quality": 0, "promo_or_pump_flag": False, "dilution_language": False, "one_line_summary": ""}

SYSTEM = """You classify recent news for ONE small-cap US company whose stock is gapping up premarket.
You are given the company's name and ticker, its news items from the last 48 hours, and its recent SEC filing titles.

Only news ABOUT THIS COMPANY counts. News items are sometimes tagged with this ticker even though they
are about a different company (for example a "stocks moving premarket" list, or another company's merger
or earnings). Ignore anything about other companies, even if it is big news. If nothing is about this
company itself, the answer is catalyst_type "none" with quality 0.

Fields:
- catalyst_type: the main driver for THIS company. "offering" covers any equity raise, registered direct,
  ATM, warrant inducement or shelf takedown. "promo" covers paid promotion, newsletter hype, or vague
  "strategic" releases with no concrete event. "none" if there is no event about this company.
- quality: integer 0-5. 5 = concrete, material and verifiable (signed contract with a named counterparty
  and dollar value, FDA approval, definitive merger agreement, earnings with numbers). 0 = no catalyst
  or pure hype.
- promo_or_pump_flag: true if the company's own items read like promotion rather than news.
- dilution_language: true if any item about this company mentions an offering, warrants, ATM, shelf,
  convertible notes or share issuance, even in passing.
- one_line_summary: at most 20 words, factual, about this company.

Return only the JSON object."""

SUFFIXES = re.compile(
    r",?\s+(?:inc\.?|incorporated|corp\.?|corporation|co\.?,?|company|ltd\.?|limited|plc|holdings?|group|n\.v\.|s\.a\.|ag|"
    r"common stock|ordinary shares|class [a-c]|american depositary shares|ads)\b.*$",
    re.I,
)


# --------------------------------------------------------------------- deterministic parts


def core_name(name: str) -> str:
    """'J-Star Holding Co., Ltd. Class A Ordinary Shares' -> 'J-Star'."""
    n = SUFFIXES.sub("", name or "").strip(" ,.")
    return n or (name or "").strip()


GENERIC_FIRST_WORDS = {"american", "global", "first", "united", "national", "international", "general", "digital", "china",
                       "new", "great", "pacific", "atlantic", "north", "south", "east", "west", "advanced", "applied"}


def _word(text: str, w: str, flags=re.I) -> bool:
    return bool(re.search(rf"(?<![A-Za-z0-9]){re.escape(w)}(?![A-Za-z0-9])", text, flags))


def _fold(s: str) -> str:
    """Drop accents so 'Solésence' (headline) matches 'Solesence' (listing name)."""
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def mentions_company(item: dict, ticker: str, company: str) -> bool:
    text = _fold(f"{item.get('headline', '')} {item.get('summary', '')}")
    core = _fold(core_name(company))
    if core and len(core) >= 3 and _word(text, core):
        return True
    # Long names are often shortened in headlines ("Investcorp" for "Investcorp Credit
    # Management BDC"): accept a distinctive first word of 5+ letters.
    first = core.split()[0] if core else ""
    if len(core.split()) > 1 and len(first) >= 5 and first.lower() not in GENERIC_FIRST_WORDS and _word(text, first):
        return True
    # Ticker: case-sensitive whole word; short tickers only in "(XYZ)" or ":XYZ" form.
    if len(ticker) >= 3 and re.search(rf"(?<![A-Za-z0-9]){re.escape(ticker)}(?![A-Za-z0-9])", text):
        return True
    return bool(re.search(rf"[(:]\s*{re.escape(ticker)}\s*\)?", text))


def prepare_items(news: List[dict], max_symbols: int, max_items: int) -> Tuple[List[dict], int]:
    """(kept items newest first, number dropped as roundups)."""
    kept = [n for n in news if len(n.get("symbols", [])) <= max_symbols]
    kept.sort(key=lambda n: n.get("created_at", ""), reverse=True)
    return kept[:max_items], len(news) - len(kept)


def valid(d: Any) -> bool:
    return (
        isinstance(d, dict)
        and set(d) == set(OUTPUT_SCHEMA["required"])
        and d["catalyst_type"] in TYPES
        and isinstance(d["quality"], int) and not isinstance(d["quality"], bool) and 0 <= d["quality"] <= 5
        and isinstance(d["promo_or_pump_flag"], bool)
        and isinstance(d["dilution_language"], bool)
        and isinstance(d["one_line_summary"], str)
    )


def build_prompt(ticker: str, company: str, items: List[dict], filings: List[dict], summary_chars: int) -> str:
    lines = [f"Company: {company}", f"Ticker: {ticker}", "", "News items (newest first):"]
    if not items:
        lines.append("(none)")
    for i, n in enumerate(items, 1):
        lines.append(f"{i}. [{n.get('created_at', '')[:16]}] [{n.get('source', '')}] [tagged: {', '.join(n.get('symbols', []))}]")
        lines.append(f"   Headline: {n.get('headline', '')}")
        if n.get("summary"):
            lines.append(f"   Summary: {n['summary'][:summary_chars]}")
    lines += ["", "Recent SEC filings:"]
    lines += [f"- {f['form']} {f['filed']} {f.get('desc') or ''} {('items ' + f['items']) if f.get('items') else ''}".rstrip() for f in filings] or ["(none)"]
    return "\n".join(lines)


# --------------------------------------------------------------------- model call


def call_model(client, prompt: str, cfg: dict) -> Tuple[Optional[dict], dict]:
    """One attempt. Returns (parsed JSON or None, meta)."""
    import anthropic

    meta: Dict[str, Any] = {}
    try:
        r = client.messages.create(
            model=cfg["model"],
            max_tokens=cfg["max_tokens"],
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": cfg["effort"], "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}},
        )
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
        meta["error"] = f"{type(e).__name__}: {str(e)[:200]}"
        return None, meta
    meta.update(stop_reason=r.stop_reason, input_tokens=r.usage.input_tokens, output_tokens=r.usage.output_tokens)
    if r.stop_reason != "end_turn":  # refusal, max_tokens, ...
        meta["error"] = f"stop_reason {r.stop_reason}"
        return None, meta
    text = next((b.text for b in r.content if b.type == "text"), None)
    try:
        return json.loads(text) if text is not None else None, meta
    except json.JSONDecodeError as e:
        meta["error"] = f"JSONDecodeError: {e}"
        return None, meta


def classify(client, ticker: str, company: str, news: List[dict], filings: List[dict], cfg: dict) -> dict:
    """Full SPEC 6 pipeline for one company. Never raises."""
    items, dropped = prepare_items(news, cfg["max_symbols_per_item"], cfg["max_items"])
    about = [n for n in items if mentions_company(n, ticker, company)]
    rec: Dict[str, Any] = {"model": cfg["model"], "items_used": len(items), "items_dropped_roundup": dropped,
                           "items_mentioning_company": len(about), "attempts": [], "forced_none": False}
    if not items and not filings:
        rec.update(status="no_news", output=dict(NONE_RESULT))
        return rec
    prompt = build_prompt(ticker, company, items, filings, cfg["summary_chars"])
    out = None
    for _ in range(2):  # validate, retry once
        parsed, meta = call_model(client, prompt, cfg)
        ok = valid(parsed)
        meta["valid"] = ok
        if not ok and parsed is not None:
            meta["invalid_output"] = parsed
        rec["attempts"].append(meta)
        if ok:
            out = parsed
            break
    if out is None:
        rec.update(status="unavailable", output=None)
        return rec
    rec["model_output"] = dict(out)
    if not about:
        # No remaining item mentions this company: whatever the model said, no catalyst.
        out = dict(out, catalyst_type="none", quality=0)
        rec["forced_none"] = True
    rec.update(status="ok", output=out)
    return rec


# --------------------------------------------------------------------- scan integration


def news_item(n: dict, summary_chars: int) -> dict:
    return {
        "id": n.get("id"),
        "created_at": n.get("created_at"),
        "source": n.get("source"),
        "symbols": n.get("symbols", []),
        "headline": n.get("headline", ""),
        "summary": (n.get("summary") or "")[:summary_chars],
        "url": n.get("url"),
    }


def gather(alp, client, cands: List[dict], edgar_inp: Dict[str, dict], as_of: datetime, cfg: dict) -> Tuple[Dict[str, list], Dict[str, dict]]:
    """News (as of the scan time) and one classification per candidate."""
    start = as_of - timedelta(hours=cfg["news_lookback_hours"])
    news, results = {}, {}
    for r in cands:
        sym = r["symbol"]
        try:
            raw = alp.news([sym], start, as_of)
            # Alpaca filters by start/end already; check against the scan time again (no look-ahead).
            news[sym] = [news_item(n, cfg["summary_chars"]) for n in raw if n.get("created_at") and _ts(n["created_at"]) <= as_of]
        except Exception as e:
            news[sym] = []
            results[sym] = {"status": "unavailable", "output": None, "error": f"news: {type(e).__name__}: {e}"}
            continue
        since = (as_of.date() - timedelta(days=5)).isoformat()
        fl = [f for f in (edgar_inp.get(sym) or {}).get("filings", []) if f["filed"] >= since]
        results[sym] = classify(client, sym, r.get("name", ""), news[sym], fl, cfg)
    return news, results


def _ts(s: str) -> datetime:
    from src.timeutil import parse_ts
    return parse_ts(s)


# --------------------------------------------------------------------- eval


CASES = Path(__file__).resolve().parent.parent / "tests" / "data" / "catalyst_cases.json"


def check_expect(out: Optional[dict], exp: dict) -> List[str]:
    if out is None:
        return ["classifier unavailable"]
    bad = []
    if "types" in exp and out["catalyst_type"] not in exp["types"]:
        bad.append(f"type {out['catalyst_type']} not in {exp['types']}")
    if "quality_max" in exp and out["quality"] > exp["quality_max"]:
        bad.append(f"quality {out['quality']} > {exp['quality_max']}")
    if "quality_min" in exp and out["quality"] < exp["quality_min"]:
        bad.append(f"quality {out['quality']} < {exp['quality_min']}")
    for k in ("promo_or_pump_flag", "dilution_language"):
        if k in exp and out[k] != exp[k]:
            bad.append(f"{k} {out[k]} != {exp[k]}")
    return bad


def run_eval(cfg: dict) -> int:
    import anthropic

    from src.config import load_env

    load_env()
    client = anthropic.Anthropic()
    cases = json.loads(CASES.read_text())
    fails = model_fails = 0
    tin = tout = 0
    print(f"| case | wrong-co | pipeline | model alone | result |\n|---|---|---|---|---|")
    for c in cases:
        rec = classify(client, c["ticker"], c["company"], c["news"], c.get("filings", []), cfg)
        for a in rec["attempts"]:
            tin += a.get("input_tokens", 0)
            tout += a.get("output_tokens", 0)
        bad = check_expect(rec["output"], c["expect"])
        mbad = check_expect(rec.get("model_output"), c["expect"]) if rec.get("model_output") else bad
        fails += bool(bad)
        model_fails += bool(mbad)
        o, m = rec["output"] or {}, rec.get("model_output") or {}
        print(f"| {c['id']} | {'yes' if c.get('wrong_company') else ''} | {o.get('catalyst_type')}/{o.get('quality')}"
              f"{' (forced)' if rec.get('forced_none') else ''} | {m.get('catalyst_type')}/{m.get('quality')} | "
              f"{'PASS' if not bad else 'FAIL: ' + '; '.join(bad)}{'' if not mbad or bad else ' (model alone: ' + '; '.join(mbad) + ')'} |")
    print(f"\npipeline: {len(cases) - fails}/{len(cases)} pass; model alone: {len(cases) - model_fails}/{len(cases)}; "
          f"tokens in {tin}, out {tout}")
    return 1 if fails else 0


if __name__ == "__main__":
    from src.config import load_config

    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", action="store_true")
    a = ap.parse_args()
    if a.eval:
        raise SystemExit(run_eval(load_config()["catalyst"]))
    ap.print_help()
