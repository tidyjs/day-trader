from __future__ import annotations

from datetime import date, datetime

import pytest

from src import rules as R
from src.timeutil import ET
from tests.fixtures import CFG, daily, filing, flat_history

PRIOR = date(2026, 11, 12)
DAY = date(2026, 11, 13)
CONT = CFG["filters"]["continuation"]


# ------------------------------------------------------------ continuation


def test_continuation_close_up_20_pct_passes():
    h = flat_history(25)
    h[-2] = daily("2026-11-11", 1.20)  # +20.0% vs 1.00
    h[-1] = daily("2026-11-12", 1.20)
    st, detail = R.continuation(h, PRIOR, CONT)
    assert st == "pass" and "11-11 +20.0%" in detail


def test_continuation_volume_3x_passes():
    h = flat_history(25, v=1_000_000)
    h[-3] = daily("2026-11-10", 1.0, v=3_000_000)
    st, detail = R.continuation(h, PRIOR, CONT)
    assert st == "pass" and "3.0x vol" in detail


def test_continuation_just_below_both_fails():
    h = flat_history(25, v=1_000_000)
    h[-1] = daily("2026-11-12", 1.1999, v=2_999_999)
    assert R.continuation(h, PRIOR, CONT)[0] == "fail"


def test_continuation_ignores_scan_day_bar():
    # A bar dated on the scan day must never count (look-ahead).
    h = flat_history(25) + [daily("2026-11-13", 5.0, v=10**9)]
    assert R.continuation(h, PRIOR, CONT)[0] == "fail"


def test_continuation_only_window_before_avg():
    # The 3x spike sits in the averaging period, not the window: no pass.
    h = flat_history(25, v=1_000_000)
    h[-5] = daily(h[-5]["t"][:10], 1.0, v=9_000_000)
    assert R.continuation(h, PRIOR, CONT)[0] == "fail"


def test_continuation_short_history_is_unknown_not_fail():
    h = flat_history(3)  # no averaging period
    st, detail = R.continuation(h, PRIOR, CONT)
    assert st == "unknown" and "short history" in detail
    assert R.continuation([], PRIOR, CONT)[0] == "unknown"


def test_continuation_short_history_can_still_pass_on_close():
    h = [daily("2026-11-11", 1.0), daily("2026-11-12", 1.5)]
    assert R.continuation(h, PRIOR, CONT)[0] == "pass"


# ------------------------------------------------------------ prior range


@pytest.mark.parametrize("c,expect", [(2.0, "pass"), (1.75, "pass"), (1.7499, "fail"), (1.0, "fail")])
def test_prior_range_top_quarter(c, expect):
    st, pos = R.prior_range({"h": 2.0, "l": 1.0, "c": c}, 25)
    assert st == expect


def test_prior_range_flat_or_missing_is_unknown():
    assert R.prior_range({"h": 1.0, "l": 1.0, "c": 1.0}, 25)[0] == "unknown"
    assert R.prior_range(None, 25)[0] == "unknown"


# ------------------------------------------------------------ float


F = CFG["filters"]


def test_float_under_cap_passes():
    assert R.float_rule({"floatShares": 10e6}, None, F)[:3] == ("pass", 10e6, "yahoo")


def test_float_within_margin_passes_with_warning():
    st, fl, src, w = R.float_rule({"floatShares": 55e6}, None, F)
    assert st == "pass" and "within 15%" in w[0]


def test_float_over_margin_fails():
    assert R.float_rule({"floatShares": 57.5e6}, None, F)[0] == "fail"


def test_float_missing_uses_edgar_ceiling():
    st, fl, src, w = R.float_rule({}, {"val": 20e6}, F)
    assert st == "pass" and "ceiling" in src and "float missing (Yahoo)" in w


def test_float_missing_and_no_ceiling_is_unknown():
    assert R.float_rule(None, {"val": 80e6}, F)[0] == "unknown"
    assert R.float_rule(None, None, F)[0] == "unknown"


