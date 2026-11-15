"""Shared helpers for Milestone 0 verification scripts.

These are throwaway probes, not scanner code. They read secrets from the
environment (or a git-ignored .env file in the repo root) and write raw
outputs to docs/m0_raw/ so every result in docs/m0_results.md is traceable.
"""
from __future__ import annotations

import json
import os
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "docs" / "m0_raw"
ET = ZoneInfo("America/New_York")
UTC = timezone.utc

DATA_URL = "https://data.alpaca.markets"
# Paper and live keys both work for market data; the asset/calendar endpoints
# live on the trading API host. Paper is the safe default.
TRADING_URL = os.environ.get("ALPACA_TRADING_URL", "https://paper-api.alpaca.markets")


def load_env() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env()


def need(*names: str) -> None:
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        raise SystemExit(f"Missing env vars: {', '.join(missing)} (set them in .env)")


def save_raw(name: str, obj: Any) -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    p = RAW / f"{name}.json"
    p.write_text(json.dumps(obj, indent=2, default=str))
    return p


def load_raw(name: str) -> Optional[Any]:
    p = RAW / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def now_et() -> datetime:
    return datetime.now(tz=ET)


def et(d: date, hh: int, mm: int = 0) -> datetime:
    return datetime(d.year, d.month, d.day, hh, mm, tzinfo=ET)


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def chunks(xs: List[str], n: int) -> Iterable[List[str]]:
    for i in range(0, len(xs), n):
        yield xs[i : i + n]


# ---------------------------------------------------------------- Alpaca


class Alpaca:
    """Minimal Alpaca client that records rate-limit headers it sees."""

    def __init__(self) -> None:
        need("ALPACA_KEY_ID", "ALPACA_SECRET_KEY")
        self.s = requests.Session()
        self.s.headers.update(
            {
                "APCA-API-KEY-ID": os.environ["ALPACA_KEY_ID"],
                "APCA-API-SECRET-KEY": os.environ["ALPACA_SECRET_KEY"],
                "Accept": "application/json",
            }
        )
        self.last_headers: Dict[str, str] = {}
        self.calls = 0

    def get(self, url: str, params: Optional[dict] = None, ok=(200,)) -> requests.Response:
        for attempt in range(5):
            r = self.s.get(url, params=params, timeout=30)
            self.calls += 1
            self.last_headers = {k.lower(): v for k, v in r.headers.items() if k.lower().startswith("x-ratelimit")}
            if r.status_code == 429:
                reset = int(r.headers.get("X-RateLimit-Reset", "0") or 0)
                wait = max(1, reset - int(time.time())) if reset else 2 ** attempt
                time.sleep(min(wait, 60))
                continue
            if r.status_code not in ok:
                return r
            remaining = int(self.last_headers.get("x-ratelimit-remaining", "999") or 999)
            if remaining < 5:
                time.sleep(3)
            return r
        return r

    # Trading API
    def assets(self) -> List[dict]:
        r = self.get(f"{TRADING_URL}/v2/assets", {"status": "active", "asset_class": "us_equity"})
        r.raise_for_status()
        return r.json()

    def calendar(self, start: date, end: date) -> List[dict]:
        r = self.get(f"{TRADING_URL}/v2/calendar", {"start": start.isoformat(), "end": end.isoformat()})
        r.raise_for_status()
        return r.json()

    # Market data
    def snapshots(self, symbols: List[str], feed: str = "iex") -> Dict[str, dict]:
        out: Dict[str, dict] = {}
        for batch in chunks(symbols, 200):
            r = self.get(f"{DATA_URL}/v2/stocks/snapshots", {"symbols": ",".join(batch), "feed": feed})
            r.raise_for_status()
            out.update(r.json())
        return out

    def bars(
        self,
        symbols: List[str],
        timeframe: str,
        start: datetime,
        end: datetime,
        feed: str = "sip",
        batch: int = 200,
    ) -> Dict[str, List[dict]]:
        """Multi-symbol bars with pagination. Raises with the API message on error."""
        out: Dict[str, List[dict]] = {}
        for syms in chunks(symbols, batch):
            token = None
            while True:
                params = {
                    "symbols": ",".join(syms),
                    "timeframe": timeframe,
                    "start": iso(start),
                    "end": iso(end),
                    "feed": feed,
                    "limit": 10000,
                    "adjustment": "raw",
                }
                if token:
                    params["page_token"] = token
                r = self.get(f"{DATA_URL}/v2/stocks/bars", params)
                if r.status_code != 200:
                    raise AlpacaError(r.status_code, r.text)
                j = r.json()
                for sym, bs in (j.get("bars") or {}).items():
                    out.setdefault(sym, []).extend(bs)
                token = j.get("next_page_token")
                if not token:
                    break
        return out

    def news(self, symbols: List[str], start: datetime, end: datetime, limit: int = 50) -> List[dict]:
        out: List[dict] = []
        token = None
        while True:
            params = {
                "symbols": ",".join(symbols),
                "start": iso(start),
                "end": iso(end),
                "limit": limit,
                "include_content": "false",
                "sort": "desc",
            }
            if token:
                params["page_token"] = token
            r = self.get(f"{DATA_URL}/v1beta1/news", params)
            if r.status_code != 200:
                raise AlpacaError(r.status_code, r.text)
            j = r.json()
            out.extend(j.get("news", []))
            token = j.get("next_page_token")
            if not token or len(out) >= 500:
                return out


