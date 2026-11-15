"""Yahoo float (approximate, unofficial). Called only for names that survive
every cheaper rule, one at a time with a pause, never in a tight loop."""
from __future__ import annotations

import time
from datetime import datetime
from typing import Dict, List

FIELDS = ("floatShares", "sharesOutstanding", "impliedSharesOutstanding")


def gather(symbols: List[str], now: datetime, pause_s: float = 1.5) -> Dict[str, dict]:
    import yfinance as yf  # imported lazily: slow, and only needed here

    out: Dict[str, dict] = {}
    for i, sym in enumerate(symbols):
        if i:
            time.sleep(pause_s)
        rec = {"fetched_at": now.isoformat()}
        try:
            info = yf.Ticker(sym).get_info() or {}
            rec.update({k: info.get(k) for k in FIELDS})
        except Exception as e:
            rec["error"] = f"{type(e).__name__}: {str(e)[:120]}"
        out[sym] = rec
    return out
