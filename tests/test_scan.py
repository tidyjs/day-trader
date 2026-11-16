from __future__ import annotations

import csv
import json

import pytest

from src import scan
from tests.fixtures import CFG, bar, make_inputs


def cands(inp):
    return {r["symbol"]: r for r in scan.evaluate(inp, CFG)["candidates"]}


# ------------------------------------------------------------ price and gap


@pytest.mark.parametrize(
    "price,expect",
    [(0.99, False), (1.00, True), (1.50, True), (2.00, True), (2.01, False)],
)
def test_price_boundaries_inclusive(price, expect):
    # prior close low enough that the gap always passes
    inp = make_inputs({"GAPR": 0.80}, {"GAPR": [bar("08:30", price)]})
    assert ("GAPR" in cands(inp)) is expect


def test_gap_exactly_min_passes_and_just_below_fails():
    ok = make_inputs({"GAPR": 1.00}, {"GAPR": [bar("08:30", 1.10)]})
    no = make_inputs({"GAPR": 1.00}, {"GAPR": [bar("08:30", 1.0999)]})
    assert cands(ok)["GAPR"]["gap_pct"] == 10.0
    assert "GAPR" not in cands(no)


def test_prior_close_band_upper_is_exact():
    # price_max / 1.10 = 1.8182; a 1.82 prior close can never gap 10% into $2.
    assert scan.prior_close_band(CFG)[1] == pytest.approx(2.0 / 1.1)
    inp = make_inputs({"HIGH": 1.82}, {"HIGH": [bar("08:30", 2.00)]})
    s = scan.evaluate(inp, CFG)["summary"]
    assert s["checked_in_band"] == 0 and s["candidates"] == 0


def test_no_premarket_bars_means_no_candidate():
    inp = make_inputs({"GAPR": 1.0}, {})
    out = scan.evaluate(inp, CFG)
    assert out["candidates"] == [] and out["summary"]["checked_in_band"] == 1


# ------------------------------------------------------------ no look-ahead


def test_bars_after_cutoff_are_ignored():
    # as_of 09:15, delay 16 -> cutoff 08:59. Only bars that closed by 08:59 count.
    bars = [bar("08:30", 1.05), bar("08:58", 1.06), bar("08:59", 1.50), bar("09:10", 1.60)]
    inp = make_inputs({"GAPR": 1.00}, {"GAPR": bars})
    assert inp["data_cutoff_et"].startswith("2026-11-13T08:59")
    assert "GAPR" not in cands(inp)  # 1.06 is only +6%


def test_last_complete_bar_sets_price_and_stats():
    bars = [bar("04:00", 1.20, v=1000, n=10, h=1.30), bar("08:58", 1.25, v=2000, n=20), bar("08:59", 9.99, v=10**6)]
    r = cands(make_inputs({"GAPR": 1.00}, {"GAPR": bars}))["GAPR"]
    assert r["price"] == 1.25 and r["last_bar_et"] == "08:58"
    assert r["pm_high"] == 1.30 and r["pm_volume"] == 3000 and r["pm_trades"] == 30
    assert r["pm_dollar_volume"] == pytest.approx(1000 * 1.20 + 2000 * 1.25)


def test_bars_before_premarket_start_are_ignored():
    early = bar("03:59", 1.50)
    inp = make_inputs({"GAPR": 1.00}, {"GAPR": [early]})
    assert "GAPR" not in cands(inp)


def test_unsorted_bars_are_handled():
    bars = [bar("08:40", 1.30), bar("08:10", 1.05)]
    assert cands(make_inputs({"GAPR": 1.00}, {"GAPR": bars}))["GAPR"]["price"] == 1.30


# ------------------------------------------------------------ T212 rule and log


def test_non_t212_names_are_logged_with_t212_fail():
    inp = make_inputs({"GAPR": 1.0, "NOPE": 1.0}, {"GAPR": [bar("08:30", 1.2)], "NOPE": [bar("08:30", 1.3)]}, t212=("GAPR",))
    c = cands(inp)
    assert c["GAPR"]["rule_t212"] == "pass"
    assert c["NOPE"]["rule_t212"] == "fail" and not c["NOPE"]["eligible"]
    assert scan.evaluate(inp, CFG)["summary"]["rules"]["rule_t212"] == {"pass": 1, "fail": 1}


