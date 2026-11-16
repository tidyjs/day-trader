from __future__ import annotations

import csv

import pytest

from src import log_trade as L


def rows(p):
    return list(csv.DictReader(p.open()))


def test_skipped_row(tmp_path):
    p = tmp_path / "t.csv"
    assert L.main(["--date", "2026-11-17", "--ticker", "abcd", "--tier", "A", "--decision", "skipped", "--gut", "2", "--reason", "spread wide"], p) == 0
    r = rows(p)[0]
    assert list(r) == L.COLUMNS and r["ticker"] == "ABCD" and r["decision"] == "skipped" and r["entry"] == "" and r["pnl"] == ""


def test_traded_row_computes_pnl_and_update_replaces(tmp_path):
    p = tmp_path / "t.csv"
    base = ["--date", "2026-11-17", "--ticker", "ABCD", "--tier", "B", "--decision", "traded", "--gut", "4", "--reason", "break",
            "--entry", "1.32", "--stop", "1.24", "--shares", "30"]
    L.main(base, p)
    assert rows(p)[0]["exit"] == "" and rows(p)[0]["pnl"] == ""
    with pytest.raises(SystemExit, match="already logged"):
        L.main(base, p)
    L.main(base + ["--exit", "1.44", "--exit-reason", "trail", "--update"], p)
    r = rows(p)
    assert len(r) == 1 and r[0]["pnl"] == "3.6" and r[0]["exit_reason"] == "trail"


def test_validation(tmp_path):
    p = tmp_path / "t.csv"
    with pytest.raises(SystemExit, match="needs --entry"):
        L.main(["--date", "2026-11-17", "--ticker", "X", "--tier", "A", "--decision", "traded", "--gut", "3", "--reason", "r"], p)
    with pytest.raises(SystemExit, match="below --entry"):
        L.main(["--date", "2026-11-17", "--ticker", "X", "--tier", "A", "--decision", "traded", "--gut", "3", "--reason", "r",
                "--entry", "1.0", "--stop", "1.1", "--shares", "5"], p)
    with pytest.raises(SystemExit):
        L.main(["--date", "2026-11-17", "--ticker", "X", "--tier", "A", "--decision", "traded", "--gut", "6", "--reason", "r"], p)
    with pytest.raises(ValueError):
        L.main(["--date", "17/11/2026", "--ticker", "X", "--tier", "A", "--decision", "skipped", "--gut", "3", "--reason", "r"], p)
