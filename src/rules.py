"""SPEC 4.1-4.3 rules as pure functions of saved inputs.

Every rule returns a status string so candidates.csv can show what each rule
did to each name:
  "pass"     rule met (for disqualifiers: not disqualified)
  "fail"     rule not met (for disqualifiers: disqualified)
  "unknown"  could not be decided from the data; see the name's warnings
  ""         not checked (only Yahoo float, which is called only for names
             that survive every cheaper rule)
"""
from __future__ import annotations

import re
import statistics
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from src.timeutil import ET, parse_ts

PASS, FAIL, UNKNOWN, NOT_CHECKED = "pass", "fail", "unknown", ""


def threshold(value: Optional[float], minimum: float) -> str:
    if value is None:
        return UNKNOWN
    return PASS if value >= minimum else FAIL


# --------------------------------------------------------------------- 4.1


def continuation(daily: List[dict], prior_day: date, cfg: dict) -> Tuple[str, str]:
    """In at least one of the last N sessions: close up >= X% or volume >= Mx
    the average volume of the sessions before that window.

    Note: Alpaca daily volume includes extended hours (checked in M1), so
    the multiple compares like with like.
    """
    bars = sorted((b for b in daily if parse_ts(b["t"]).astimezone(ET).date() <= prior_day), key=lambda b: b["t"])
    n = cfg["sessions"]
    if len(bars) < 2:
        return UNKNOWN, "fewer than 2 sessions of history"
    window = bars[-n:]
    before = bars[: len(bars) - len(window)]
    avg_src = before[-cfg["avg_volume_sessions"]:]
    avg = statistics.mean(b["v"] for b in avg_src) if len(avg_src) >= cfg["min_avg_sessions"] else None
    notes, any_unknown = [], False
    for i, b in enumerate(window):
        idx = len(before) + i
        d = parse_ts(b["t"]).astimezone(ET).strftime("%m-%d")
        # Rounded so an exact +20.00% isn't lost to float error (1.2/1.0-1 = 0.19999...).
        up = round((b["c"] / bars[idx - 1]["c"] - 1) * 100, 6) if idx >= 1 and bars[idx - 1]["c"] else None
        mult = round(b["v"] / avg, 6) if avg else None
        if (up is not None and up >= cfg["close_up_pct"]) or (mult is not None and mult >= cfg["volume_multiple"]):
            parts = [f"{d}"] + ([f"{up:+.1f}%"] if up is not None else []) + ([f"{mult:.1f}x vol"] if mult is not None else [])
            return PASS, " ".join(parts)
        if up is None or mult is None:
            any_unknown = True
        notes.append(f"{d} {'' if up is None else f'{up:+.1f}%'}{'' if mult is None else f' {mult:.1f}x'}".strip())
    if len(window) < n or any_unknown:
        return UNKNOWN, "; ".join(notes) + " (short history)"
    return FAIL, "; ".join(notes)


def prior_range(prior_bar: Optional[dict], top_pct: float) -> Tuple[str, Optional[float]]:
    """Prior close in the top X% of its regular-session range (Alpaca daily
    high/low are regular-session only, checked in M2)."""
    if not prior_bar or prior_bar["h"] <= prior_bar["l"]:
        return UNKNOWN, None
    pos = round((prior_bar["c"] - prior_bar["l"]) / (prior_bar["h"] - prior_bar["l"]) * 100, 6)
    return (PASS if pos >= 100 - top_pct else FAIL), round(pos, 1)


def edgar_shares(points: List[dict], day: date) -> Optional[dict]:
    """Latest shares-outstanding point filed before the scan day (no look-ahead)."""
    ok = [p for p in points if p.get("filed") and date.fromisoformat(p["filed"]) < day]
    return max(ok, key=lambda p: (p.get("end") or "", p["filed"])) if ok else None


def float_rule(yahoo: Optional[dict], edgar_so: Optional[dict], cfg: dict) -> Tuple[str, Optional[float], str, List[str]]:
    """(status, float_shares, source, warnings). Never hard-fails within the
    margin over the cap (SPEC 4.1); a missing float is a warning, not a fail."""
    cap, margin = cfg["float_max"], cfg["float_margin_pct"] / 100
    warns: List[str] = []
    fl = (yahoo or {}).get("floatShares")
    if fl:
        if fl < cap:
            return PASS, fl, "yahoo", warns
        if fl < cap * (1 + margin):
            return PASS, fl, "yahoo", [f"float {fl / 1e6:.1f}M within {cfg['float_margin_pct']:.0f}% over the {cap / 1e6:.0f}M cap"]
        return FAIL, fl, "yahoo", warns
    warns.append("float missing (Yahoo)")
    so = (edgar_so or {}).get("val")
    if so and so < cap:
        return PASS, so, "edgar shares outstanding (ceiling)", warns
    return UNKNOWN, None, "", warns


