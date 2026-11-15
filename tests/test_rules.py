from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

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


# ---- Real MRLN wording (11-13). The old rule disqualified it on boilerplate.
MRLN_COVER = (Path(__file__).parent / "data" / "mrln_424b3_2026-11-13_cover.txt").read_text()
MRLN_BASE = ("Secondary Offering of up to 13,336,000 SHARES OF COMMON STOCK This prospectus relates to the offer and resale, "
             "from time to time, by the selling stockholder named in this prospectus, (including its successors or permitted assigns) "
             "(the \u201c Selling Stockholder \u201d) of up to 13,336,000 shares of common stock, par value $0.0001. "
             "We will not receive any proceeds from the sale of the Resale Shares by the Selling Stockholder.")


def _mrln(base=True):
    f = filing("424B3", "2026-11-13", cover=MRLN_COVER)
    if base:
        f["base"] = {"form": "424B3", "filed": "2026-05-13", "url": "https://www.sec.gov/x", "text": {"cover": MRLN_BASE, "hits": [], "chars": 1}}
    return f


def test_mrln_boilerplate_listing_sentence_is_not_an_offering():
    assert "Our shares of Common Stock are listed on the Nasdaq" in MRLN_COVER
    assert R.ISSUANCE.search(MRLN_COVER) is None


def test_mrln_supplement_to_resale_registration_is_a_warning():
    st, dq, warn, ev = R.offering([_mrln()], DAY, 5)
    assert st == "pass" and dq == []
    assert warn[0].startswith("resale registration, supply overhang") and "2026-05-13" in warn[0]
    assert "We will not receive any proceeds" in ev[0]["sentence"]


def test_mrln_attached_10q_history_does_not_count_as_a_new_raise():
    # The real 11-13 supplement embeds the 10-Q, which describes the past PIPE.
    f = _mrln()
    f["text"]["hits"] = ['the Company would issue shares of its 12.0% Series A Cumulative Convertible Preferred Stock ("Series A Preferred Stock") '
                         'and common stock purchase warrants ("PIPE Warrants") in a PIPE transaction for aggregate gross proceeds of $120,000 (the "Closing PIPE").']
    st, dq, warn, ev = R.offering([f], DAY, 5)
    assert st == "pass" and warn[0].startswith("resale registration, supply overhang")


def test_supplement_whose_cover_is_a_new_offering_still_disqualifies():
    f = filing("424B5", "2026-11-12", cover="This prospectus supplement amends and supplements the prospectus. We are offering 3,000,000 shares of our common stock.")
    assert R.offering([f], DAY, 5)[0] == "fail"


def test_mrln_supplement_without_base_is_still_a_warning_not_silent():
    st, dq, warn, ev = R.offering([_mrln(base=False)], DAY, 5)
    assert st == "pass" and warn and "updating an existing registration" in warn[0]


def test_resale_prospectus_itself_is_a_warning():
    st, dq, warn, _ = R.offering([filing("424B3", "2026-11-12", cover=MRLN_BASE)], DAY, 5)
    assert st == "pass" and warn[0].startswith("resale registration")


def test_supplement_to_active_atm_disqualifies():
    f = filing("424B5", "2026-11-12", cover="This prospectus supplement updates, amends and supplements the prospectus with the information contained in our Quarterly Report on Form 10-Q.")
    f["base"] = {"form": "424B5", "filed": "2026-03-01", "url": "u", "text": {"cover": "We have entered into an At The Market Offering Agreement with H.C. Wainwright under which we may offer and sell shares of our common stock having an aggregate offering price of up to $5,000,000.", "hits": [], "chars": 1}}
    assert R.offering([f], DAY, 5)[0] == "fail"


# ---- Company's own issuance disqualifies


@pytest.mark.parametrize("text", [
    "We are offering 2,000,000 shares of our common stock and pre-funded warrants to purchase up to 500,000 shares.",
    "XYZ Corp. announced the pricing of its $5 million registered direct offering of ordinary shares.",
    "The Company entered into a securities purchase agreement with certain institutional investors for the sale of 3,000,000 shares.",
    "We have entered into an equity distribution agreement with Maxim Group LLC relating to our common stock.",
    "The Company announced the closing of its previously announced underwritten public offering.",
    "The Company has agreed to issue to the investors 1,000,000 shares of common stock in a warrant inducement transaction.",
])
@pytest.mark.parametrize("form", ["424B5", "8-K", "6-K"])
def test_own_issuance_disqualifies(text, form):
    st, dq, warn, ev = R.offering([filing(form, "2026-11-12", hits=[text])], DAY, 5)
    assert st == "fail", (form, text)
    assert ev[0]["sentence"] and ev[0]["result"] == "disqualify"