def test_t212_match_ignores_punctuation():
    inp = make_inputs({"ABCD": 1.0}, {"ABCD": [bar("08:30", 1.2)]}, t212=("AB.CD",))
    assert cands(inp)["ABCD"]["rule_t212"] == "pass"


def test_sorted_by_premarket_dollar_volume():
    inp = make_inputs(
        {"AAA": 1.0, "BBB": 1.0},
        {"AAA": [bar("08:30", 1.2, v=100)], "BBB": [bar("08:30", 1.2, v=10_000)]},
        t212=("AAA", "BBB"),
    )
    assert [r["symbol"] for r in scan.evaluate(inp, CFG)["candidates"]] == ["BBB", "AAA"]


# ------------------------------------------------------------ warnings


def test_historical_run_warnings():
    inp = make_inputs({"GAPR": 1.0}, {"GAPR": [bar("08:30", 1.2)]}, t212_as_of="2026-11-15", fetched_at="2026-11-15T10:00:00-05:00")
    w = scan.evaluate(inp, CFG)["summary"]["warnings"]
    assert any("T212 list is from 2026-11-15" in x for x in w)
    assert any("no delisted names" in x for x in w)


def test_stale_t212_list_warning_and_refresh_error():
    inp = make_inputs({"GAPR": 1.0}, {"GAPR": [bar("08:30", 1.2)]}, t212_as_of="2026-11-10")
    inp["t212"]["refresh_error"] = "RuntimeError: T212 HTTP 401"
    w = scan.evaluate(inp, CFG)["summary"]["warnings"]
    assert "T212 list is 3 days old" in w
    assert any("401" in x for x in w)
    assert "3 days old" in cands(inp)["GAPR"]["warnings"]


# ------------------------------------------------------------ universe


def test_common_stock_filter():
    assets = [
        {"symbol": "GOOD", "name": "Good Corp Common Stock", "exchange": "NASDAQ", "tradable": True},
        {"symbol": "ORDN", "name": "Foo Ltd Ordinary Shares", "exchange": "NYSE", "tradable": True},
        {"symbol": "GOODW", "name": "Good Corp Warrant", "exchange": "NASDAQ", "tradable": True},
        {"symbol": "SPYX", "name": "Some ETF", "exchange": "ARCA", "tradable": True},
        {"symbol": "OTCX", "name": "Otc Co Common Stock", "exchange": "OTC", "tradable": True},
        {"symbol": "BRK.B", "name": "Berkshire Class B", "exchange": "NYSE", "tradable": True},
        {"symbol": "HALT", "name": "Halted Inc Common Stock", "exchange": "NYSE", "tradable": False},
        {"symbol": "TRST", "name": "Trustco Bank Corp Common Stock", "exchange": "NASDAQ", "tradable": True},
    ]
    assert list(scan.common_stock_filter(assets, CFG)) == ["GOOD", "ORDN", "TRST"]


# ------------------------------------------------------------ reproducibility


def test_evaluate_is_deterministic_and_trim_preserves_output():
    pcs = {"AAA": 1.0, "BBB": 1.0, "CCC": 1.5, "DDD": 0.9}
    bars = {
        "AAA": [bar("04:05", 1.1), bar("08:30", 1.2)],                  # candidate
        "BBB": [bar("05:00", 1.02), bar("08:00", 1.03), bar("09:00", 2)],  # fails gap; 09:00 is after cutoff
        "CCC": [bar("07:00", 1.9)],                                      # candidate, not on T212
        "DDD": [bar("06:00", 0.95)],                                     # fails price
    }
    inp = make_inputs(pcs, bars, t212=("AAA",))
    a, b = scan.evaluate(inp, CFG), scan.evaluate(json.loads(json.dumps(inp)), CFG)
    assert a == b
    trimmed = scan.trim_inputs(inp, a)
    assert trimmed["premarket_bars"]["BBB"] == [bars["BBB"][1]]  # last bar before cutoff only
    assert trimmed["premarket_bars"]["AAA"] == bars["AAA"]
    assert "symbols" not in trimmed["t212"]
    trimmed["t212"]["symbols"] = inp["t212"]["symbols"]
    assert scan.evaluate(trimmed, CFG) == a


