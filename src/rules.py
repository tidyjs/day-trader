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
    r"|units?,? each consisting|\bat[- ]the[- ]market|equity distribution agreement|\bsales agreement",
    re.I,
)
OFFER = re.compile(
    r"public offering|registered direct|private placement|securities purchase agreement|underwriting agreement"
    r"|placement agency|\bat[- ]the[- ]market offering|equity distribution agreement|prospectus supplement",
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


# Equity-raise wording about the company's OWN issuance (SPEC 4.2, revised after
# MRLN: a generic "our Common Stock is listed on Nasdaq" is not an offering).
ISSUANCE = re.compile(
    r"\bwe are (?:offering|selling|issuing)\b"
    r"|\bthe company (?:is|has agreed to|agreed to) (?:offer|sell|issue)\w*"
    r"|\b(?:we|the company) (?:have |has )?(?:entered into|agreed to enter into) (?:a|an|the|certain) (?:securities purchase|underwriting|placement agency"
    r"|equity distribution|\bat[- ]the[- ]market(?: sales)?|sales|subscription|warrant inducement|equity purchase) agreements?"
    r"|\bregistered direct offering\b|\b(?:underwritten|firm[- ]commitment|best[- ]efforts) (?:public )?offering\b"
    r"|\bat[- ]the[- ]market (?:offering|program|equity|sales)\b|\bATM (?:offering|program|facility)\b"
    r"|\b(?:announces?|announced|announcing) (?:the )?(?:pricing|closing|upsizing) of\b|\bpricing of (?:its|a|an|our|the|their) [^.]{0,60}offering\b"
    r"|\bclosing of (?:its|a|an|our|the|their) [^.]{0,60}(?:offering|private placement)\b|\bwarrant inducement\b"
    r"|\bgross proceeds (?:to (?:us|the company) )?(?:of|from (?:this|the) offering)\b"
    r"|\b(?:offering|offer and sell|to sell) (?:of )?(?:up to )?(?:an aggregate of )?\$?[\d,]+(?:\.\d+)?(?: million)? (?:shares|units|american depositary shares|ADSs|of (?:our |shares of )?(?:common stock|ordinary shares))",
    re.I,
)
# Primary-offering wording strong enough to outweigh resale wording in the same document.
# Judged on a document's COVER only: deep text often mentions past offerings
# (MRLN's resale prospectus mentions its earlier underwritten offering).
STRONG_PRIMARY = re.compile(r"\bwe are (?:offering|selling)\b|\bprimary offering of\b|registered direct offering|underwritten (?:public )?offering|\bat[- ]the[- ]market (?:offering|program)", re.I)
RESALE = re.compile(
    r"selling (?:stock|share|security)holders?|\bresale\b|\boffer and resale\b"
    r"|we will not receive any (?:of the )?proceeds from (?:the|any) (?:sale|resale)",
    re.I,
)
NO_PROCEEDS = re.compile(r"we will not receive any (?:of the )?proceeds from (?:the|any) (?:sale|resale)", re.I)


def _resale_evidence(texts: List[str]) -> Optional[str]:
    """Best sentence showing a resale: the no-proceeds statement if present."""
    return _first_sentence(texts, NO_PROCEEDS) or _first_sentence(texts, RESALE)


# A prospectus supplement that only attaches a periodic or current report.
UPDATE = re.compile(
    r"prospectus supplement (?:is being filed to update|updates, amends and supplements|is filed to update|amends and supplements)"
    r"|to (?:update|supplement) the information (?:contained|included) in the prospectus with the information (?:contained|included) in",
    re.I,
)
SHELF = re.compile(r"\bwe may (?:offer|sell|offer and sell)[^.]{0,120}from time to time", re.I)


def _first_sentence(texts: List[str], rx: "re.Pattern") -> Optional[str]:
    for h in texts:
        m = rx.search(h)
        if m:
            return _sentence(h, m)
    return None


def _primary_sentence(cover: str) -> Optional[str]:
    """First primary-offering sentence on the cover that is not itself about
    selling holders ("The Selling Stockholder may sell ... in underwritten
    offerings" describes how holders sell, not a company raise)."""
    for m in STRONG_PRIMARY.finditer(cover):
        sent = _sentence(cover, m)
        if not RESALE.search(sent):
            return sent
    return None


def _texts(f: dict) -> List[str]:
    t = f.get("text") or {}
    return [t.get("cover", "")] + list(t.get("hits", []))


def classify_offering(f: dict) -> Tuple[str, str, str]:
    """('disqualify' | 'resale' | 'possible' | 'none', reason, matched sentence) for one filing.

    disqualify  the company's own equity raise (issuance wording, an active ATM,
                or 8-K item 3.02)
    resale      a resale registration: selling holders sell, the company gets no
                proceeds. Warning "resale registration, supply overhang"
    possible    an offering-type filing without clear issuance wording. Warning,
                never a silent pass
    """
    form = f["form"].upper()
    label = f"{f['form']} {f['filed']}"
    if form.startswith("8-K") and "3.02" in _items(f):
        return "disqualify", f"{label} item 3.02 (unregistered equity sale)", f"8-K items: {f.get('items')}"
    if f.get("text_error"):
        if form.startswith(OFFERING_FORMS):
            return "possible", f"{label} text not readable", f.get("text_error", "")
        return "none", "", ""
    if f.get("text") is None:  # not fetched (doc cap): an offering form is never a silent pass
        return ("possible", f"{label} not read (document cap)", "") if form.startswith(OFFERING_FORMS) else ("none", "", "")
    texts = _texts(f)
    issuance = _first_sentence(texts, ISSUANCE)
    resale = _resale_evidence(texts)
    strong = _primary_sentence(texts[0])  # cover only

    if form.startswith(OFFERING_FORMS):
        # A supplement that only attaches a periodic/current report is judged by the
        # registration it supplements. The attached report describes history (MRLN
        # 11-13: a 10-Q describing a past PIPE), so its wording is not a new raise.
        upd = _first_sentence(texts, UPDATE)
        cover_strong = _primary_sentence((f.get("text") or {}).get("cover", ""))
        if upd and not cover_strong:
            base = f.get("base")
            if base and base.get("text"):
                btexts = _texts(base)
                b_label = f"{base['form']} {base['filed']}"
                b_resale, b_strong = _resale_evidence(btexts), _primary_sentence(btexts[0])  # cover only
                b_issue = _first_sentence(btexts, ISSUANCE)
                if b_resale and not b_strong:
                    return "resale", f"{label} supplement to resale registration ({b_label}), supply overhang", b_resale
                atm = _first_sentence(btexts, re.compile(r"\bat[- ]the[- ]market|equity distribution agreement|\bsales agreement", re.I))
                if atm:
                    return "disqualify", f"{label} supplement to an active ATM / sales-agreement prospectus ({b_label})", atm
                if b_issue:
                    return "possible", f"{label} supplement to a primary offering prospectus ({b_label}); no new offering terms", b_issue
            return "possible", f"{label} prospectus supplement updating an existing registration; no new offering terms", upd
        if resale and not strong:
            return "resale", f"{label} resale registration, supply overhang", resale
        if issuance:
            return "disqualify", f"{label} company equity raise", issuance
        shelf = _first_sentence(texts, SHELF)
        if shelf:
            return "possible", f"{label} shelf registration (future offering capacity)", shelf
        return "possible", f"{label} offering-type filing, no equity-raise wording", (texts[0] or "")[:300]

    if form.startswith(CURRENT_REPORTS):
        if issuance:
            return "disqualify", f"{label} company equity raise", issuance
        if resale:
            return "resale", f"{label} resale registration, supply overhang", resale
        generic = _first_sentence(texts, OFFER)
        if generic:
            return "possible", f"{label} offering language, no issuance wording", generic
    return "none", "", ""


def offering(filings: List[dict], day: date, lookback_days: int) -> Tuple[str, List[str], List[str], List[dict]]:
    """(status, disqualify reasons, warnings ("possible offering: ..." or
    "resale registration, supply overhang: ..."), evidence)."""
    since = day - timedelta(days=lookback_days)
    dq, maybe, ev = [], [], []
    for f in filings:
        if date.fromisoformat(f["filed"]) < since:
            continue
        kind, why, sent = classify_offering(f)
        if kind == "none":
            continue
        if kind == "disqualify":
            dq.append(why)
        elif kind == "resale":
            maybe.append(f"resale registration, supply overhang: {why}")
        else:
            maybe.append(f"possible offering: {why}")
        ev.append({"rule": "offering", "result": kind, "filing": why, "sentence": sent, "url": filing_url(f)})
    return (FAIL if dq else PASS), dq, maybe, ev


RS_BOILERPLATE = re.compile(
    r"adjust\w*[^.]{0,100}(?:split|consolidation)"          # anti-dilution clauses in warrants / agreements
    r"|including reverse (?:stock |share )?splits"
    r"|(?:potential need|may (?:need|be required) to|could|might|if we)[^.]{0,80}reverse",
    re.I,
)
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
DATE_RE = re.compile(rf"\b({MONTHS}) (\d{{1,2}}), (\d{{4}})")
# Wording just before a date that makes it the split's EFFECTIVE date.
EFFECTIVE_CTX = re.compile(
    r"effective(?: as of| on| date)?|effected|effecting|became effective|become effective|took effect|take effect"
    r"|(?:post|split)[- ]?(?:split|adjusted)? basis[^.]{0,80}?on|began trading[^.]{0,80}?on|begin trading[^.]{0,80}?on|market open on",
    re.I,
)
# Wording that makes a date an approval / meeting / record date instead.
APPROVAL_CTX = re.compile(r"approv|meeting|held on|record date|dated|adopt|resolution|vote|filed|announced", re.I)
RECENT_SPLIT_DAYS = 90


def _dates(s: str) -> List[date]:
    out = []
    for m, d, y in DATE_RE.findall(s):
        try:
            out.append(datetime.strptime(f"{m} {d} {y}", "%B %d %Y").date())
        except ValueError:
            pass
    return out


def effective_dates(s: str) -> List[date]:
    """Dates in a sentence that are the split's effective date: an effective-type
    word within 100 chars before the date, with no approval/meeting word between."""
    out = []
    for m in DATE_RE.finditer(s):
        before = s[max(0, m.start() - 100):m.start()]
        ctx = list(EFFECTIVE_CTX.finditer(before))
        if not ctx:
            continue
        between = before[ctx[-1].end():]
        if APPROVAL_CTX.search(between):
            continue
        try:
            out.append(datetime.strptime(" ".join(m.groups()), "%B %d %Y").date())
        except ValueError:
            pass
    return out


def classify_reverse_split_sentence(s: str, day: date, following: str = "") -> Optional[Tuple[str, Optional[date]]]:
    """('pending' | 'completed' | 'nodate', effective date) or None (boilerplate / no match).

    Decided by the effective date against the scan day (rule set 2026-11-16):
      effective on or after the scan day  -> pending (disqualify)
      effective before the scan day       -> completed (warning if within 90 days)
      no effective date in the sentence   -> nodate ("possible reverse split" warning)
    """
    if not RSPLIT.search(s) or RS_BOILERPLATE.search(s):
        return None
    # The effective date is often in the next sentence (EZGO 11-05: "...approved a
    # reverse share split ... The Company's ordinary shares began trading on a
    # post-split basis ... on November 5, 2026").
    ds = effective_dates(s) or effective_dates(following)
    if not ds:
        return "nodate", None
    eff = max(ds)
    return ("pending" if eff >= day else "completed"), eff


def reverse_split(filings: List[dict], day: date, lookback_days: int) -> Tuple[str, List[str], List[str], List[dict]]:
    """(status, disqualify reasons, warnings, evidence), by effective date."""
    since = day - timedelta(days=lookback_days)
    dq, warn, ev = [], [], []
    for f in filings:
        if date.fromisoformat(f["filed"]) < since or not f.get("text"):
            continue
        t = f["text"]
        found: Dict[str, Tuple[str, Optional[date]]] = {}  # kind -> (sentence, date); latest date wins
        for h in [t["cover"]] + t["hits"]:
            sents = re.split(r"(?<=[.;])\s+", h)
            for i, sent in enumerate(sents):
                k = classify_reverse_split_sentence(sent, day, " ".join(sents[i + 1:i + 3]))
                if not k:
                    continue
                kind, eff = k
                if kind not in found or (eff and (found[kind][1] is None or eff > found[kind][1])):
                    found[kind] = (sent.strip()[:400], eff)
        label = f"{f['form']} {f['filed']}"
        if "pending" in found:
            sent, eff = found["pending"]
            dq.append(f"{label} reverse split effective {eff} (on or after the scan day)")
            ev.append({"rule": "reverse_split", "result": "disqualify", "filing": f"{label} effective {eff}", "sentence": sent, "url": f.get("url", "")})
        elif "completed" in found:
            sent, eff = found["completed"]
            age = (day - eff).days
            if age <= RECENT_SPLIT_DAYS:
                warn.append(f"reverse split completed {eff} ({age} days ago, per {label})")
            ev.append({"rule": "reverse_split", "result": "completed", "filing": f"{label} effective {eff}", "sentence": sent, "url": f.get("url", "")})
        elif "nodate" in found:
            sent, _ = found["nodate"]
            warn.append(f"possible reverse split: {label} mentions one, no effective date found")
            ev.append({"rule": "reverse_split", "result": "possible", "filing": f"{label} no effective date", "sentence": sent, "url": f.get("url", "")})
    return (FAIL if dq else PASS), dq, warn, ev


AMENDED_FORMS = ("10-Q/A", "10-K/A")


def amended_filings(filings: List[dict], day: date, lookback_days: int = 90, minimum: int = 2) -> Optional[str]:
    """Warning when there are >= `minimum` 10-Q/A or 10-K/A filings in the window."""
    since = day - timedelta(days=lookback_days)
    n = [f for f in filings if f["form"].upper() in AMENDED_FORMS and date.fromisoformat(f["filed"]) >= since]
    if len(n) >= minimum:
        forms = ", ".join(sorted({f"{f['form']} {f['filed']}" for f in n}))
        return f"recent amended filings (possible restatement): {len(n)} in {lookback_days} days ({forms})"
    return None


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


# --------------------------------------------------------------------- 4.2 catalyst (M3)


def prior_day_volume_multiple(daily: List[dict], prior_day: date, cfg: dict) -> Optional[float]:
    """Prior session volume / average of the sessions before it, or None."""
    bars = sorted((b for b in daily if parse_ts(b["t"]).astimezone(ET).date() <= prior_day), key=lambda b: b["t"])
    if not bars or parse_ts(bars[-1]["t"]).astimezone(ET).date() != prior_day:
        return None
    before = bars[:-1][-cfg["avg_volume_sessions"]:]
    if len(before) < cfg["min_avg_sessions"]:
        return None
    avg = statistics.mean(b["v"] for b in before)
    return round(bars[-1]["v"] / avg, 2) if avg else None


def catalyst_rule(rec: Optional[dict], surge: Optional[float], surge_min: float) -> Tuple[str, str, List[str]]:
    """dq_promo_or_no_catalyst: (status, disqualify reason, warnings)."""
    if not rec:
        return UNKNOWN, "", ["classifier not run"]
    if rec.get("status") == "unavailable":
        return UNKNOWN, "", [f"classifier unavailable{': ' + rec['error'] if rec.get('error') else ''}"]
    out = rec["output"]
    votes = rec.get("votes") or {}
    vote_note = f" ({votes['promo']}/{votes['valid_runs']} runs)" if "promo" in votes else ""
    if out["promo_or_pump_flag"] or out["catalyst_type"] == "promo":
        return FAIL, f"classifier: promo/pump{vote_note} ({out['one_line_summary'][:80]})", []
    warns = []
    if out["catalyst_type"] == "unclear":
        warns.append(f"classifier runs disagree on catalyst type ({votes.get('types')})")
    if out["catalyst_type"] == "none":
        if surge is None:
            return UNKNOWN, "", ["no verifiable catalyst; prior-day volume surge unknown (short history)"]
        if surge < surge_min:
            none_note = f", {votes['none']}/{votes['valid_runs']} runs" if "none" in votes and not rec.get("forced_none") else ""
            return FAIL, f"no verifiable catalyst{none_note} and no prior-day volume surge ({surge:.1f}x)", []
    return PASS, "", warns
