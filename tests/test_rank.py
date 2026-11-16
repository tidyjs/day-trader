"""M4 tests: score, provisional levels, sizing edge cases, shortlist order."""
from __future__ import annotations

from datetime import datetime

import pytest

from src import rank
from src.config import load_config
from src.timeutil import ET
from tests.fixtures import bar

CFG = load_config()
START = datetime(2026, 11, 13, 4, 0, tzinfo=ET)
CUT = datetime(2026, 11, 13, 8, 59, tzinfo=ET)
MEASURE = CFG["risk_profiles"]["measure"]


def b(hhmm, lo, hi=None):
    x = bar(hhmm, (lo + (hi or lo)) / 2)
    x["l"], x["h"] = lo, hi if hi is not None else lo + 0.02
    return x


# ------------------------------------------------------------ sizing edge cases (SPEC M4)


def test_size_by_risk():
    s = rank.size(1.20, 1.10, MEASURE, 50, 2)       # $2.50 risk / $0.10 = 25 shares, $30 position
    assert (s["shares"], s["position_usd"], s["risk_usd"], s["note"]) == (25.0, 30.0, 2.5, "sized by risk")


def test_size_capped_by_position_limit():
    s = rank.size(1.20, 1.18, MEASURE, 50, 2)       # risk says 125 shares ($150) but equity is $50
    assert s["shares"] == 41.66 and s["position_usd"] <= 50 and s["note"] == "capped by position limit"
    assert s["risk_usd"] == pytest.approx(0.83, abs=0.01)  # actual risk is below the 5% budget


def test_size_floors_fractional_shares():
    s = rank.size(1.33, 1.21, MEASURE, 50, 2)       # 2.5 / 0.12 = 20.8333 -> 20.83
    assert s["shares"] == 20.83


def test_challenge_profile_blank_is_not_set():
    assert rank.size(1.2, 1.1, CFG["risk_profiles"]["challenge"], 50, 2) == {"note": "profile not set"}
    assert rank.size(1.2, 1.1, None, 50, 2) == {"note": "profile not set"}


def test_size_needs_a_stop_below_trigger():
    assert rank.size(1.2, 1.2, MEASURE, 50, 2)["note"] == "no valid stop"


def test_tiny_equity_rounds_to_zero():
    assert rank.size(1.2, 1.1, MEASURE, 0.0001, 2)["note"] == "rounds to 0 shares"


# ------------------------------------------------------------ provisional levels


def test_trigger_is_premarket_high_plus_tick_and_stop_under_higher_low():
    # lows: 1.00, 1.05(pivot) ... a later higher pivot low at 1.08; high 1.20
    lows = [1.10, 1.07, 1.05, 1.07, 1.10, 1.12, 1.10, 1.08, 1.11, 1.13, 1.15]
    bars = [b(f"08:{40 + i:02d}", lo, 1.20 if i == 9 else None) for i, lo in enumerate(lows)]
    lv = rank.provisional_levels(bars, START, CUT, CFG)
    assert lv["trigger"] == 1.21 and lv["stop"] == 1.07 and "higher low 1.08" in lv["stop_basis"]
    assert lv["target_1_5r"] == pytest.approx(1.21 + 1.5 * 0.14) and lv["levels_status"] == "ok"


def test_no_higher_low_falls_back_to_recent_low():
    bars = [b(f"08:{30 + i:02d}", 1.30 - 0.01 * i) for i in range(20)]  # steady decline: no higher low
    lv = rank.provisional_levels(bars, START, CUT, CFG)
    assert "no higher low found" in lv["stop_basis"] and lv["stop"] == pytest.approx(1.10)


def test_stop_too_wide_is_a_skip():
    bars = [b("08:00", 1.00, 1.40), b("08:01", 1.10), b("08:02", 1.02), b("08:03", 1.10), b("08:04", 1.20)]
    lv = rank.provisional_levels(bars, START, CUT, CFG)
    assert lv["levels_status"].startswith("skip: stop") and lv["stop_pct"] > 12


