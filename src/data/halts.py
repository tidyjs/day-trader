"""Nasdaq Trader trade-halts RSS (free, public): a warning only, never a
disqualifier (SPEC 4.3).

The feed has no history: it lists today's halts plus ones not yet resumed.
So each scan saves the full feed contents in its inputs, and a historical
scan (scan day before the fetch day) gets "halt status unknown".

Coverage: M2/M3 check on 2026-11-15 saw Market values NASDAQ and AMEX
(NYSE American). No NYSE-listed halt was in that (Sunday) sample, so NYSE
coverage is recorded per scan in `markets` until it is confirmed.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET_XML
from datetime import date, datetime
from typing import Dict, List, Optional

import requests

from src.timeutil import ET

URL = "https://www.nasdaqtrader.com/rss.aspx?feed=tradehalts"
FIELDS = ["HaltDate", "HaltTime", "IssueSymbol", "IssueName", "Market", "ReasonCode",
          "PauseThresholdPrice", "ResumptionDate", "ResumptionQuoteTime", "ResumptionTradeTime"]


def parse(xml: "str | bytes") -> List[dict]:
    # The feed starts with a UTF-8 byte-order mark; parse bytes so it is handled.
    if isinstance(xml, str):
        xml = xml.lstrip("﻿").encode("utf-8")
    root = ET_XML.fromstring(xml)
    out = []
    for item in root.iter("item"):
        rec = {}
        for child in item:
            tag = child.tag.split("}", 1)[-1]  # strip the ndaq namespace
            if tag in FIELDS:
                rec[tag] = (child.text or "").strip()
        if rec.get("IssueSymbol"):
            out.append(rec)
    return out


def fetch(now: datetime, timeout: int = 20) -> dict:
    """Never raises: a failure is recorded so the scan can warn."""
    rec: dict = {"fetched_at": now.isoformat(), "ok": False, "items": [], "error": None}
    try:
        r = requests.get(URL, timeout=timeout, headers={"User-Agent": "DayTraderResearch scanner"})
        r.raise_for_status()
        rec["items"] = parse(r.content)
        rec["ok"] = True
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {str(e)[:150]}"
    rec["markets"] = sorted({i.get("Market", "") for i in rec["items"]})
    return rec


def _dt(d: str, t: str) -> Optional[datetime]:
    if not d or not t:
        return None
    try:
        return datetime.strptime(f"{d} {t[:8]}", "%m/%d/%Y %H:%M:%S").replace(tzinfo=ET)
    except ValueError:
        return None


LOG_COLUMNS = ["fetched_at", "ok", "items", "markets"]


def log_markets(feed: dict, path) -> None:
    """Append which markets the feed labelled, so NYSE coverage can be confirmed."""
    import csv
    from collections import Counter

    counts = Counter(i.get("Market", "") for i in feed.get("items", []))
    new = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(LOG_COLUMNS)
        w.writerow([feed["fetched_at"], feed["ok"], len(feed.get("items", [])), " ".join(f"{k}:{v}" for k, v in sorted(counts.items()))])


def status(feed: Optional[dict], sym: str, day: date, as_of: datetime, exchange: Optional[str] = None,
           confirmed_markets: Optional[List[str]] = None) -> Optional[str]:
    """Warning text, or None if not halted at as_of.

    A name listed on a market the feed is not confirmed to cover (today: NYSE,
    ARCA, BATS) is always "unknown", so it can never get a clean pass."""
    if confirmed_markets is not None and (exchange or "") not in confirmed_markets:
        return f"halt status unknown ({exchange or 'unknown exchange'}: feed coverage not confirmed)"
    if not feed:
        return "halt status unknown (feed not fetched)"
    if not feed.get("ok"):
        return f"halt status unknown (feed failed: {feed.get('error')})"
    if datetime.fromisoformat(feed["fetched_at"]).astimezone(ET).date() > day:
        return "halt status unknown (historical run: the feed only holds current halts)"
    for h in feed["items"]:
        if h.get("IssueSymbol", "").upper() != sym.upper():
            continue
        start = _dt(h.get("HaltDate", ""), h.get("HaltTime", ""))
        resume = _dt(h.get("ResumptionDate", ""), h.get("ResumptionTradeTime", ""))
        if start and start <= as_of and (resume is None or resume > as_of):
            return f"halted at {start.strftime('%m-%d %H:%M:%S')} ET (reason {h.get('ReasonCode') or '?'})"
    return None
