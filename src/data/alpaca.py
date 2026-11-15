"""Alpaca market data (free plan): assets, calendar, bars, snapshots, news.

Rate limit is 200 requests/min (confirmed in M0). Header names are
`X-Ratelimit-*`, so they are read case-insensitively.
"""
from __future__ import annotations

import os
import time
from datetime import date, datetime
from typing import Dict, Iterable, List, Optional

import requests

from src.timeutil import to_utc_z

DATA_URL = "https://data.alpaca.markets"
TRADING_URL_DEFAULT = "https://paper-api.alpaca.markets"


class AlpacaError(Exception):
    def __init__(self, status: int, body: str):
        super().__init__(f"Alpaca HTTP {status}: {body[:300]}")
        self.status = status
        self.body = body


def _chunks(xs: List[str], n: int) -> Iterable[List[str]]:
    for i in range(0, len(xs), n):
        yield xs[i : i + n]


class Alpaca:
    def __init__(self, key_id: Optional[str] = None, secret: Optional[str] = None, trading_url: Optional[str] = None):
        key_id = key_id or os.environ.get("ALPACA_KEY_ID")
        secret = secret or os.environ.get("ALPACA_SECRET_KEY")
        if not key_id or not secret:
            raise RuntimeError("ALPACA_KEY_ID and ALPACA_SECRET_KEY must be set")
        url = (trading_url or os.environ.get("ALPACA_TRADING_URL") or TRADING_URL_DEFAULT).rstrip("/")
        # Alpaca's dashboard shows the endpoint with /v2; paths here add it.
        self.trading_url = url[:-3] if url.endswith("/v2") else url
        self.s = requests.Session()
        self.s.headers.update({"APCA-API-KEY-ID": key_id, "APCA-API-SECRET-KEY": secret, "Accept": "application/json"})
        self.calls = 0

    def _get(self, url: str, params: Optional[dict] = None) -> dict:
        last = None
        for attempt in range(5):
            try:
                r = self.s.get(url, params=params, timeout=30)
            except requests.RequestException as e:
                last = e
                time.sleep(2 ** attempt)
                continue
            self.calls += 1
            if r.status_code == 429 or r.status_code >= 500:
                reset = r.headers.get("x-ratelimit-reset")
                wait = max(1, int(reset) - int(time.time())) if reset and reset.isdigit() else 2 ** attempt
                time.sleep(min(wait, 60))
                last = AlpacaError(r.status_code, r.text)
                continue
            if r.status_code != 200:
                raise AlpacaError(r.status_code, r.text)
            rem = r.headers.get("x-ratelimit-remaining")
            if rem and rem.isdigit() and int(rem) < 5:
                time.sleep(3)
            return r.json()
        raise last if isinstance(last, Exception) else RuntimeError("Alpaca request failed")

    def assets(self) -> List[dict]:
        return self._get(f"{self.trading_url}/v2/assets", {"status": "active", "asset_class": "us_equity"})

    def calendar(self, start: date, end: date) -> List[dict]:
        return self._get(f"{self.trading_url}/v2/calendar", {"start": start.isoformat(), "end": end.isoformat()})

    def bars(
        self,
        symbols: List[str],
        timeframe: str,
        start: datetime,
        end: datetime,
        feed: str = "sip",
        batch: int = 200,
    ) -> Dict[str, List[dict]]:
        out: Dict[str, List[dict]] = {}
        for syms in _chunks(sorted(symbols), batch):
            token = None
            while True:
                params = {
                    "symbols": ",".join(syms),
                    "timeframe": timeframe,
                    "start": to_utc_z(start),
                    "end": to_utc_z(end),
                    "feed": feed,
                    "limit": 10000,
                    "adjustment": "raw",
                }
                if token:
                    params["page_token"] = token
                j = self._get(f"{DATA_URL}/v2/stocks/bars", params)
                for sym, bs in (j.get("bars") or {}).items():
                    out.setdefault(sym, []).extend(bs)
                token = j.get("next_page_token")
                if not token:
                    break
        return out

    def quotes(self, symbols: List[str], start: datetime, end: datetime, feed: str = "sip", max_pages: int = 5) -> Dict[str, List[dict]]:
        """Historical quotes, one symbol at a time so a busy name can't starve
        the others. Capped at max_pages per symbol (pages run oldest first)."""
        out: Dict[str, List[dict]] = {}
        for sym in sorted(symbols):
            token, pages = None, 0
            while pages < max_pages:
                params = {"symbols": sym, "start": to_utc_z(start), "end": to_utc_z(end), "feed": feed, "limit": 10000}
                if token:
                    params["page_token"] = token
                j = self._get(f"{DATA_URL}/v2/stocks/quotes", params)
                out.setdefault(sym, []).extend((j.get("quotes") or {}).get(sym, []))
                token, pages = j.get("next_page_token"), pages + 1
                if not token:
                    break
        return out

    def news(self, symbols: List[str], start: datetime, end: datetime, limit: int = 50, max_items: int = 200) -> List[dict]:
        out: List[dict] = []
        token = None
        while len(out) < max_items:
            params = {"symbols": ",".join(symbols), "start": to_utc_z(start), "end": to_utc_z(end), "limit": limit, "sort": "desc", "include_content": "false"}
            if token:
                params["page_token"] = token
            j = self._get(f"{DATA_URL}/v1beta1/news", params)
            out.extend(j.get("news", []))
            token = j.get("next_page_token")
            if not token:
                break
        return out[:max_items]

    def snapshots(self, symbols: List[str], feed: str = "iex") -> Dict[str, dict]:
        out: Dict[str, dict] = {}
        for syms in _chunks(sorted(symbols), 200):
            out.update(self._get(f"{DATA_URL}/v2/stocks/snapshots", {"symbols": ",".join(syms), "feed": feed}))
        return out