def test_save_and_replay_roundtrip(tmp_path, monkeypatch):
    from src.data import t212 as t212mod

    monkeypatch.setattr(scan, "ROOT", tmp_path)
    lst_path = t212mod.save(["AAA"], __import__("datetime").date(2026, 11, 13), tmp_path / "data/t212")
    inp = make_inputs({"AAA": 1.0, "BBB": 1.0}, {"AAA": [bar("08:30", 1.2)], "BBB": [bar("08:30", 1.3)]}, t212=("AAA",))
    lst = t212mod.load_file(lst_path, tmp_path)
    inp["t212"].update(path=lst.path, sha256=lst.sha256)
    out = scan.evaluate(inp, CFG)
    cfg = dict(CFG, paths={**CFG["paths"]})
    p = tmp_path / "data/scans/2026-11-13.json"
    scan.save(cfg, inp, out, p)
    assert scan.replay(p, CFG)

    # an old-schema file is refused rather than silently mis-scored
    j = json.loads(p.read_text())
    j["inputs"]["schema"] = 1
    old = tmp_path / "data/scans/old.json"
    old.write_text(json.dumps(j))
    with pytest.raises(RuntimeError, match="schema 1"):
        scan.replay(old, CFG)

    # changing the committed T212 file must be detected
    t212mod.save(["AAA", "BBB"], __import__("datetime").date(2026, 11, 13), tmp_path / "data/t212")
    with pytest.raises(RuntimeError, match="hash mismatch"):
        scan.replay(p, CFG)


def test_candidates_csv_upsert_is_idempotent(tmp_path):
    p = tmp_path / "c.csv"
    inp = make_inputs({"AAA": 1.0, "BBB": 1.0}, {"AAA": [bar("08:30", 1.2)], "BBB": [bar("08:30", 1.3)]})
    rows = scan.evaluate(inp, CFG)["candidates"]
    other = [dict(rows[0], date="2026-11-12", as_of_et="2026-11-12T09:15:00-05:00")]
    scan.upsert_candidates(p, other, "2026-11-12", other[0]["as_of_et"])
    for _ in range(2):
        scan.upsert_candidates(p, rows, inp["day"], inp["as_of_et"])
    got = list(csv.DictReader(p.open()))
    assert len(got) == 3
    assert [r["date"] for r in got] == ["2026-11-12", "2026-11-13", "2026-11-13"]
    assert set(got[0]) == set(scan.CSV_COLUMNS)


# ------------------------------------------------------------ M2: rules on rows and gating

from tests.fixtures import daily, filing, flat_history  # noqa: E402


CAT_OK = {"status": "ok", "forced_none": False, "items_used": 2, "items_dropped_roundup": 1,
          "output": {"catalyst_type": "contract", "quality": 4, "promo_or_pump_flag": False, "dilution_language": False,
                     "acquisition_target": False, "one_line_summary": "Signed $5M contract"}}


def _hist_pass():
    h = flat_history(25, v=1_000_000)
    h[-1] = daily("2026-11-12", 1.0, v=5_000_000, h=1.0, l=0.8)  # 5x volume, closed at the high
    return h


def _liquid(c=1.2):
    return [bar("08:30", c, v=200_000, n=500)]


def _edgar_clean(cik=1):
    return {"cik": cik, "filings": [], "shares_points": [{"val": 20e6, "end": "2026-09-30", "filed": "2026-10-15"}], "errors": [], "docs_capped": 0}


def test_full_row_eligible_with_all_rules():
    inp = make_inputs({"GAPR": 1.0}, {"GAPR": _liquid()}, history={"GAPR": _hist_pass()}, edgar={"GAPR": _edgar_clean()},
                      quotes={"GAPR": [{"t": "2026-11-13T13:58:00Z", "bp": 1.19, "ap": 1.21}]},
                      yahoo={"GAPR": {"fetched_at": "2026-11-13T09:15:00-05:00", "floatShares": 12e6, "sharesOutstanding": 20e6}},
                      catalyst={"GAPR": CAT_OK})
    r = cands(inp)["GAPR"]
    for c in scan.MUST_PASS + ["rule_float"] + scan.DISQUALIFIERS:
        assert r[c] == "pass", c
    assert r["catalyst_type"] == "contract" and r["catalyst_quality"] == 4
    assert r["eligible"] and r["spread_pct"] == pytest.approx(1.67, abs=0.01)
    assert r["warnings"] == ""


