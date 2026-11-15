"""Trading 212 tradable list.

Only the read-only `/api/v0/equity/metadata/instruments` endpoint is called.
Symbols come from `shortName` (the current exchange symbol). T212's internal
`ticker` keeps old symbols after renames, e.g. CRMN is stored as SKBL_US_EQ.

Each day's list is saved as data/t212/YYYY-MM-DD.json (sorted symbols plus a
hash) so every scan can record exactly which list it used. If the refresh
fails, the newest saved list is used and the scan gets an age warning.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, List, Optional, Set

import requests

ENDPOINT = "/api/v0/equity/metadata/instruments"


def norm(sym: str) -> str:
    """Compare symbols without punctuation: BRK.B, BRK_B and BRKB match."""
    return re.sub(r"[^A-Z0-9]", "", sym.upper())


def us_stock_symbols(instruments: Iterable[dict]) -> List[str]:
    out = set()
    for x in instruments:
        t = x.get("ticker", "")
        if not t.endswith("_US_EQ") or t.endswith("WAR_US_EQ"):
            continue
        if x.get("type") != "STOCK" or x.get("currencyCode") != "USD":
            continue
        sym = x.get("shortName") or t[: -len("_US_EQ")]
        out.add(sym.upper())
    return sorted(out)


@dataclass
class T212List:
    symbols: List[str]
    as_of: date          # date the list was downloaded
    path: str            # file the scan used, relative to repo root
    sha256: str
    age_days: int = 0
    refresh_error: Optional[str] = None

    def contains(self, sym: str) -> bool:
        return norm(sym) in self._normed

    def __post_init__(self) -> None:
        self._normed: Set[str] = {norm(s) for s in self.symbols}


def _digest(symbols: List[str]) -> str:
    return hashlib.sha256("\n".join(symbols).encode()).hexdigest()


def save(symbols: List[str], d: date, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / f"{d.isoformat()}.json"
    p.write_text(json.dumps({"as_of": d.isoformat(), "count": len(symbols), "sha256": _digest(symbols), "symbols": symbols}, indent=0))
    return p


def load_file(p: Path, root: Path, today: Optional[date] = None) -> T212List:
    j = json.loads(p.read_text())
    d = date.fromisoformat(j["as_of"])
    syms = j["symbols"]
    return T212List(syms, d, str(p.relative_to(root)), _digest(syms), ((today or d) - d).days)


def latest_saved(folder: Path) -> Optional[Path]:
    files = sorted(folder.glob("????-??-??.json"))
    return files[-1] if files else None


def fetch(base_url: str, key: str, secret: Optional[str]) -> List[dict]:
    """Key + secret use basic auth (current T212 keys); a key alone goes in the header."""
    url = base_url.rstrip("/") + ENDPOINT
    kw = {"auth": (key, secret)} if secret else {"headers": {"Authorization": key}}
    r = requests.get(url, timeout=60, **kw)
    if r.status_code != 200:
        raise RuntimeError(f"T212 HTTP {r.status_code}")
    return r.json()


def get_list(today: date, folder: Path, root: Path, base_url: str, refresh: bool = True) -> T212List:
    """Today's list if saved; else refresh from T212; else newest saved list.

    Raises only if there is no list at all.
    """
    todays = folder / f"{today.isoformat()}.json"
    if todays.exists():
        return load_file(todays, root, today)
    err = None
    key = os.environ.get("T212_API_KEY")
    if refresh and key:
        try:
            syms = us_stock_symbols(fetch(base_url, key, os.environ.get("T212_API_SECRET")))
            if len(syms) < 1000:  # sanity: M0 saw ~6,900 US stocks
                raise RuntimeError(f"T212 list suspiciously small ({len(syms)})")
            return load_file(save(syms, today, folder), root, today)
        except Exception as e:  # fall back to the newest saved list
            err = f"{type(e).__name__}: {e}"
    elif refresh:
        err = "T212_API_KEY not set"
    p = latest_saved(folder)
    if not p:
        raise RuntimeError(f"No T212 list available ({err})")
    lst = load_file(p, root, today)
    lst.refresh_error = err
    return lst
