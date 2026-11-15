"""SEC EDGAR: ticker -> CIK, shares outstanding, recent filings, filing text.

The User-Agent must contain an email address (M0: 403 without one); it comes
from SEC_USER_AGENT. Requests are spaced to stay under 10/second.

Only what the rules need is saved in the scan file: CIK, recent filing
metadata, shares-outstanding points, and short text excerpts around keyword
hits plus each document's cover. That keeps replays reproducible without
storing whole prospectuses.

`acceptanceDateTime` in the submissions JSON is true UTC (checked against the
filing index pages in M2), so filings are compared against the scan time.
"""
from __future__ import annotations

import html
import json
import os
import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import requests

from src.timeutil import UTC

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
DOC_URL = "https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc}/{doc}"

OFFERING_FORMS = ("424B", "S-1", "S-3", "F-1", "F-3")
CURRENT_REPORTS = ("8-K", "6-K")
PROXY_FORMS = ("DEF 14A", "PRE 14A", "DEF 14C", "PRE 14C")

# Excerpts are cut around anything the rules test, built from the rules' own
# patterns so a rule can never look for wording the excerpts dropped.
def _keywords() -> "re.Pattern":
    from src import rules as R
    return re.compile("|".join(f"(?:{p.pattern})" for p in (R.EQUITY, R.OFFER, R.ISSUANCE, R.RESALE, R.UPDATE, R.SHELF, R.RSPLIT)), re.I)


KEYWORDS = _keywords()


def html_to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()


def excerpts(text: str, cover_chars: int, window: int, max_hits: int = 40) -> Dict[str, object]:
    """Document cover plus merged windows of +/- `window` chars around keywords."""
    spans: List[List[int]] = []
    for m in KEYWORDS.finditer(text):
        s, e = max(0, m.start() - window), min(len(text), m.end() + window)
        if spans and s <= spans[-1][1]:
            spans[-1][1] = e
        elif len(spans) < max_hits:
            spans.append([s, e])
        else:
            break
    return {"cover": text[:cover_chars], "hits": [text[s:e] for s, e in spans], "chars": len(text)}


class Edgar:
    def __init__(self, user_agent: Optional[str] = None, min_interval: float = 0.15):
        ua = user_agent or os.environ.get("SEC_USER_AGENT", "")
        if "@" not in ua:
            raise RuntimeError("SEC_USER_AGENT must contain a contact email (SEC returns 403 otherwise)")
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": ua, "Accept-Encoding": "gzip, deflate"})
        self.min_interval = min_interval
        self._last = 0.0
        self.calls = 0

    def _get(self, url: str, stream: bool = False) -> requests.Response:
        for attempt in range(4):
            gap = time.time() - self._last
            if gap < self.min_interval:
                time.sleep(self.min_interval - gap)
            self._last = time.time()
            r = self.s.get(url, timeout=30, stream=stream)
            self.calls += 1
            if r.status_code in (429, 503):
                time.sleep(2 ** attempt)
                continue
            return r
        return r

    def ticker_map(self, cache_dir: Path, today: date) -> Dict[str, int]:
        cache_dir.mkdir(parents=True, exist_ok=True)
        p = cache_dir / f"company_tickers_{today.isoformat()}.json"
        if p.exists():
            data = json.loads(p.read_text())
        else:
            r = self._get(TICKERS_URL)
            r.raise_for_status()
            data = r.json()
            p.write_text(json.dumps(data))
        return {v["ticker"].upper(): int(v["cik_str"]) for v in data.values()}

    def submissions(self, cik: int) -> dict:
        r = self._get(SUBMISSIONS_URL.format(cik=f"{cik:010d}"))
        r.raise_for_status()
        return r.json()

    def shares_points(self, cik: int, keep: int = 8) -> List[dict]:
        r = self._get(FACTS_URL.format(cik=f"{cik:010d}"))
        if r.status_code == 404:
            return []
        r.raise_for_status()
        try:
            pts = r.json()["facts"]["dei"]["EntityCommonStockSharesOutstanding"]["units"]["shares"]
        except KeyError:
            return []
        pts = sorted(pts, key=lambda p: (p.get("filed", ""), p.get("end", "")))
        return [{"val": p["val"], "end": p.get("end"), "filed": p.get("filed"), "form": p.get("form")} for p in pts[-keep:]]

    def doc_text(self, cik: int, accession: str, doc: str, max_bytes: int) -> str:
        url = DOC_URL.format(cik_int=cik, acc=accession.replace("-", ""), doc=doc)
        r = self._get(url, stream=True)
        r.raise_for_status()
        buf = b""
        for chunk in r.iter_content(65536):
            buf += chunk
            if len(buf) >= max_bytes:
                break
        r.close()
        return html_to_text(buf.decode(r.encoding or "utf-8", errors="ignore"))


def recent_filings(sub: dict, as_of: datetime, since: date) -> List[dict]:
    """Filings accepted at or before `as_of` and filed on or after `since`."""
    rec = sub.get("filings", {}).get("recent", {})
    cik = int(sub.get("cik", 0) or 0)
    out = []
    for i, form in enumerate(rec.get("form", [])):
        acc_t = datetime.fromisoformat(rec["acceptanceDateTime"][i].replace("Z", "+00:00"))
        filed = date.fromisoformat(rec["filingDate"][i])
        if acc_t > as_of.astimezone(UTC) or filed < since:
            continue
        out.append(
            {
                "form": form,
                "filed": rec["filingDate"][i],
                "accepted": rec["acceptanceDateTime"][i],
                "accession": rec["accessionNumber"][i],
                "doc": rec["primaryDocument"][i],
                "items": rec.get("items", [""] * len(rec["form"]))[i] or "",
                "desc": rec.get("primaryDocDescription", [""] * len(rec["form"]))[i] or "",
                "file_number": rec.get("fileNumber", [""] * len(rec["form"]))[i] or "",
                "url": DOC_URL.format(cik_int=cik, acc=rec["accessionNumber"][i].replace("-", ""), doc=rec["primaryDocument"][i]) if cik else "",
            }
        )
    return out