def test_failing_cheap_rule_skips_yahoo_and_spread():
    # Low premarket dollar volume: Yahoo data present in inputs must still be ignored.
    inp = make_inputs({"GAPR": 1.0}, {"GAPR": [bar("08:30", 1.2, v=100, n=1)]}, history={"GAPR": _hist_pass()},
                      edgar={"GAPR": _edgar_clean()}, yahoo={"GAPR": {"fetched_at": "x", "floatShares": 1}})
    r = cands(inp)["GAPR"]
    assert r["rule_pm_dollar_volume"] == "fail" and r["rule_pm_trades"] == "fail"
    assert r["rule_float"] == "" and r["float_shares"] is None and r["spread_pct"] is None
    assert not r["eligible"]


def test_disqualified_name_is_logged_with_reason():
    ed = _edgar_clean()
    ed["filings"] = [filing("424B5", "2026-11-12", cover="We are offering 2,000,000 shares of our common stock.")]
    inp = make_inputs({"GAPR": 1.0}, {"GAPR": _liquid()}, history={"GAPR": _hist_pass()}, edgar={"GAPR": ed})
    r = cands(inp)["GAPR"]
    assert r["dq_offering"] == "fail" and "424B5" in r["dq_reasons"] and not r["eligible"] and r["rule_float"] == ""


def test_possible_offering_and_unknowns_stay_eligible_with_warnings():
    ed = _edgar_clean()
    ed["filings"] = [filing("424B2", "2026-11-12", cover="Notes due 2031")]  # debt only: possible, not DQ
    ed["shares_points"] = [{"val": 20e6, "end": "2026-03-31", "filed": "2026-05-01"}]  # > 120 days old
    inp = make_inputs({"GAPR": 1.0}, {"GAPR": _liquid()}, history={"GAPR": _hist_pass()}, edgar={"GAPR": ed},
                      yahoo={"GAPR": {"fetched_at": "2026-11-13T09:15:00-05:00", "floatShares": None, "sharesOutstanding": 60e6}})
    r = cands(inp)["GAPR"]
    assert r["eligible"] and r["rule_float"] == "pass" and r["float_source"].startswith("edgar")
    for w in ("possible offering", "stale", "float missing", "differ", "spread unknown"):
        assert w in r["warnings"], w


def test_no_cik_is_unknown_not_disqualified():
    inp = make_inputs({"GAPR": 1.0}, {"GAPR": _liquid()}, history={"GAPR": _hist_pass()}, edgar={"GAPR": {"cik": None}})
    r = cands(inp)["GAPR"]
    assert r["dq_offering"] == "unknown" and r["dq_reverse_split"] == "unknown"
    assert "no CIK" in r["warnings"] and r["rule_float"] == "unknown"


def test_unknown_continuation_is_not_eligible():
    inp = make_inputs({"GAPR": 1.0}, {"GAPR": _liquid()}, history={"GAPR": []}, edgar={"GAPR": _edgar_clean()})
    r = cands(inp)["GAPR"]
    assert r["rule_continuation"] == "unknown" and not r["eligible"] and "continuation unknown" in r["warnings"]


class _FakeAlpaca:
    def __init__(self):
        self.quote_syms = None

    def bars(self, syms, timeframe, start, end, feed="sip", batch=200):
        return {s: _hist_pass() for s in syms}

    def quotes(self, syms, start, end, feed="sip"):
        self.quote_syms = sorted(syms)
        return {s: [{"t": "2026-11-13T13:58:00Z", "bp": 1.19, "ap": 1.21}] for s in syms}


