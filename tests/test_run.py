from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from src import run
from src.timeutil import ET


def et_from_utc(y, m, d, hh, mm):
    return datetime(y, m, d, hh, mm, tzinfo=timezone.utc).astimezone(ET)


# Both sides of DST: 2026-07-15 is EDT (UTC-4), 2026-11-16 is EST (UTC-5).
@pytest.mark.parametrize("day,utc_hhmm,expect", [
    ((2026, 7, 15), (13, 15), "scan"),    # 09:15 EDT: in-season entry
    ((2026, 7, 15), (14, 15), "alert"),   # 10:15 EDT, no scan exists -> alert (backstop)
    ((2026, 7, 15), (15, 30), "alert"),   # 11:30 EDT backstop
    ((2026, 11, 16), (13, 15), "skip"),   # 08:15 EST: off-season entry, too early
    ((2026, 11, 16), (14, 15), "scan"),   # 09:15 EST: in-season entry
    ((2026, 11, 16), (15, 30), "alert"),  # 10:30 EST backstop
])
def test_cron_entries_both_sides_of_dst(day, utc_hhmm, expect):
    assert run.decide(et_from_utc(*day, *utc_hhmm), True, False).action == expect


def test_existing_scan_makes_every_entry_quiet():
    for hhmm in ((13, 15), (14, 15), (15, 30)):
        assert run.decide(et_from_utc(2026, 7, 15, *hhmm), True, True).action == "skip"


def test_delayed_off_season_entry_cannot_scan_twice():
    # 08:15 EST entry delayed 70 min to 09:25: inside the window, but the scan exists.
    late = et_from_utc(2026, 11, 16, 14, 25)
    assert run.decide(late, True, True).action == "skip"


def test_late_start_is_scanned_but_marked_late():
    d = run.decide(datetime(2026, 11, 16, 9, 41, tzinfo=ET), True, False)
    assert d.action == "scan" and d.late


def test_non_trading_day_is_quiet():
    assert run.decide(datetime(2026, 11, 26, 9, 15, tzinfo=ET), False, False).action == "skip"  # Thanksgiving


def test_force_error_sends_failure_alert_and_exits_nonzero(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "ROOT", tmp_path)
    sent = []
    monkeypatch.setattr(run.alerts, "send", lambda kind, subject, body, now: sent.append((kind, subject, body)))
    code = run.main(["--now", "2026-11-16T09:15", "--force-error"], scan_fn=lambda: pytest.fail("must not scan"),
                    trading_day_fn=lambda d: True)
    assert code == 1 and sent[0][0] == "scanner_failed" and "forced error" in sent[0][2]


def test_scan_exception_sends_failure_alert(tmp_path, monkeypatch):
    sent = []
    monkeypatch.setattr(run.alerts, "send", lambda kind, subject, body, now: sent.append(body))
    def boom():
        raise ConnectionError("Alpaca unreachable")
    assert run.main(["--now", "2026-11-16T09:16"], scan_fn=boom, trading_day_fn=lambda d: True) == 1
    assert "ConnectionError: Alpaca unreachable" in sent[0]


def test_calendar_failure_is_a_failure_alert(monkeypatch):
    sent = []
    monkeypatch.setattr(run.alerts, "send", lambda kind, subject, body, now: sent.append(subject))
    def cal(d):
        raise TimeoutError("calendar down")
    assert run.main(["--now", "2026-11-16T09:15"], scan_fn=lambda: None, trading_day_fn=cal) == 1
    assert "calendar check" in sent[0]


def test_successful_scan_exits_zero(monkeypatch, capsys):
    out = {"summary": {"candidates": 7, "eligible": 1}}
    assert run.main(["--now", "2026-11-16T09:15"], scan_fn=lambda: out, trading_day_fn=lambda d: True) == 0
    assert "7 candidates, 1 eligible" in capsys.readouterr().out


def test_backstop_alerts_once_per_day(tmp_path, monkeypatch):
    from src import alerts
    monkeypatch.setattr(alerts, "folder", lambda: tmp_path)
    args = ["--now", "2026-11-16T10:30"]
    assert run.main(args, scan_fn=lambda: None, trading_day_fn=lambda d: True) == 1
    assert run.main(args, scan_fn=lambda: None, trading_day_fn=lambda d: True) == 1
    assert len(list(tmp_path.glob("*/*/*_scanner_failed*.md"))) == 1