BASE_FORMS = ("424B", "S-1", "F-1", "S-3", "F-3")


def find_base(sub: dict, f: dict, as_of: datetime) -> Optional[dict]:
    """For a prospectus supplement, the registration it supplements: the earliest
    final prospectus (424B*) with the same file number, else the earliest
    S-1/F-1/S-3/F-3, accepted before as_of."""
    fn = f.get("file_number")
    if not fn:
        return None
    rec = sub.get("filings", {}).get("recent", {})
    cik = int(sub.get("cik", 0) or 0)
    found = []
    for i, form in enumerate(rec.get("form", [])):
        if rec.get("fileNumber", [""] * len(rec["form"]))[i] != fn or rec["accessionNumber"][i] == f["accession"]:
            continue
        if not form.upper().startswith(BASE_FORMS):
            continue
        acc_t = datetime.fromisoformat(rec["acceptanceDateTime"][i].replace("Z", "+00:00"))
        if acc_t > as_of.astimezone(UTC):
            continue
        found.append((0 if form.upper().startswith("424B") else 1, rec["filingDate"][i], i))
    if not found:
        return None
    # The final prospectus (424B*) is the operative document; fall back to the
    # registration statement only if no 424B exists. Earliest within that kind.
    _, _, i = min(found, key=lambda x: (x[0], x[1]))
    return {
        "form": rec["form"][i], "filed": rec["filingDate"][i], "accession": rec["accessionNumber"][i],
        "doc": rec["primaryDocument"][i],
        "url": DOC_URL.format(cik_int=cik, acc=rec["accessionNumber"][i].replace("-", ""), doc=rec["primaryDocument"][i]),
    }


def wants_text(f: dict, day: date, cfg: dict) -> Optional[str]:
    """Why this filing's text is needed, or None."""
    filed = date.fromisoformat(f["filed"])
    form = f["form"].upper()
    if filed >= day - timedelta(days=cfg["offering_lookback_days"]):
        if form.startswith(OFFERING_FORMS) or form.startswith(CURRENT_REPORTS):
            return "offering"
    if filed >= day - timedelta(days=cfg["reverse_split_lookback_days"]):
        if form.startswith(CURRENT_REPORTS) or form in PROXY_FORMS:
            return "reverse_split"
    return None


def gather(ed: Edgar, symbols: List[str], day: date, as_of: datetime, cfg: dict, cache_dir: Path, today: date) -> Dict[str, dict]:
    """EDGAR inputs per symbol, ready to save in the scan file."""
    tmap = ed.ticker_map(cache_dir, today)
    since = day - timedelta(days=max(cfg["deficiency_lookback_days"], cfg["reverse_split_lookback_days"]))
    out: Dict[str, dict] = {}
    for sym in symbols:
        cik = tmap.get(sym.upper())
        if cik is None:
            out[sym] = {"cik": None}
            continue
        rec: dict = {"cik": cik, "filings": [], "shares_points": [], "errors": []}
        sub = {}
        try:
            sub = ed.submissions(cik)
            fl = recent_filings(sub, as_of, since)
        except Exception as e:
            rec["errors"].append(f"submissions: {type(e).__name__}: {e}")
            fl = []
        try:
            rec["shares_points"] = ed.shares_points(cik)
        except Exception as e:
            rec["errors"].append(f"companyfacts: {type(e).__name__}: {e}")
        # Offering-window documents first, then reverse-split ones; newest first in each.
        need = [f for f in fl if wants_text(f, day, cfg)]
        need = sorted((f for f in need if wants_text(f, day, cfg) == "offering"), key=lambda f: f["accepted"], reverse=True) + sorted(
            (f for f in need if wants_text(f, day, cfg) == "reverse_split"), key=lambda f: f["accepted"], reverse=True
        )
        for f in need[: cfg["max_docs_per_name"]]:
            try:
                txt = ed.doc_text(cik, f["accession"], f["doc"], cfg["doc_max_bytes"])
                f["text"] = excerpts(txt, cfg["cover_chars"], cfg["excerpt_chars"])
            except Exception as e:
                f["text_error"] = f"{type(e).__name__}: {e}"
                continue
            # A supplement that only attaches a report: read the registration it supplements.
            from src import rules as R
            if f["form"].upper().startswith("424B") and any(R.UPDATE.search(h) for h in [f["text"]["cover"]] + f["text"]["hits"]):
                base = find_base(sub, f, as_of)
                if base:
                    try:
                        btxt = ed.doc_text(cik, base["accession"], base["doc"], cfg["doc_max_bytes"])
                        base["text"] = excerpts(btxt, cfg["cover_chars"], cfg["excerpt_chars"])
                    except Exception as e:
                        base["text_error"] = f"{type(e).__name__}: {e}"
                    f["base"] = base
        rec["docs_capped"] = max(0, len(need) - cfg["max_docs_per_name"])
        rec["filings"] = fl
        out[sym] = rec
    return out
