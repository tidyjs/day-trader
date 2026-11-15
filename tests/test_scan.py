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


def test_non_t212_names_are_logged_but_fail_m1():
    inp = make_inputs({"GAPR": 1.0, "NOPE": 1.0}, {"GAPR": [bar("08:30", 1.2)], "NOPE": [bar("08:30", 1.3)]}, t212=("GAPR",))
    c = cands(inp)
    assert c["GAPR"]["rule_t212"] and c["GAPR"]["passes_m1"]
    assert not c["NOPE"]["rule_t212"] and not c["NOPE"]["passes_m1"]
    assert scan.evaluate(inp, CFG)["summary"]["passes_m1"] == 1


def test_t212_match_ignores_punctuation():
    inp = make_inputs({"ABCD": 1.0}, {"ABCD": [bar("08:30", 1.2)]}, t212=("AB.CD",))
    assert cands(inp)["ABCD"]["rule_t212"]


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
