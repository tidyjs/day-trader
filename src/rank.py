"""M4: ranking, provisional levels and sizing (SPEC 4.4, 4.5). Deterministic;
the classifier's catalyst quality is one numeric input to the score.

Score (0-100) = 100 x sum(weight x part), weights in config `ranking`:
  gap       min(gap % / gap_full_pct, 1)
  volume    prior-day volume multiple on a log scale: 1x -> 0, volume_full_multiple -> 1
  catalyst  quality / 5 (0 when there is no classifier output)
  float     1 - float / float_max, clipped to 0..1; unknown float -> float_unknown_score
Ties: higher premarket dollar volume.

Levels are PROVISIONAL at the 09:15 scan, because SPEC 4.5's opening 5-minute
range does not exist until 09:35:
  trigger  high of the last 60 premarket minutes + 1 tick (M6's reference trade
           uses the 08:30-09:29 high combined with the opening 5-minute high)
  stop     1 tick under the most recent premarket higher low (a pivot low above
           the pivot low before it, below the trigger); if there is none, under
           the lowest low of the last `fallback_low_minutes` premarket minutes
  target   trigger + 1.5 x (trigger - stop)
  skip     if the stop is more than max_stop_pct below the trigger

Sizing, for every risk profile in config: shares = equity x risk_per_trade /
(trigger - stop), floored to share_decimals, capped so the position is at most
max_position_pct x equity. A profile with a blank value is "not set".
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from src.timeutil import ET, at_et, bar_complete_before, parse_ts

AT_OPEN_RULE = ("At 09:35 ET, recompute before entering: trigger = the higher of this premarket high and the 09:30-09:35 high; "
                "stop = under the 09:30-09:35 low or the most recent higher low; skip if the price is already more than "
                "{chase:g}% above the trigger, or the stop is more than {max_stop:g}% below the entry. Limit orders only; "
                "place the stop order right after the fill. Flat by 15:30 ET.")


# --------------------------------------------------------------------- score


def score(r: dict, cfg: dict) -> Tuple[float, Dict[str, float]]:
    rc, w = cfg["ranking"], cfg["ranking"]["weights"]
    gap = min(max(float(r["gap_pct"]), 0) / rc["gap_full_pct"], 1.0)
    mult = r.get("prior_day_volume_multiple")
    vol = 0.0 if not mult or mult <= 1 else min(math.log(mult) / math.log(rc["volume_full_multiple"]), 1.0)
    q = r.get("catalyst_quality")
    cat = (q / 5) if isinstance(q, (int, float)) else 0.0
    fl = r.get("float_shares")
    flt = rc["float_unknown_score"] if not fl else min(max(1 - fl / cfg["filters"]["float_max"], 0.0), 1.0)
    parts = {"gap": round(gap, 4), "volume": round(vol, 4), "catalyst": round(cat, 4), "float": round(flt, 4)}
    total = round(100 * sum(w[k] * parts[k] for k in parts), 2)
    return total, parts


# --------------------------------------------------------------------- levels


def _round_up(x: float, tick: float) -> float:
    return round(math.ceil(round(x / tick, 6)) * tick, 4)


def _round_down(x: float, tick: float) -> float:
    return round(math.floor(round(x / tick, 6)) * tick, 4)


def pivot_lows(bars: List[dict], k: int) -> List[Tuple[int, float]]:
    """(index, low) of bars whose low is below the k bars on each side."""
    out = []
    for i in range(k, len(bars) - k):
        lo = bars[i]["l"]
        if all(lo < bars[j]["l"] for j in range(i - k, i)) and all(lo < bars[j]["l"] for j in range(i + 1, i + k + 1)):
            out.append((i, lo))
    return out


def provisional_levels(bars: List[dict], start: datetime, cutoff: datetime, cfg: dict) -> Dict[str, Any]:
    lc = cfg["levels"]
    tick = lc["tick"]
    use = sorted((b for b in bars if parse_ts(b["t"]) >= start and bar_complete_before(b["t"], cutoff)), key=lambda b: b["t"])
    if not use:
        return {"levels_status": "skip: no premarket bars"}
    # Trigger basis: the high of the last `trigger_lookback_minutes` before the cutoff, not the
    # full-session premarket high (pre-declared 2026-11-16, SPEC 4.5; CRMN 11-12 spiked to 10.84 at 04:41).
    recent = [b for b in use if parse_ts(b["t"]) >= cutoff - timedelta(minutes=lc["trigger_lookback_minutes"])] or use[-1:]
    pm_high = max(b["h"] for b in recent)
    trigger = _round_up(pm_high + tick, tick)
    piv = pivot_lows(use, lc["pivot_bars"])
    stop_low, basis = None, ""
    for n in range(len(piv) - 1, 0, -1):  # most recent first
        (i, lo), (_, prev) = piv[n], piv[n - 1]
        if lo > prev and lo < trigger:
            stop_low = lo
            basis = f"higher low {lo:g} at {parse_ts(use[i]['t']).astimezone(ET):%H:%M}"
            break
    if stop_low is None:
        tail = use[-lc["fallback_low_minutes"]:]
        stop_low = min(b["l"] for b in tail)
        basis = f"lowest low of the last {len(tail)} premarket minutes ({stop_low:g}); no higher low found"
    stop = _round_down(stop_low - tick, tick)
    risk = round(trigger - stop, 4)
    out = {"pm_high_used": pm_high, "trigger": trigger, "stop": stop, "stop_basis": basis, "risk_per_share": risk}
    if risk <= 0:
        out["levels_status"] = "skip: stop is not below the trigger"
        return out
    out["stop_pct"] = round(100 * risk / trigger, 2)
    out["target_1_5r"] = round(trigger + lc["target_r"] * risk, 4)
    out["levels_status"] = (f"skip: stop {out['stop_pct']:.1f}% below the trigger (max {lc['max_stop_pct']:g}%)"
                            if out["stop_pct"] > lc["max_stop_pct"] else "ok")
    return out


# --------------------------------------------------------------------- sizing


def size(trigger: float, stop: float, profile: Optional[dict], equity: float, decimals: int) -> Dict[str, Any]:
    keys = ("risk_per_trade", "daily_loss_cap", "max_consecutive_losses", "max_position_pct")
    if not profile or any(profile.get(k) is None for k in keys):
        return {"note": "profile not set"}
    risk = trigger - stop
    if risk <= 0:
        return {"note": "no valid stop"}
    q = 10 ** decimals
    floor = lambda x: math.floor(round(x * q, 6)) / q  # noqa: E731
    risk_usd = equity * profile["risk_per_trade"]
    by_risk = floor(risk_usd / risk)
    by_cap = floor(equity * profile["max_position_pct"] / trigger)
    shares = min(by_risk, by_cap)
    note = "capped by position limit" if by_cap < by_risk else "sized by risk"
    if shares <= 0:
        return {"shares": 0.0, "position_usd": 0.0, "risk_usd": 0.0, "note": "rounds to 0 shares"}
    return {"shares": shares, "position_usd": round(shares * trigger, 2), "risk_usd": round(shares * risk, 2),
            "risk_pct_equity": round(100 * shares * risk / equity, 2), "note": note}


# --------------------------------------------------------------------- apply to a scan


def apply(cands: List[dict], inp: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    """Score, levels and sizing for Tier A and Tier B names, and the shortlist
    order (Tier A first, then Tier B, at most max_shortlist). In place."""
    day = datetime.fromisoformat(inp["data_cutoff_et"]).date()
    start = at_et(day, cfg["schedule"]["premarket_start"])
    cutoff = datetime.fromisoformat(inp["data_cutoff_et"])
    acct = cfg["account"]
    profiles = cfg.get("risk_profiles", {})
    for r in cands:
        r["score"], r["shortlist_rank"] = None, None
        if not r.get("tier"):
            continue
        r["score"], parts = score(r, cfg)
        r["score_parts"] = " ".join(f"{k}={v}" for k, v in parts.items())
        lv = provisional_levels(inp["premarket_bars"].get(r["symbol"], []), start, cutoff, cfg)
        r.update(lv)
        for name in profiles:
            sz = size(lv.get("trigger", 0), lv.get("stop", 0), profiles[name], acct["equity_usd"], acct["share_decimals"]) \
                if lv.get("levels_status") == "ok" else {"note": lv.get("levels_status", "")}
            r[f"shares_{name}"] = sz.get("shares")
            r[f"position_usd_{name}"] = sz.get("position_usd")
            r[f"risk_usd_{name}"] = sz.get("risk_usd")
            r[f"size_note_{name}"] = sz.get("note", "")
    # Ranked by score only within each tier (2026-11-16): levels never gate the list.
    # They are kept for M6's background reference trade and never appear in messages.
    ranked = sorted((r for r in cands if r.get("tier")),
                    key=lambda r: (0 if r["tier"] == "A" else 1, -(r["score"] or 0), -r["pm_dollar_volume"], r["symbol"]))
    for i, r in enumerate(ranked[: acct["max_shortlist"]], 1):
        r["shortlist_rank"] = i