def test_edgar_shares_ignores_points_filed_on_or_after_scan_day():
    pts = [
        {"val": 10, "end": "2026-06-30", "filed": "2026-08-01"},
        {"val": 99, "end": "2026-09-30", "filed": "2026-11-13"},  # filed on the scan day
    ]
    assert R.edgar_shares(pts, DAY)["val"] == 10
    assert R.edgar_shares([], DAY) is None


# ------------------------------------------------------------ offering (4.2)


def test_8k_item_302_disqualifies():
    st, dq, maybe, ev = R.offering([filing("8-K", "2026-11-12", items="3.02,9.01", text=False)], DAY, 5)
    assert st == "fail" and "3.02" in dq[0]


def test_424b_with_equity_on_cover_disqualifies():
    f = filing("424B5", "2026-11-12", cover="Prospectus Supplement 5,000,000 Shares of Common Stock and Pre-Funded Warrants")
    st, dq, _, ev = R.offering([f], DAY, 5)
    assert st == "fail"


def test_424b2_debt_only_is_possible_not_disqualify():
    # M0: Apple's notes offering came through as 424B2.
    f = filing("424B2", "2026-11-12", cover="$1,000,000,000 4.25% Notes due 2036")
    st, dq, maybe, ev = R.offering([f], DAY, 5)
    assert st == "pass" and dq == [] and "no equity wording" in maybe[0]


def test_424b_equity_only_deep_in_text_is_possible():
    f = filing("424B3", "2026-11-12", cover="Prospectus", hits=["... the selling stockholders may resell common stock ..."])
    st, dq, maybe, ev = R.offering([f], DAY, 5)
    assert st == "pass" and "not on its cover" in maybe[0]


def test_unreadable_offering_form_is_never_a_silent_pass():
    st, dq, maybe, ev = R.offering([filing("S-1", "2026-11-12", error="HTTPError: 500")], DAY, 5)
    assert st == "pass" and maybe and "not readable" in maybe[0]
    st, dq, maybe, ev = R.offering([filing("S-3", "2026-11-12", text=False)], DAY, 5)
    assert maybe and "document cap" in maybe[0]


def test_8k_offering_language_with_equity_disqualifies():
    f = filing("8-K", "2026-11-12", items="1.01,8.01", hits=["entered into a securities purchase agreement for the sale of 2,000,000 shares of common stock"])
    assert R.offering([f], DAY, 5)[0] == "fail"


def test_6k_offering_language_disqualifies_foreign_filer():
    f = filing("6-K", "2026-11-12", hits=["announces pricing of $5 million registered direct offering of ordinary shares"])
    assert R.offering([f], DAY, 5)[0] == "fail"


def test_8k_offering_language_without_equity_is_possible():
    f = filing("8-K", "2026-11-12", items="8.01", hits=["the Company closed its private placement"])
    st, dq, maybe, ev = R.offering([f], DAY, 5)
    assert st == "pass" and "no equity terms" in maybe[0]


def test_earnings_8k_is_not_an_offering():
    f = filing("8-K", "2026-11-12", items="2.02,9.01", cover="Third quarter results. Revenue rose 40%. Our product offering expanded.")
    assert R.offering([f], DAY, 5) == ("pass", [], [], [])


def test_offering_older_than_lookback_ignored():
    f = filing("424B5", "2026-11-07", cover="Shares of Common Stock")
    assert R.offering([f], DAY, 5)[0] == "pass"
    assert R.offering([filing("424B5", "2026-11-08", cover="Shares of Common Stock")], DAY, 5)[0] == "fail"


# ------------------------------------------------------------ reverse split and 3.01


