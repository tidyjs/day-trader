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


def _out(eligible=True):
    row = {"symbol": "ABCD", "date": "2026-11-16", "data_cutoff_et": "2026-11-16T08:59:00-05:00", "price": 1.25, "gap_pct": 22.5,
           "pm_dollar_volume": 1234567.0, "eligible": eligible, "catalyst_type": "earnings", "catalyst_quality": 4,
           "catalyst_summary": "Q3 beat", "warnings": "spread 3.4%; float missing (Yahoo)", "rule_price": "pass", "rule_gap": "pass",
           "rule_t212": "pass", "rule_pm_dollar_volume": "pass", "rule_pm_trades": "pass", "rule_continuation": "pass" if eligible else "fail",
           "tier": "A" if eligible else "", "shortlist_rank": 1 if eligible else None, "score": 61.5}
    tb = dict(row, symbol="TIRB", eligible=False, tier="B", shortlist_rank=2 if eligible else 1, score=40.0, rule_continuation="fail")
    thin = dict(row, symbol="THIN", eligible=False, tier="", shortlist_rank=None, rule_pm_dollar_volume="fail")
    rows = [row, tb, thin] if eligible else [dict(row, rule_continuation="fail"), dict(tb, shortlist_rank=None, tier="", rule_prior_range="fail"), thin]
    return {"summary": {"candidates": 3, "eligible": int(eligible), "tiers": {"A": int(eligible), "B": int(eligible)}, "warnings": []}, "candidates": rows}


def test_successful_scan_exits_zero_and_writes_summary(tmp_path, monkeypatch, capsys):
    from src import alerts
    monkeypatch.setattr(alerts, "folder", lambda: tmp_path)
    assert run.main(["--now", "2026-11-16T09:15"], scan_fn=_out, trading_day_fn=lambda d: True) == 0
    assert "3 candidates, 1 eligible" in capsys.readouterr().out
    files = list(tmp_path.glob("2026/11/2026-11-16_0915_scan_summary.md"))
    assert files
    t = files[0].read_text()
    assert "# Scan summary: 1 Tier A, 1 Tier B" in t and "| 1 | ABCD | 61.5 | 1.25 | 22.5 | 1,234,567 |" in t
    assert t.index("## Tier A") < t.index("## Tier B") and "| 2 | TIRB | 40.0 |" in t
    assert "Do not trade from it" in t and "spread 3.4%<br>float missing" in t
    assert "rule_pm_dollar_volume: THIN" in t and "Levels use data up to about 08:59 ET. Re-check the live premarket high at the open." in t
    assert (tmp_path / "LATEST.md").exists()


def test_summary_when_nothing_passes(tmp_path, monkeypatch):
    from src import alerts
    monkeypatch.setattr(alerts, "folder", lambda: tmp_path)
    assert run.main(["--now", "2026-11-16T09:41"], scan_fn=lambda: _out(eligible=False), trading_day_fn=lambda d: True) == 0
    t = next(tmp_path.glob("2026/11/*_scan_summary.md")).read_text()
    assert "Scan summary: no names passed" in t and "No name passed Tier A or Tier B today." in t and "Late start" in t
    assert "rule_continuation: ABCD" in t


def test_summary_write_failure_is_a_failure_alert(monkeypatch):
    sent = []
    def send(kind, subject, body, now):
        if kind == "scan_summary":
            raise OSError("disk full")
        sent.append(kind)
    monkeypatch.setattr(run.alerts, "send", send)
    assert run.main(["--now", "2026-11-16T09:15"], scan_fn=_out, trading_day_fn=lambda d: True) == 1
    assert sent == ["scanner_failed"]


def test_backstop_alerts_once_per_day(tmp_path, monkeypatch):
    from src import alerts
    monkeypatch.setattr(alerts, "folder", lambda: tmp_path)
    args = ["--now", "2026-11-16T10:30"]
    assert run.main(args, scan_fn=lambda: None, trading_day_fn=lambda d: True) == 1
    assert run.main(args, scan_fn=lambda: None, trading_day_fn=lambda d: True) == 1
    assert len(list(tmp_path.glob("*/*/*_scanner_failed*.md"))) == 1


# ------------------------------------------------------------ manual modes


def test_mode_test_message_writes_only_a_test_message(tmp_path, monkeypatch):
    from src import alerts
    monkeypatch.setattr(alerts, "folder", lambda: tmp_path)
    code = run.main(["--mode", "test_message", "--now", "2026-11-16T02:20"],
                    scan_fn=lambda: pytest.fail("must not scan"), trading_day_fn=lambda d: pytest.fail("no calendar call"))
    files = list(tmp_path.glob("2026/11/*.md"))
    assert code == 0 and [f.name for f in files] == ["2026-11-16_0220_test.md"]
    assert "No scan ran" in files[0].read_text() and (tmp_path / "LATEST.md").exists()


@pytest.mark.parametrize("now,is_td,expect", [
    ("2026-11-16T02:20", True, "2026-11-13"),   # Monday before the open -> Friday
    ("2026-11-16T15:59", True, "2026-11-13"),   # Monday, market still open -> Friday
    ("2026-11-16T16:00", True, "2026-11-16"),   # Monday after the close -> Monday
    ("2026-11-15T12:00", False, "2026-11-13"),  # Sunday -> Friday
])
def test_past_trading_day(now, is_td, expect):
    d = run.past_trading_day(datetime.fromisoformat(now).replace(tzinfo=ET), lambda d: is_td, lambda d: date(2026, 11, 13))
    assert d.isoformat() == expect


def test_mode_past_day_writes_rerun_summary(tmp_path, monkeypatch):
    from src import alerts
    monkeypatch.setattr(alerts, "folder", lambda: tmp_path)
    seen = []
    def past_scan(d):
        seen.append(d)
        return _out()
    code = run.main(["--mode", "past_day", "--now", "2026-11-16T02:20"], trading_day_fn=lambda d: True,
                    prior_day_fn=lambda d: date(2026, 11, 13), past_scan_fn=past_scan)
    assert code == 0 and seen == [date(2026, 11, 13)]
    t = next(tmp_path.glob("2026/11/2026-11-16_0220_scan_summary.md")).read_text()
    assert t.startswith("# Manual re-run for 2026-11-13: 1 Tier A, 1 Tier B") and "mode: past_day" in t


def test_mode_past_day_failure_is_a_failure_alert(monkeypatch):
    sent = []
    monkeypatch.setattr(run.alerts, "send", lambda kind, subject, body, now: sent.append((kind, subject)))
    def boom(d):
        raise ConnectionError("Alpaca down")
    code = run.main(["--mode", "past_day", "--now", "2026-11-16T02:20"], trading_day_fn=lambda d: True,
                    prior_day_fn=lambda d: date(2026, 11, 13), past_scan_fn=boom)
    assert code == 1 and sent[0][0] == "scanner_failed" and "past_day" in sent[0][1]


def test_scheduled_runs_default_to_normal_mode():
    import yaml
    wf = yaml.safe_load(open(Path(__file__).resolve().parent.parent / ".github/workflows/scan.yml"))
    on = wf.get("on", wf.get(True))  # YAML 1.1 reads the key `on` as True
    assert on["workflow_dispatch"]["inputs"]["mode"]["options"] == ["normal", "test_message", "past_day"]
    step = next(s for s in wf["jobs"]["scan"]["steps"] if s.get("name", "").startswith("Scan"))
    assert '--mode "${MODE:-normal}"' in step["run"] and step["env"]["MODE"] == "${{ inputs.mode }}"
