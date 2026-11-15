from __future__ import annotations

from datetime import date, datetime

from src.data import halts
from src.timeutil import ET

XML = """<?xml version="1.0"?><rss xmlns:ndaq="http://www.nasdaqtrader.com/"><channel>
<item><title>AAA</title><ndaq:HaltDate>11/13/2026</ndaq:HaltDate><ndaq:HaltTime>08:40:00.000</ndaq:HaltTime>
<ndaq:IssueSymbol>AAA</ndaq:IssueSymbol><ndaq:Market>NASDAQ</ndaq:Market><ndaq:ReasonCode>T1</ndaq:ReasonCode>
<ndaq:ResumptionDate /><ndaq:ResumptionTradeTime /></item>
<item><title>BBB</title><ndaq:HaltDate>11/13/2026</ndaq:HaltDate><ndaq:HaltTime>08:00:00.000</ndaq:HaltTime>
<ndaq:IssueSymbol>BBB</ndaq:IssueSymbol><ndaq:Market>AMEX</ndaq:Market><ndaq:ReasonCode>LUDP</ndaq:ReasonCode>
<ndaq:ResumptionDate>11/13/2026</ndaq:ResumptionDate><ndaq:ResumptionTradeTime>08:05:00.000</ndaq:ResumptionTradeTime></item>
<item><title>CCC</title><ndaq:HaltDate>11/13/2026</ndaq:HaltDate><ndaq:HaltTime>10:00:00.000</ndaq:HaltTime>
<ndaq:IssueSymbol>CCC</ndaq:IssueSymbol><ndaq:Market>NYSE</ndaq:Market><ndaq:ReasonCode>T1</ndaq:ReasonCode>
<ndaq:ResumptionDate /><ndaq:ResumptionTradeTime /></item>
</channel></rss>"""

DAY = date(2026, 11, 13)
AS_OF = datetime(2026, 11, 13, 9, 15, tzinfo=ET)
FEED = {"fetched_at": AS_OF.isoformat(), "ok": True, "items": halts.parse(XML), "error": None}


def test_parse_strips_namespace_and_empty_tags():
    items = halts.parse(XML)
    assert [i["IssueSymbol"] for i in items] == ["AAA", "BBB", "CCC"]
    assert items[0]["ResumptionTradeTime"] == "" and items[1]["Market"] == "AMEX"


def test_active_halt_is_reported_with_time():
    assert halts.status(FEED, "AAA", DAY, AS_OF) == "halted at 11-13 08:40:00 ET (reason T1)"


def test_resumed_and_future_halts_are_not_halted():
    assert halts.status(FEED, "BBB", DAY, AS_OF) is None   # resumed 08:05
    assert halts.status(FEED, "CCC", DAY, AS_OF) is None   # halts after the scan time
    assert halts.status(FEED, "ZZZ", DAY, AS_OF) is None


def test_feed_failure_or_missing_is_unknown_never_silent():
    bad = {"fetched_at": AS_OF.isoformat(), "ok": False, "items": [], "error": "HTTPError: 503"}
    assert "unknown" in halts.status(bad, "AAA", DAY, AS_OF) and "503" in halts.status(bad, "AAA", DAY, AS_OF)
    assert "unknown" in halts.status(None, "AAA", DAY, AS_OF)


def test_historical_run_is_unknown():
    later = dict(FEED, fetched_at=datetime(2026, 11, 15, 10, tzinfo=ET).isoformat())
    assert "historical run" in halts.status(later, "AAA", DAY, AS_OF)


def test_parse_handles_utf8_bom_bytes():
    assert len(halts.parse(b"\xef\xbb\xbf" + XML.encode())) == 3
    assert len(halts.parse("﻿" + XML)) == 3