def test_gather_calls_yahoo_and_quotes_only_for_survivors(monkeypatch):
    from src.data import edgar as edgarmod
    from src.data import yahoo as yahoomod

    from src.data import halts as haltsmod

    called = {}
    monkeypatch.setattr(haltsmod, "fetch", lambda now: {"fetched_at": now.isoformat(), "ok": True, "items": [], "error": None, "markets": []})
    monkeypatch.setattr(haltsmod, "log_markets", lambda feed, path: None)  # never write into real data/
    from src import catalyst as catmod
    monkeypatch.setattr(catmod, "gather", lambda alp, llm, cands, ed, as_of, cfg: ({}, {r["symbol"]: CAT_OK for r in cands}))
    monkeypatch.setattr(edgarmod, "gather", lambda ed, syms, *a, **k: {s: _edgar_clean() for s in syms})
    monkeypatch.setattr(yahoomod, "gather", lambda syms, now: called.setdefault("yahoo", sorted(syms)) and {s: {"fetched_at": now.isoformat(), "floatShares": 5e6} for s in syms})
    bars = {"GOOD": _liquid(), "THIN": [bar("08:30", 1.2, v=100, n=1)], "NOTT": _liquid()}
    inp = make_inputs({"GOOD": 1.0, "THIN": 1.0, "NOTT": 1.0}, bars, t212=("GOOD", "THIN"))
    alp = _FakeAlpaca()
    now = __import__("datetime").datetime.fromisoformat(inp["as_of_et"])
    out = scan.gather_filter_inputs(alp, None, CFG, inp, now, __import__("datetime").datetime.fromisoformat(inp["data_cutoff_et"]), now)
    assert called["yahoo"] == ["GOOD"] and alp.quote_syms == ["GOOD"]
    assert sorted(out["edgar"]) == ["GOOD", "NOTT", "THIN"]  # EDGAR for every candidate
    res = {r["symbol"]: r for r in scan.evaluate(out, CFG)["candidates"]}
    assert res["GOOD"]["eligible"] and not res["THIN"]["eligible"] and not res["NOTT"]["eligible"]


def test_halt_feed_failure_is_a_warning_on_every_row():
    bad = {"fetched_at": "2026-11-13T09:15:00-05:00", "ok": False, "items": [], "error": "Timeout", "markets": []}
    inp = make_inputs({"GAPR": 1.0}, {"GAPR": _liquid()}, history={"GAPR": _hist_pass()}, edgar={"GAPR": _edgar_clean()}, halts=bad)
    r = cands(inp)["GAPR"]
    assert r["halt_status"].startswith("halt status unknown") and "Timeout" in r["warnings"]
    assert r["dq_offering"] == "pass"  # a warning, never a disqualifier


def test_evidence_has_sentence_and_url():
    ed = _edgar_clean()
    f = filing("424B5", "2026-11-12", cover="Prospectus Supplement. We are offering 2,000,000 shares of our common stock at $1.00 per share. Other text.")  # noqa
    f["url"] = "https://www.sec.gov/Archives/edgar/data/1/000000000026000001/d.htm"
    ed["filings"] = [f]
    inp = make_inputs({"GAPR": 1.0}, {"GAPR": _liquid()}, history={"GAPR": _hist_pass()}, edgar={"GAPR": ed})
    ev = cands(inp)["GAPR"]["evidence"]
    assert "[offering:disqualify]" in ev and "2,000,000 shares of our common stock" in ev and f["url"] in ev


def test_funnel_counts_only_this_rule():
    from src import funnel
    base = {c: "pass" for c in funnel.RULES}
    rows = [
        dict(base, symbol="A", date="2026-11-13", rule_gap="fail"),
        dict(base, symbol="B", date="2026-11-13", rule_gap="fail", rule_t212="fail"),
        dict(base, symbol="C", date="2026-11-13", rule_float="", dq_offering="unknown"),
    ]
    f = {x["rule"]: x for x in funnel.funnel(rows)}
    assert (f["rule_gap"]["fail"], f["rule_gap"]["fail_only_this"]) == (2, 1)
    assert (f["rule_t212"]["fail"], f["rule_t212"]["fail_only_this"]) == (1, 0)
    assert f["rule_float"]["not_checked"] == 1 and f["dq_offering"]["unknown"] == 1
    # cost order: gap runs before t212, so A and B are removed at gap and only C reaches t212
    assert f["rule_gap"]["reached"] == 3 and f["rule_gap"]["fail_at_step"] == 2
    assert f["rule_t212"]["reached"] == 1 and f["rule_t212"]["fail_at_step"] == 0