# Real excerpts from the M2 run (2026-11-09..13), trimmed.
RS_CASES = [
    ("YMAT", "6-K", "2026-10-30", "(c) all fractional entitlements to the issued Consolidated Class A Ordinary Shares resulting from such share consolidation will not be issued to the shareholders.", "fail"),
    ("EZGO", "6-K", "2026-11-05", "On August 6, 2026, the board of directors approved a reverse share split of the Company's ordinary shares at a ratio of 1-for-3.", "fail"),
    ("AMIX", "8-K", "2026-11-03", "3. To approve an amendment to grant our Board of Directors authority to affect a reverse stock split of the outstanding shares of the Company's common stock, at a ratio of between 1-for-2 to 1-for-25.", "fail"),
    ("WORX", "8-K", "2026-10-05", "each of which the Company satisfied, including effecting a 1-for-12 reverse stock split on August 3, 2026, and evidencing a closing bid price at or above $1.00.", "completed"),
    ("HTOO", "6-K", "2026-09-25", "calculated by dividing $2,000,000 by a price per share of $4.00, subject to adjustment for any share consolidation, share split, share dividend, or any similar event.", "ignore"),
    ("CABR", "8-K", "2026-10-22", "The floor is adjusted proportionately only for subdivisions, combinations, including reverse stock splits, and reclassifications specified in the PIPE Warrants.", "ignore"),
    ("XBIO", "8-K", "2026-11-13", "(xiv) risks related to compliance with Nasdaq listing requirements and the potential need for the combined company to effect a reverse stock split in order to satisfy Nasdaq listing requirements;", "ignore"),
]


@pytest.mark.parametrize("sym,form,filed,text,expect", RS_CASES, ids=[c[0] for c in RS_CASES])
def test_reverse_split_real_wording(sym, form, filed, text, expect):
    st, dq, warn, ev = R.reverse_split([filing(form, filed, hits=[text])], DAY, 60)
    if expect == "fail":
        assert st == "fail" and dq
    elif expect == "completed":
        assert st == "pass" and "completed" in warn[0]
    else:
        assert (st, dq, warn) == ("pass", [], [])


def test_reverse_split_unclear_mention_is_a_warning():
    st, dq, warn, ev = R.reverse_split([filing("8-K", "2026-11-01", hits=["The company discussed a reverse stock split."])], DAY, 60)
    assert st == "pass" and "possible reverse split" in warn[0]


def test_reverse_split_with_future_effective_date_is_pending():
    f = filing("8-K", "2026-11-12", hits=["The reverse stock split became effective on November 20, 2026."])
    assert R.reverse_split([f], DAY, 60)[0] == "fail"


def test_reverse_split_outside_lookback_ignored():
    f = filing("8-K", "2026-09-01", hits=["approved a 1-for-10 reverse stock split"])
    assert R.reverse_split([f], DAY, 60)[0] == "pass"


def test_item_301_deficiency_warning():
    fl = [filing("8-K", "2026-09-01", items="3.01", text=False), filing("8-K", "2026-06-01", items="3.01", text=False)]
    w = R.deficiency(fl, DAY, 90)
    assert len(w) == 1 and "2026-09-01" in w[0]


# ------------------------------------------------------------ spread, shares mismatch


def test_spread_median_and_cutoff():
    cut = datetime(2026, 11, 13, 8, 59, tzinfo=ET)
    q = [
        {"t": "2026-11-13T13:58:00Z", "bp": 1.00, "ap": 1.02},
        {"t": "2026-11-13T13:58:10Z", "bp": 1.00, "ap": 1.04},
        {"t": "2026-11-13T13:58:20Z", "bp": 1.00, "ap": 1.06},
        {"t": "2026-11-13T13:58:30Z", "bp": 0, "ap": 1.06},             # no bid: ignored
        {"t": "2026-11-13T13:58:40Z", "bp": 1.10, "ap": 1.00},          # crossed: ignored
        {"t": "2026-11-13T13:59:00Z", "bp": 1.00, "ap": 2.00},          # at cutoff: ignored
    ]
    assert R.spread_pct(q, cut, 200) == pytest.approx(3.92, abs=0.01)
    assert R.spread_pct([], cut, 200) is None


def test_shares_mismatch_warning():
    assert R.shares_mismatch({"sharesOutstanding": 3.3e6}, {"val": 13.95e6}, 25)  # YMAT in M0
    assert R.shares_mismatch({"sharesOutstanding": 10e6}, {"val": 11e6}, 25) is None
    assert R.shares_mismatch(None, {"val": 1}, 25) is None