class AlpacaError(Exception):
    def __init__(self, status: int, body: str):
        super().__init__(f"HTTP {status}: {body[:300]}")
        self.status = status
        self.body = body


LISTED_EXCHANGES = {"NYSE", "NASDAQ", "AMEX", "ARCA", "BATS"}
NON_COMMON_WORDS = ("warrant", "unit", " right", "etf", "etn", "fund", "trust", "preferred", "depositary share", "notes")


def common_stock_universe(assets: List[dict]) -> List[dict]:
    """Heuristic US-listed common stock filter. Alpaca has no clean
    'common stock' flag, so this is approximate and recorded as such."""
    keep = []
    for a in assets:
        if a.get("exchange") not in LISTED_EXCHANGES or not a.get("tradable"):
            continue
        sym = a["symbol"]
        name = (a.get("name") or "").lower()
        if "." in sym or "/" in sym:
            continue
        if any(w in name for w in NON_COMMON_WORDS) and "common" not in name and "ordinary" not in name:
            continue
        keep.append(a)
    return keep


def recent_trading_days(alp: Alpaca, n: int, before: Optional[date] = None) -> List[date]:
    """Last n completed trading days strictly before `before` (default: today ET)."""
    before = before or now_et().date()
    cal = alp.calendar(before - timedelta(days=n * 3 + 10), before - timedelta(days=1))
    days = [date.fromisoformat(c["date"]) for c in cal]
    return days[-n:]


# ---------------------------------------------------------------- SEC


def sec_session() -> requests.Session:
    ua = os.environ.get("SEC_USER_AGENT")
    if not ua:
        raise SystemExit("Set SEC_USER_AGENT, e.g. 'DayTraderResearch you@example.com'")
    s = requests.Session()
    s.headers.update({"User-Agent": ua, "Accept-Encoding": "gzip, deflate"})
    return s


_last_sec = [0.0]


def sec_get(s: requests.Session, url: str) -> requests.Response:
    # Stay well under the 10 req/s limit.
    gap = time.time() - _last_sec[0]
    if gap < 0.15:
        time.sleep(0.15 - gap)
    _last_sec[0] = time.time()
    return s.get(url, timeout=30)


def md_table(rows: List[dict], cols: List[str]) -> str:
    head = "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n"
    body = "".join("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |\n" for r in rows)
    return head + body
