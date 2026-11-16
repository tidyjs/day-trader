"""Open a GitHub Issue for every new message file (SPEC 8, 2026-11-16).

Run inside the workflow, which provides the `gh` CLI and the built-in token
(GH_TOKEN = github.token, permission `issues: write`). No new secrets.

  python -m src.github_issues list                 # new message files, one per line
  python -m src.github_issues open --list FILE     # one issue per listed file

If the repository variable NOTIFY_USER is set (a GitHub username, not a
secret), the issue body ends with "cc @NOTIFY_USER", which makes GitHub send
that user a "mentioned" notification by email and to GitHub Mobile.

Any failure exits non-zero, so the workflow run fails and GitHub reports it.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, List, Optional

from src.config import ROOT

MAX_BODY = 60000  # GitHub's limit is 65,536 characters
LABELS = {"shortlist": "shortlist", "no_trade": "no-names", "scanner_failed": "scanner-failed", "test": "test", "recap": "recap"}


def new_message_files(git: Callable[..., str] = None) -> List[str]:
    """Message files added since the last commit (never LATEST.md)."""
    git = git or (lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, check=True).stdout)
    out = git("status", "--porcelain=v1", "--untracked-files=all", "--", "messages/")
    files = []
    for line in out.splitlines():
        code, path = line[:2], line[3:].strip()
        if ("?" in code or "A" in code) and path.endswith(".md") and not path.endswith("LATEST.md"):
            files.append(path)
    return sorted(files)


def kind_of(path: str) -> str:
    m = re.search(r"_\d{4}_([a-z_]+?)(?:_\d+)?\.md$", path)
    return m.group(1) if m else "message"


def issue_body(text: str, path: str, server: str, repo: str, notify: Optional[str]) -> str:
    body = text.split("\n", 1)[1].lstrip("\n") if text.startswith("# ") else text  # the title is the issue title
    link = f"{server}/{repo}/blob/main/{path}" if server and repo else path
    footer = f"\n\n---\nFile: [{path}]({link})"
    if notify:
        footer += f"\n\ncc @{notify.lstrip('@')}"
    if len(body) + len(footer) > MAX_BODY:
        body = body[: MAX_BODY - len(footer) - 40] + "\n\n…(truncated; see the file)"
    return body + footer


def open_issues(paths: List[str], run: Callable[[List[str]], None] = None, env: Optional[dict] = None) -> int:
    env = env if env is not None else os.environ
    run = run or (lambda cmd: subprocess.run(cmd, cwd=ROOT, check=True))
    server, repo, notify = env.get("GITHUB_SERVER_URL", ""), env.get("GITHUB_REPOSITORY", ""), env.get("NOTIFY_USER") or None
    labels_made = set()
    for path in paths:
        text = (ROOT / path).read_text()
        title = text.splitlines()[0].lstrip("# ").strip() if text else path
        label = LABELS.get(kind_of(path), "message")
        if label not in labels_made:  # idempotent; keeps issues filterable by kind
            run(["gh", "label", "create", label, "--force", "--description", "day-trader message"])
            labels_made.add(label)
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(issue_body(text, path, server, repo, notify))
        run(["gh", "issue", "create", "--title", title, "--body-file", f.name, "--label", label])
        print(f"[issues] opened: {title}")
    return len(paths)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    o = sub.add_parser("open")
    o.add_argument("--list", required=True, type=Path)
    a = ap.parse_args(argv)
    if a.cmd == "list":
        print("\n".join(new_message_files()))
        return 0
    paths = [p.strip() for p in a.list.read_text().splitlines() if p.strip()] if a.list.exists() else []
    if not paths:
        print("[issues] no new messages")
        return 0
    open_issues(paths)
    return 0


if __name__ == "__main__":
    sys.exit(main())
