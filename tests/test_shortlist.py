"""M5 message format (src/shortlist.py)."""
from __future__ import annotations

from src import shortlist as SL
from src.config import load_config

CFG = load_config()
RULES = {c: "pass" for c, _ in SL.RULE_LABELS}


def row(sym, tier="", rank=None, pm=500_000.0, **kw):
    r = {"symbol": sym, "name": f"{sym} Inc. Common Stock", "date": "2026-11-13", "data_cutoff_et": "2026-11-13T08:59:00-05:00",
         "price": 1.25, "prior_close": 1.0, "gap_pct": 25.0, "pm_high": 1.40, "pm_high_last60": 1.30, "pm_dollar_volume": pm,
         "pm_trades": 900, "float_shares": 12e6, "float_source": "yahoo", "catalyst_type": "earnings", "catalyst_quality": 4,
         "catalyst_summary": "Q3 beat", "catalyst_votes": "3/3 runs agree", "tier": tier, "shortlist_rank": rank, "score": 55.0 if tier else None,
         "warnings": "", "evidence": "", "dq_reasons": "", **RULES}
    r.update(kw)
    return r


def out(rows):
    return {"summary": {"candidates": len(rows), "tiers": {"A": sum(r["tier"] == "A" for r in rows), "B": sum(r["tier"] == "B" for r in rows)}, "warnings": []},
            "candidates": rows}


def test_order_and_cap_tier_a_then_b_then_watch():
    rows = [row("B1", "B", 2), row("A1", "A", 1), row("B2", "B", 3), row("B3", "B", 4), row("B4", "B", 5), row("B5", "B", 6),
            row("W1", pm=9e6, rule_continuation="fail", watch_reason="other")]
    kind, subject, body = SL.build(out(rows), CFG)
    assert kind == "shortlist" and subject == "Shortlist 2026-11-13: 1 Tier A, 4 Tier B, 0 Watch"
    order = [l.split(". ")[1].split(":")[0] for l in body.splitlines() if l.startswith("### ")]
    assert order == ["A1", "B1", "B2", "B3", "B4"]  # 5 in total; B5 and W1 not shown
    assert "beyond the 5-name limit: B5" in body


def test_watch_fills_remaining_places_with_reason_banner():
    rows = [row("A1", "A", 1),
            row("W1", pm=2e6, rule_continuation="fail", rule_prior_range="fail", watch_reason="other"),
            row("W2", pm=9e6, dq_promo_or_no_catalyst="fail", dq_reasons="no verifiable catalyst, 3/3 runs and no prior-day volume surge (0.2x)",
                watch_reason="no_catalyst"),
            row("W3", pm=5e6, dq_promo_or_no_catalyst="fail", dq_reasons="classifier: promo/pump (2/3 runs) (x)", watch_reason="promo"),
            row("OFFR", pm=99e6, dq_offering="fail", dq_reasons="424B5 2026-11-12 company equity raise"),
            row("SPLT", pm=98e6, dq_reverse_split="fail", dq_reasons="8-K reverse split effective 2026-11-14"),
            row("THIN", rule_pm_dollar_volume="fail")]
    kind, subject, body = SL.build(out(rows), CFG)
    assert subject.endswith("1 Tier A, 0 Tier B, 3 Watch")
    assert body.index("### 2. W2") < body.index("### 3. W3") < body.index("### 4. W1")  # by premarket $ volume
    assert "> **WATCH: NO VERIFIABLE CATALYST** (and no prior-day volume surge)" in body
    assert "> **WATCH: PROMO / PUMP FLAGGED** by at least 2 of 3 classifier runs" in body
    assert "> **WATCH: in no tier** (see the rules line)" in body
    shown_part, not_shown = body.split("## Not shown")
    assert "OFFR" not in shown_part and "SPLT" not in shown_part
    assert "- excluded from Watch: offering disqualifier: OFFR" in not_shown
    assert "- excluded from Watch: pending reverse split: SPLT" in not_shown
    assert "rule_pm_dollar_volume: THIN" in not_shown