def test_bars_after_cutoff_are_not_used_for_levels():
    bars = [b("08:30", 1.10, 1.20), b("08:59", 1.10, 5.00)]  # the 08:59 bar closes after the cutoff
    assert rank.provisional_levels(bars, START, CUT, CFG)["pm_high_used"] == 1.20


# ------------------------------------------------------------ score


def test_score_parts_and_unknown_float():
    r = {"gap_pct": 25.0, "prior_day_volume_multiple": 20.0, "catalyst_quality": 4, "float_shares": None}
    total, parts = rank.score(r, CFG)
    assert parts == {"gap": 0.5, "volume": 1.0, "catalyst": 0.8, "float": 0.0}
    assert total == pytest.approx(100 * (0.3 * 0.5 + 0.3 * 1.0 + 0.25 * 0.8))
    assert rank.score({**r, "float_shares": 10e6}, CFG)[1]["float"] == pytest.approx(0.8)
    assert rank.score({**r, "prior_day_volume_multiple": 0.5}, CFG)[1]["volume"] == 0.0


# ------------------------------------------------------------ shortlist order


def _row(sym, tier, score_inputs, pm=1000.0, low=1.10):
    r = {"symbol": sym, "tier": tier, "pm_dollar_volume": pm, **score_inputs}
    return r, [b(f"08:{40 + i:02d}", lo) for i, lo in enumerate([low + 0.05, low + 0.02, low, low + 0.02, low + 0.05, low + 0.08])]


def test_shortlist_tier_a_first_then_b_capped_at_five():
    good = {"gap_pct": 20.0, "prior_day_volume_multiple": 5.0, "catalyst_quality": 3, "float_shares": 5e6}
    best = {**good, "gap_pct": 45.0}
    rows, bars = [], {}
    for sym, tier, si, pm in [("B1", "B", best, 9e6), ("A1", "A", good, 1e3), ("A2", "A", good, 5e3), ("B2", "B", good, 1e3),
                              ("B3", "B", good, 2e3), ("B4", "B", good, 3e3), ("B5", "B", good, 4e3), ("NO", "", best, 9e9)]:
        r, bb = _row(sym, tier, si, pm)
        rows.append(r)
        bars[sym] = bb
    inp = {"data_cutoff_et": CUT.isoformat(), "premarket_bars": bars}
    rank.apply(rows, inp, CFG)
    order = sorted((r for r in rows if r["shortlist_rank"]), key=lambda r: r["shortlist_rank"])
    assert [r["symbol"] for r in order] == ["A2", "A1", "B1", "B5", "B4"]  # A by score then pm$ tie-break; B after
    no = next(r for r in rows if r["symbol"] == "NO")
    assert no["score"] is None and no["shortlist_rank"] is None and "trigger" not in no
    assert all(r.get("shares_measure") for r in order) and all(r["size_note_challenge"] == "profile not set" for r in order)


def test_early_spike_does_not_set_the_trigger():
    # CRMN-like: a 04:41 spike to 10.84, then trading near 1.70 in the last hour.
    bars = [b("04:41", 8.81, 10.84)] + [b(f"08:{10 + i:02d}", lo) for i, lo in enumerate([1.70, 1.66, 1.64, 1.66, 1.70, 1.72, 1.70, 1.68, 1.71])]
    lv = rank.provisional_levels(bars, START, CUT, CFG)
    assert lv["pm_high_used"] == pytest.approx(1.74) and lv["trigger"] == 1.75


def test_levels_never_gate_the_shortlist():
    wide = {"gap_pct": 30.0, "prior_day_volume_multiple": 5.0, "catalyst_quality": 3, "float_shares": 5e6}
    r, _ = _row("WIDE", "A", wide)
    spiky = [b("08:00", 1.00, 1.40), b("08:01", 1.10), b("08:02", 1.02), b("08:03", 1.10), b("08:04", 1.20)]
    rank.apply([r], {"data_cutoff_et": CUT.isoformat(), "premarket_bars": {"WIDE": spiky}}, CFG)
    assert r["levels_status"].startswith("skip") and r["shortlist_rank"] == 1
