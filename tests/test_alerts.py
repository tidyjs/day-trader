"""Messages are files under messages/ (SPEC 8)."""
from __future__ import annotations

from datetime import datetime

from src import alerts
from src.timeutil import ET

NOW = datetime(2026, 11, 16, 9, 15, tzinfo=ET)


def test_message_file_path_and_content(tmp_path):
    p = alerts.write("scanner_failed", "Scanner failed 2026-11-16", "boom", NOW, tmp_path)
    assert p == tmp_path / "2026" / "11" / "2026-11-16_0915_scanner_failed.md"
    t = p.read_text()
    assert t.startswith("# Scanner failed 2026-11-16") and "kind: `scanner_failed`" in t and "boom" in t
    assert "2026-11-16 09:15 New York" in t


def test_same_minute_messages_are_both_kept(tmp_path):
    a = alerts.write("scanner_failed", "first", "1", NOW, tmp_path)
    b = alerts.write("scanner_failed", "second", "2", NOW, tmp_path)
    assert a != b and a.exists() and b.exists() and b.name.endswith("_scanner_failed_2.md")


def test_latest_shows_newest_in_full_and_links_earlier(tmp_path):
    alerts.write("test", "Older", "old body", NOW, tmp_path)
    alerts.write("scanner_failed", "Newer", "new body", NOW.replace(minute=16), tmp_path)
    latest = (tmp_path / "LATEST.md").read_text()
    assert latest.index("Newer") < latest.index("Older")
    assert "### Newer" in latest and "new body" in latest              # newest in full
    assert "](2026/11/2026-11-16_0915_test.md): Older" in latest       # earlier as a link
    assert "old body" not in latest


def test_already_sent_today(tmp_path, monkeypatch):
    monkeypatch.setattr(alerts, "folder", lambda: tmp_path)
    assert not alerts.already_sent_today("scanner_failed", NOW)
    alerts.write("scanner_failed", "x", "y", NOW, tmp_path)
    assert alerts.already_sent_today("scanner_failed", NOW)
    assert not alerts.already_sent_today("scanner_failed", NOW.replace(day=17))
    assert not alerts.already_sent_today("shortlist", NOW)


def test_failure_body_has_error_and_traceback():
    try:
        raise ValueError("bad input")
    except ValueError as e:
        body = alerts.failure_body(e, "Morning scan failed.")
    assert "**ValueError: bad input**" in body and "Traceback" in body
