from __future__ import annotations

from src import github_issues as G


def test_new_message_files_only_new_md_and_never_latest():
    status = "?? messages/2026/11/2026-11-17_0915_shortlist.md\n M messages/LATEST.md\n?? messages/2026/11/2026-11-17_1030_scanner_failed.md\n M data/candidates.csv\n"
    files = G.new_message_files(git=lambda *a: status)
    assert files == ["messages/2026/11/2026-11-17_0915_shortlist.md", "messages/2026/11/2026-11-17_1030_scanner_failed.md"]


def test_kind_of():
    assert G.kind_of("messages/2026/11/2026-11-17_0915_no_trade.md") == "no_trade"
    assert G.kind_of("messages/2026/11/2026-11-17_0915_scanner_failed_2.md") == "scanner_failed"


def test_issue_body_drops_title_adds_link_and_mention():
    body = G.issue_body("# Shortlist 2026-11-17: 1 Tier A\n\n> note\n", "messages/2026/11/x.md", "https://github.com", "o/r", "someone")
    assert body.startswith("> note") and "[messages/2026/11/x.md](https://github.com/o/r/blob/main/messages/2026/11/x.md)" in body
    assert body.rstrip().endswith("cc @someone")
    assert "cc @" not in G.issue_body("# t\n\nb", "p.md", "", "", None)


def test_issue_body_truncated_under_limit():
    body = G.issue_body("# t\n\n" + "x" * 100_000, "p.md", "", "", None)
    assert len(body) <= G.MAX_BODY and "truncated" in body


def test_open_issues_calls_gh(tmp_path, monkeypatch):
    monkeypatch.setattr(G, "ROOT", tmp_path)
    p = tmp_path / "messages/2026/11/2026-11-17_0915_shortlist.md"
    p.parent.mkdir(parents=True)
    p.write_text("# Shortlist 2026-11-17: 1 Tier A, 0 Tier B, 0 Watch\n\nbody\n")
    calls = []
    n = G.open_issues(["messages/2026/11/2026-11-17_0915_shortlist.md"], run=calls.append, env={})
    assert n == 1 and calls[0][:4] == ["gh", "label", "create", "shortlist"]
    assert calls[1][:4] == ["gh", "issue", "create", "--title"] and calls[1][4] == "Shortlist 2026-11-17: 1 Tier A, 0 Tier B, 0 Watch"
    assert calls[1][-2:] == ["--label", "shortlist"]


def test_open_with_empty_list_does_nothing(tmp_path):
    f = tmp_path / "list.txt"
    f.write_text("\n")
    assert G.main(["open", "--list", str(f)]) == 0


def test_test_message_becomes_a_labelled_test_issue(tmp_path, monkeypatch):
    monkeypatch.setattr(G, "ROOT", tmp_path)
    p = tmp_path / "messages/2026/11/2026-11-17_0320_test.md"
    p.parent.mkdir(parents=True)
    p.write_text("# TEST: notification check 2026-11-17 03:20 ET\n\n> **This is a TEST.**\n")
    calls = []
    G.open_issues(["messages/2026/11/2026-11-17_0320_test.md"], run=calls.append, env={"NOTIFY_USER": "me"})
    title = calls[1][calls[1].index("--title") + 1]
    assert title == "TEST: notification check 2026-11-17 03:20 ET" and calls[1][-2:] == ["--label", "test"]
