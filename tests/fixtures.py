"""Synthetic scan inputs. Times are ET; 2026-11-13 is EST (UTC-5)."""
from __future__ import annotations

import copy
from datetime import datetime, timedelta

from src.config import load_config
from src.timeutil import ET, to_utc_z

DAY = "2026-11-13"
CFG = load_config()


def bar(hhmm: str, c: float, v: int = 10_000, n: int = 50, h=None, vw=None, day: str = DAY) -> dict:
    t = datetime.fromisoformat(f"{day}T{hhmm}").replace(tzinfo=ET)
    return {"t": to_utc_z(t), "o": c, "h": h or c, "l": c, "c": c, "v": v, "n": n, "vw": vw or c}


def make_inputs(prior_close: dict, bars: dict, t212=("GAPR",), names=None, as_of="09:15", t212_as_of=DAY, fetched_at=None) -> dict:
    as_of_dt = datetime.fromisoformat(f"{DAY}T{as_of}").replace(tzinfo=ET)
    cutoff = (as_of_dt - timedelta(minutes=CFG["schedule"]["sip_delay_minutes"])).replace(second=0)
    syms = sorted(set(prior_close) | set(bars))
    return copy.deepcopy(
        {
            "schema": 1,
            "day": DAY,
            "as_of_et": as_of_dt.isoformat(),
            "data_cutoff_et": cutoff.isoformat(),
            "prior_day": "2026-11-12",
            "universe": {"source": "fixture", "fetched_at": fetched_at or as_of_dt.isoformat(), "symbols": {s: (names or {}).get(s, f"{s} Inc. Common Stock") for s in syms}},
            "prior_close": prior_close,
            "premarket_bars": bars,
            "t212": {"path": "fixture", "as_of": t212_as_of, "sha256": "x", "refresh_error": None, "symbols": list(t212)},
        }
    )