def _cat(**out):
    base = dict(CAT_OK["output"]); base.update(out)
    return dict(CAT_OK, output=base)


def test_catalyst_rule_on_rows():
    def row(cat, hist=None):
        inp = make_inputs({"GAPR": 1.0}, {"GAPR": _liquid()}, history={"GAPR": hist or _hist_pass()}, edgar={"GAPR": _edgar_clean()}, catalyst={"GAPR": cat})
        return cands(inp)["GAPR"]

    assert row(_cat(promo_or_pump_flag=True))["dq_promo_or_no_catalyst"] == "fail"
    assert row(_cat(catalyst_type="promo"))["dq_promo_or_no_catalyst"] == "fail"
    # no catalyst but a 5x prior-day volume surge: passes (SPEC 4.2 needs both missing)
    r = row(_cat(catalyst_type="none", quality=0))
    assert r["dq_promo_or_no_catalyst"] == "pass" and r["prior_day_volume_multiple"] == 5.0
    # no catalyst and flat volume: disqualified
    flat = flat_history(25)
    flat[-1] = daily("2026-11-12", 1.0, h=1.0, l=0.8)
    r = row(_cat(catalyst_type="none", quality=0), flat)
    assert r["dq_promo_or_no_catalyst"] == "fail" and "no prior-day volume surge (1.0x)" in r["dq_reasons"]
    # unavailable classifier is unknown + warning, not a pass or a fail
    r = row({"status": "unavailable", "output": None, "error": "stop_reason refusal"})
    assert r["dq_promo_or_no_catalyst"] == "unknown" and "classifier unavailable" in r["warnings"]
    # dilution language with no filing -> warning
    assert "dilution language in news" in row(_cat(dilution_language=True))["warnings"]


def test_dollar_volume_is_python_version_independent():
    # Naive float summation differs between Python 3.9 and 3.12 for inputs like these;
    # math.fsum is exact, so the rounded value must equal the exact decimal result.
    from decimal import Decimal
    vals = [(37, 1.0399), (100, 1.0601), (12, 1.0599), (500, 1.0333), (3, 1.0777)] * 7
    bars_ = [dict(bar(f"08:{i:02d}", c, v=v, vw=c)) for i, (v, c) in enumerate(vals)]
    st = scan.premarket_stats(bars_, *[__import__("datetime").datetime.fromisoformat(x) for x in ("2026-11-13T04:00:00-05:00", "2026-11-13T08:59:00-05:00")])
    exact = sum(Decimal(v) * Decimal(repr(c)) for v, c in vals)
    assert st["pm_dollar_volume"] == round(float(exact), 2)


def test_nyse_name_never_gets_a_clean_halt_pass():
    inp = make_inputs({"GAPR": 1.0}, {"GAPR": _liquid()}, history={"GAPR": _hist_pass()}, edgar={"GAPR": _edgar_clean()}, catalyst={"GAPR": CAT_OK})
    inp["universe"]["exchanges"] = {"GAPR": "NYSE"}
    r = cands(inp)["GAPR"]
    assert r["exchange"] == "NYSE" and r["halt_status"].startswith("halt status unknown") and "coverage not confirmed" in r["warnings"]
    assert r["eligible"]  # a warning, never a disqualifier


def test_merger_target_warning_only_for_target():
    def row(**out):
        inp = make_inputs({"GAPR": 1.0}, {"GAPR": _liquid()}, history={"GAPR": _hist_pass()}, edgar={"GAPR": _edgar_clean()}, catalyst={"GAPR": _cat(**out)})
        return cands(inp)["GAPR"]
    r = row(catalyst_type="merger", acquisition_target=True)
    assert "merger target: price likely pinned to deal terms" in r["warnings"] and r["eligible"]  # warning only
    assert "merger target" not in row(catalyst_type="merger", acquisition_target=False)["warnings"]
    assert "merger target" not in row(catalyst_type="earnings", acquisition_target=True)["warnings"]