# --------------------------------------------------------------------- 4.2 / 4.3 filings

EQUITY = re.compile(
    r"common stock|ordinary shares|american depositary|\bADSs?\b|pre-funded warrants?|warrants? to purchase"
    r"|units?,? each consisting|at[- ]the[- ]market|equity distribution agreement|\bsales agreement",
    re.I,
)
OFFER = re.compile(
    r"public offering|registered direct|private placement|securities purchase agreement|underwriting agreement"
    r"|placement agency|at[- ]the[- ]market offering|equity distribution agreement|prospectus supplement",
    re.I,
)
RSPLIT = re.compile(
    r"reverse (?:stock |share )?split|share consolidation|consolidation of (?:the company'?s |our |its )?(?:issued )?(?:ordinary |common )?shares",
    re.I,
)
OFFERING_FORMS = ("424B", "S-1", "S-3", "F-1", "F-3")
CURRENT_REPORTS = ("8-K", "6-K")


def _items(f: dict) -> List[str]:
    return [x.strip() for x in (f.get("items") or "").split(",") if x.strip()]


def _sentence(text: str, m: "re.Match", limit: int = 400) -> str:
    """The sentence around a regex match, trimmed to `limit` chars."""
    a = max(text.rfind(". ", 0, m.start()) + 2, 0) if text.rfind(". ", 0, m.start()) >= 0 else 0
    b = text.find(". ", m.end())
    b = len(text) if b < 0 else b + 1
    a = max(a, m.start() - limit // 2)
    b = min(b, m.end() + limit // 2)
    return text[a:b].strip()


def filing_url(f: dict) -> str:
    return f.get("url", "")


def classify_offering(f: dict) -> Tuple[str, str, str]:
    """('disqualify' | 'possible' | 'none', reason, matched sentence) for one filing."""
    form = f["form"].upper()
    label = f"{f['form']} {f['filed']}"
    if form.startswith("8-K") and "3.02" in _items(f):
        return "disqualify", f"{label} item 3.02 (unregistered equity sale)", f"8-K items: {f.get('items')}"
    if f.get("text_error"):
        if form.startswith(OFFERING_FORMS):
            return "possible", f"{label} text not readable", f.get("text_error", "")
        return "none", "", ""
    t = f.get("text")
    if t is None:  # text not fetched (doc cap); an offering form is never a silent pass
        return ("possible", f"{label} not read (document cap)", "") if form.startswith(OFFERING_FORMS) else ("none", "", "")
    if form.startswith(OFFERING_FORMS):
        m = EQUITY.search(t["cover"])
        if m:
            return "disqualify", f"{label} names equity on its cover", _sentence(t["cover"], m)
        for h in t["hits"]:
            m = EQUITY.search(h)
            if m:
                return "possible", f"{label} mentions equity, not on its cover", _sentence(h, m)
        return "possible", f"{label} offering-type filing, no equity wording found", t["cover"][:300]
    if form.startswith(CURRENT_REPORTS):
        for h in [t["cover"]] + t["hits"]:
            mo, me = OFFER.search(h), EQUITY.search(h)
            if mo and me:
                return "disqualify", f"{label} offering language with equity terms", _sentence(h, mo)
        for h in [t["cover"]] + t["hits"]:
            mo = OFFER.search(h)
            if mo:
                return "possible", f"{label} offering language, no equity terms", _sentence(h, mo)
    return "none", "", ""


def offering(filings: List[dict], day: date, lookback_days: int) -> Tuple[str, List[str], List[str], List[dict]]:
    """(status, disqualify reasons, possible-offering warnings, evidence)."""
    since = day - timedelta(days=lookback_days)
    dq, maybe, ev = [], [], []
    for f in filings:
        if date.fromisoformat(f["filed"]) < since:
            continue
        kind, why, sent = classify_offering(f)
        if kind == "none":
            continue
        (dq if kind == "disqualify" else maybe).append(why)
        ev.append({"rule": "offering", "result": kind, "filing": why, "sentence": sent, "url": filing_url(f)})
    return (FAIL if dq else PASS), dq, maybe, ev


RS_BOILERPLATE = re.compile(
    r"adjust\w*[^.]{0,100}(?:split|consolidation)"          # anti-dilution clauses in warrants / agreements
    r"|including reverse (?:stock |share )?splits"
    r"|(?:potential need|may (?:need|be required) to|could|might|if we)[^.]{0,80}reverse",
    re.I,
)
RS_ACTION = re.compile(
    r"approv|authori[sz]|ratio|\b1-for-\d+|\b\d+-for-1\b|consolidated (?:class [ab] )?(?:ordinary |common )?shares"
    r"|split-adjusted|will (?:effect|become effective|begin trading)|intends? to effect|plans? to effect|announc|effective (?:date|time)",
    re.I,
)
RS_DONE = re.compile(r"\b(?:effected|effecting|completed|became effective|was effective|following (?:the|our|its))\b", re.I)
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
DATE_RE = re.compile(rf"\b({MONTHS}) (\d{{1,2}}), (\d{{4}})")


def _dates(s: str) -> List[date]:
    out = []
    for m, d, y in DATE_RE.findall(s):
        try:
            out.append(datetime.strptime(f"{m} {d} {y}", "%B %d %Y").date())
        except ValueError:
            pass
    return out


def classify_reverse_split_sentence(s: str, day: date) -> Optional[str]:
    """'pending' | 'completed' | 'mention' | None (boilerplate / no match)."""
    if not RSPLIT.search(s) or RS_BOILERPLATE.search(s):
        return None
    ds = _dates(s)
    if ds and any(d >= day for d in ds):
        return "pending"  # a date on or after the scan day: not done yet
    if RS_DONE.search(s) and ds:
        return "completed"
    if RS_ACTION.search(s):
        return "pending"
    return "mention"


def reverse_split(filings: List[dict], day: date, lookback_days: int) -> Tuple[str, List[str], List[str], List[dict]]:
    """(status, disqualify reasons, warnings). Sentence-level so boilerplate
    (warrant adjustment clauses, risk factors) and completed splits don't
    disqualify, while an unclear mention is still a warning, never silent."""
    since = day - timedelta(days=lookback_days)
    dq, warn, ev = [], [], []
    for f in filings:
        if date.fromisoformat(f["filed"]) < since or not f.get("text"):
            continue
        t = f["text"]
        kinds: Dict[str, str] = {}  # kind -> first sentence of that kind
        for h in [t["cover"]] + t["hits"]:
            for s in re.split(r"(?<=[.;])\s+", h):
                k = classify_reverse_split_sentence(s, day)
                if k and k not in kinds:
                    kinds[k] = s.strip()[:400]
        label = f"{f['form']} {f['filed']}"
        for k, result, msg, bucket in (
            ("pending", "disqualify", f"{label} reverse split approved or pending", dq),
            ("completed", "completed", f"reverse split completed (per {label})", warn),
            ("mention", "possible", f"possible reverse split: {label} mentions one", warn),
        ):
            if k in kinds:
                bucket.append(msg)
                ev.append({"rule": "reverse_split", "result": result, "filing": label, "sentence": kinds[k], "url": filing_url(f)})
                break
    return (FAIL if dq else PASS), dq, warn, ev


def deficiency(filings: List[dict], day: date, lookback_days: int) -> List[str]:
    since = day - timedelta(days=lookback_days)
    return [f"8-K {f['filed']} item 3.01 (listing deficiency)" for f in filings
            if f["form"].upper().startswith("8-K") and "3.01" in _items(f) and date.fromisoformat(f["filed"]) >= since]


# --------------------------------------------------------------------- 4.3 other warnings


def spread_pct(quotes: List[dict], cutoff: datetime, max_quotes: int) -> Optional[float]:
    """Median relative spread of the last quotes before the cutoff."""
    good = [q for q in quotes if q.get("bp", 0) > 0 and q.get("ap", 0) >= q.get("bp", 0) and parse_ts(q["t"]) < cutoff]
    good.sort(key=lambda q: q["t"])
    good = good[-max_quotes:]
    if not good:
        return None
    return round(statistics.median((q["ap"] - q["bp"]) / ((q["ap"] + q["bp"]) / 2) * 100 for q in good), 2)


def shares_mismatch(yahoo: Optional[dict], edgar_so: Optional[dict], pct: float) -> Optional[str]:
    y = (yahoo or {}).get("sharesOutstanding") or (yahoo or {}).get("impliedSharesOutstanding")
    e = (edgar_so or {}).get("val")
    if not y or not e:
        return None
    diff = abs(y - e) / min(y, e) * 100
    return f"Yahoo vs EDGAR shares outstanding differ {diff:.0f}% ({y / 1e6:.1f}M vs {e / 1e6:.1f}M)" if diff > pct else None
