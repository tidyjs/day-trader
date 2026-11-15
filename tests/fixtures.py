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


def daily(day: str, c: float, v: int = 1_000_000, h=None, l=None) -> dict:
    t = datetime.fromisoformat(f"{day}T00:00").replace(tzinfo=ET)
    return {"t": to_utc_z(t), "o": c, "h": h if h is not None else c, "l": l if l is not None else c, "c": c, "v": v}


def flat_history(n: int = 25, c: float = 1.0, v: int = 1_000_000, last_day: str = "2026-11-12") -> list:
    """n flat sessions ending on last_day (weekdays only, holidays ignored)."""
    out, d = [], datetime.fromisoformat(last_day)
    while len(out) < n:
        if d.weekday() < 5:
            out.append(daily(d.date().isoformat(), c, v))
        d -= timedelta(days=1)
    return out[::-1]


def filing(form: str, filed: str, items: str = "", cover: str = "", hits=(), text=True, error=None) -> dict:
    f = {"form": form, "filed": filed, "accepted": f"{filed}T12:00:00.000Z", "accession": "0000000000-26-000001", "doc": "d.htm", "items": items}
    if error:
        f["text_error"] = error
    elif text:
        f["text"] = {"cover": cover, "hits": list(hits), "chars": len(cover)}
    return f


def make_inputs(prior_close: dict, bars: dict, t212=("GAPR",), names=None, as_of="09:15", t212_as_of=DAY, fetched_at=None,
                history=None, edgar=None, quotes=None, yahoo=None, halts=None) -> dict:
    as_of_dt = datetime.fromisoformat(f"{DAY}T{as_of}").replace(tzinfo=ET)
    cutoff = (as_of_dt - timedelta(minutes=CFG["schedule"]["sip_delay_minutes"])).replace(second=0)
    syms = sorted(set(prior_close) | set(bars))
    return copy.deepcopy(
        {
            "schema": 3,
            "day": DAY,
            "as_of_et": as_of_dt.isoformat(),
            "data_cutoff_et": cutoff.isoformat(),
            "prior_day": "2026-11-12",
            "universe": {"source": "fixture", "fetched_at": fetched_at or as_of_dt.isoformat(), "symbols": {s: (names or {}).get(s, f"{s} Inc. Common Stock") for s in syms}},
            "prior_close": prior_close,
            "premarket_bars": bars,
            "t212": {"path": "fixture", "as_of": t212_as_of, "sha256": "x", "refresh_error": None, "symbols": list(t212)},
            "history": history or {},
            "edgar": edgar or {},
            "quotes": quotes or {},
            "yahoo": yahoo or {},
            "halts": halts if halts is not None else {"fetched_at": as_of_dt.isoformat(), "ok": True, "items": [], "error": None, "markets": []},
        }
    )