@pytest.mark.parametrize("text", [
    "Our shares of Common Stock are listed on the Nasdaq Stock Market LLC under the symbol \u201cABCD\u201d.",
    "On November 11, 2026, the closing price of our Common Stock was $1.01 per share.",
    "Holders of our common stock are entitled to one vote per share.",
    "In 2025 we completed our initial public offering.",
])
def test_generic_common_stock_mentions_do_not_disqualify(text):
    st, dq, warn, ev = R.offering([filing("424B3", "2026-11-12", cover=text)], DAY, 5)
    assert st == "pass" and dq == []
    assert warn and warn[0].startswith("possible offering")  # an offering form is still never silent


def test_424b2_debt_only_is_possible_not_disqualify():
    # M0: Apple's notes offering came through as 424B2.
    st, dq, maybe, ev = R.offering([filing("424B2", "2026-11-12", cover="$1,000,000,000 4.25% Notes due 2036")], DAY, 5)
    assert st == "pass" and dq == [] and "no equity-raise wording" in maybe[0]


def test_new_shelf_is_possible_not_disqualify():
    f = filing("S-3", "2026-11-12", cover="We may offer and sell from time to time, in one or more offerings, common stock, preferred stock and warrants.")
    st, dq, maybe, _ = R.offering([f], DAY, 5)
    assert st == "pass" and "shelf registration" in maybe[0]


def test_unreadable_offering_form_is_never_a_silent_pass():
    st, dq, maybe, ev = R.offering([filing("S-1", "2026-11-12", error="HTTPError: 500")], DAY, 5)
    assert st == "pass" and maybe and "not readable" in maybe[0]
    st, dq, maybe, ev = R.offering([filing("S-3", "2026-11-12", text=False)], DAY, 5)
    assert maybe and "document cap" in maybe[0]


def test_8k_generic_offering_language_is_possible():
    f = filing("8-K", "2026-11-12", items="8.01", hits=["the Company closed its private placement"])
    st, dq, maybe, ev = R.offering([f], DAY, 5)
    assert st == "pass" and "no issuance wording" in maybe[0]


def test_earnings_8k_is_not_an_offering():
    f = filing("8-K", "2026-11-12", items="2.02,9.01", cover="Third quarter results. Revenue rose 40%. Our product offering expanded.")
    assert R.offering([f], DAY, 5) == ("pass", [], [], [])


def test_offering_older_than_lookback_ignored():
    text = "We are offering 1,000,000 shares of common stock."
    assert R.offering([filing("424B5", "2026-11-07", cover=text)], DAY, 5)[0] == "pass"
    assert R.offering([filing("424B5", "2026-11-08", cover=text)], DAY, 5)[0] == "fail"


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


def test_at_the_market_needs_a_word_boundary():
    # Real MRLN S-1 sentence that the unbounded pattern matched as an ATM.
    s = "We cannot be sure that the market will continue to grow or that it will grow in ways we anticipate."
    for rx in (R.EQUITY, R.OFFER, R.ISSUANCE, R.STRONG_PRIMARY):
        assert rx.search(s) is None, rx.pattern[:40]
    assert R.ISSUANCE.search("we entered into an at-the-market sales agreement")


def test_resale_cover_wins_over_deep_mention_of_a_past_offering():
    f = _mrln()
    f["base"]["text"]["hits"] = ["In 2025 we completed an underwritten public offering of 2,000,000 shares."]
    st, dq, warn, _ = R.offering([f], DAY, 5)
    assert st == "pass" and warn[0].startswith("resale registration")


def test_mixed_primary_and_secondary_registration_is_possible_not_resale():
    # Real MRLN 424B3 2026-04-21 cover: warrant-exercise shares (primary) plus resale.
    base = ("Primary Offering of up to 66,813,783 SHARES OF COMMON STOCK Secondary Offering of up to 157,700,431 SHARES OF COMMON STOCK "
            "736,744 SHARES OF SERIES A PREFERRED STOCK 760,232 SERIES A PREFERRED INVESTOR WARRANTS This prospectus relates to the offer and resale by the selling stockholders.")
    f = _mrln()
    f["base"]["text"]["cover"] = base
    st, dq, warn, _ = R.offering([f], DAY, 5)
    assert st == "pass" and warn[0].startswith("possible offering") and "primary offering prospectus" in warn[0]


def test_selling_holder_sale_methods_are_not_primary_wording():
    # Real sentence from MRLN's 05-13 resale prospectus cover.
    cover = MRLN_BASE + (" The Selling Stockholder may sell the Resale Shares through ordinary brokerage transactions, "
                         "in underwritten offerings, directly to market makers of our securities or through any other means.")
    f = _mrln()
    f["base"]["text"]["cover"] = cover
    st, dq, warn, _ = R.offering([f], DAY, 5)
    assert st == "pass" and warn[0].startswith("resale registration, supply overhang")
