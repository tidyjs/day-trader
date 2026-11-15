from __future__ import annotations

from datetime import date, datetime

import pytest

from src.data import t212
from src.timeutil import ET, at_et, bar_complete_before, data_cutoff, to_utc_z

INSTRUMENTS = [
    {"ticker": "SKBL_US_EQ", "shortName": "CRMN", "type": "STOCK", "currencyCode": "USD"},  # renamed
    {"ticker": "AAPL_US_EQ", "shortName": "AAPL", "type": "STOCK", "currencyCode": "USD"},
    {"ticker": "FOOWAR_US_EQ", "shortName": "FOOW", "type": "WARRANT", "currencyCode": "USD"},
    {"ticker": "SPY_US_EQ", "shortName": "SPY", "type": "ETF", "currencyCode": "USD"},
    {"ticker": "VODl_EQ", "shortName": "VOD", "type": "STOCK", "currencyCode": "GBX"},
    {"ticker": "XYZ_US_EQ", "type": "STOCK", "currencyCode": "USD"},  # no shortName
]


def test_us_stock_symbols_uses_shortname():
    assert t212.us_stock_symbols(INSTRUMENTS) == ["AAPL", "CRMN", "XYZ"]


def test_contains_normalizes():
    lst = t212.T212List(["BRK.B", "CRMN"], date(2026, 11, 13), "x", "h")
    assert lst.contains("BRKB") and lst.contains("brk_b") and lst.contains("CRMN")
    assert not lst.contains("SKBL")


def _big():
    return [{"ticker": f"S{i}_US_EQ", "shortName": f"S{i}", "type": "STOCK", "currencyCode": "USD"} for i in range(1500)]


def test_get_list_refreshes_and_saves(tmp_path, monkeypatch):
    monkeypatch.setenv("T212_API_KEY", "k")
    monkeypatch.setattr(t212, "fetch", lambda *a: _big())
    lst = t212.get_list(date(2026, 11, 16), tmp_path / "t212", tmp_path, "https://x")
    assert len(lst.symbols) == 1500 and lst.path == "t212/2026-11-16.json" and lst.refresh_error is None


def test_get_list_uses_todays_file_without_fetching(tmp_path, monkeypatch):
    t212.save(["AAA"], date(2026, 11, 16), tmp_path / "t212")
    monkeypatch.setenv("T212_API_KEY", "k")
    monkeypatch.setattr(t212, "fetch", lambda *a: pytest.fail("should not fetch"))
    assert t212.get_list(date(2026, 11, 16), tmp_path / "t212", tmp_path, "https://x").symbols == ["AAA"]


def test_get_list_falls_back_to_newest_saved(tmp_path, monkeypatch):
    t212.save(["OLD"], date(2026, 11, 10), tmp_path / "t212")
    t212.save(["NEWER"], date(2026, 11, 12), tmp_path / "t212")
    monkeypatch.setenv("T212_API_KEY", "k")

    def boom(*a):
        raise RuntimeError("T212 HTTP 401")

    monkeypatch.setattr(t212, "fetch", boom)
    lst = t212.get_list(date(2026, 11, 16), tmp_path / "t212", tmp_path, "https://x")
    assert lst.symbols == ["NEWER"] and lst.age_days == 4 and "401" in lst.refresh_error


def test_get_list_rejects_suspiciously_small_list(tmp_path, monkeypatch):
    t212.save(["OLD"], date(2026, 11, 10), tmp_path / "t212")
    monkeypatch.setenv("T212_API_KEY", "k")
    monkeypatch.setattr(t212, "fetch", lambda *a: INSTRUMENTS)
    lst = t212.get_list(date(2026, 11, 16), tmp_path / "t212", tmp_path, "https://x")
    assert lst.symbols == ["OLD"] and "suspiciously small" in lst.refresh_error


def test_get_list_with_nothing_saved_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("T212_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="No T212 list"):
        t212.get_list(date(2026, 11, 16), tmp_path / "t212", tmp_path, "https://x")


# ------------------------------------------------------------ time / DST


def test_et_offsets_follow_dst():
    assert to_utc_z(at_et(date(2026, 7, 15), "09:15")) == "2026-07-15T13:15:00Z"  # EDT
    assert to_utc_z(at_et(date(2026, 11, 13), "09:15")) == "2026-11-13T14:15:00Z"  # EST


def test_data_cutoff_rounds_down_to_minute():
    as_of = datetime(2026, 11, 13, 9, 15, 42, tzinfo=ET)
    assert data_cutoff(as_of, 16) == datetime(2026, 11, 13, 8, 59, tzinfo=ET)


def test_bar_complete_before():
    cut = datetime(2026, 11, 13, 8, 59, tzinfo=ET)
    assert bar_complete_before("2026-11-13T13:58:00Z", cut)       # 08:58 bar closes 08:59
    assert not bar_complete_before("2026-11-13T13:59:00Z", cut)   # 08:59 bar closes 09:00


def test_parse_ts_handles_nanoseconds_and_z():
    from src.timeutil import parse_ts
    a = parse_ts("2026-11-12T13:57:01.673084685Z")
    assert a.microsecond == 673084 and a.utcoffset().total_seconds() == 0
    assert parse_ts("2026-11-12T13:57:00Z").second == 0