def test_no_levels_ever_appear():
    r = row("A1", "A", 1, trigger=1.41, stop=1.20, shares_measure=12.5, target_1_5r=1.7)
    body = SL.build(out([r]), CFG)[2].lower()
    for word in ("trigger", "stop ", "shares", "target", "1.41", "12.5"):
        assert word not in body, word


def test_required_note_and_both_highs():
    body = SL.build(out([row("A1", "A", 1)]), CFG)[2]
    assert "Levels use data up to about 08:59 ET. Re-check the live premarket high at the open." in body
    assert "**premarket high** 1.4 full session · 1.3 in the 60 minutes to the cutoff" in body
    assert "**float** 12.0M (yahoo)" in body and "(3/3 runs agree)" in body


def test_banners_for_split_and_merger_target():
    ev = "[reverse_split:possible] 6-K 2026-10-30 no effective date | \"...share consolidation...\" | https://www.sec.gov/x.htm"
    r = row("A1", "A", 1, evidence=ev, warnings="possible reverse split: 6-K 2026-10-30 mentions one, no effective date found; "
                                                "merger target: price likely pinned to deal terms; spread 3.4%")
    body = SL.build(out([r]), CFG)[2]
    assert "> **⚠️ REVERSE SPLIT POSSIBLY PENDING**: [6-K 2026-10-30 no effective date](https://www.sec.gov/x.htm)" in body
    assert "> **⚠️ MERGER TARGET: price likely pinned to deal terms**" in body
    assert "  - spread 3.4%" in body and "  - merger target" not in body  # banner instead of a duplicate warning


def test_completed_split_gets_no_banner():
    ev = "[reverse_split:completed] 6-K 2026-11-05 effective 2026-11-05 | \"...\" | https://www.sec.gov/y.htm"
    body = SL.build(out([row("A1", "A", 1, evidence=ev, warnings="reverse split completed 2026-11-05 (4 days ago, per 6-K 2026-11-05)")]), CFG)[2]
    assert "REVERSE SPLIT POSSIBLY PENDING" not in body and "reverse split completed 2026-11-05" in body


def test_rules_line_symbols():
    line = SL.rules_line(row("X", rule_continuation="fail", rule_float="", dq_offering="unknown"))
    assert "continuation ✗" in line and "float –" in line and "no offering ?" in line and "price ✓" in line


def test_no_names_today():
    kind, subject, body = SL.build(out([row("THIN", rule_pm_dollar_volume="fail")]), CFG)
    assert kind == "no_trade" and subject == "No names today (2026-11-13)" and "rule_pm_dollar_volume: THIN" in body


def test_failure_message():
    kind, subject, body = SL.failure("2026-11-16", "The morning scan failed.", "ConnectionError: x")
    assert kind == "scanner_failed" and subject == "Scanner failed 2026-11-16"
    assert body.startswith("> **No shortlist today.** The morning scan failed.") and "Do not use an earlier shortlist" in body
    assert "<details>" in body and "ConnectionError: x" in body


def test_scan_level_warnings_are_not_repeated_per_name():
    o = out([row("A1", "A", 1, warnings="T212 list is 3 days old; spread 3.4%")])
    o["summary"]["warnings"] = ["T212 list is 3 days old"]
    body = SL.build(o, CFG)[2]
    assert body.count("T212 list is 3 days old") == 1 and "  - spread 3.4%" in body


def test_illiquid_disqualified_name_is_not_called_excluded_from_watch():
    rows = [row("A1", "A", 1), row("LFMD", rule_pm_dollar_volume="fail", dq_offering="fail", dq_reasons="8-K item 3.02")]
    not_shown = SL.build(out(rows), CFG)[2].split("## Not shown")[1]
    assert "rule_pm_dollar_volume: LFMD" in not_shown and "excluded from Watch" not in not_shown
