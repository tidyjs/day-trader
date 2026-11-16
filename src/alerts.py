"""All communications as files in the repo (SPEC 8, changed 2026-11-16 from
email to files at the user's request).

Every message is a Markdown file under messages/, committed back by the
workflow, so it can be read on GitHub (web or mobile app):

  messages/YYYY/MM/YYYY-MM-DD_HHMM_<kind>.md   one file per message
  messages/LATEST.md                           newest message in full, then
                                               links to the 30 before it

Kinds: scanner_failed and scan_summary (now; scan_summary is interim), and
shortlist, no_trade, recap (M5).

GitHub does not notify you about commits to your own repo. A failure also
makes the workflow run fail (non-zero exit), which GitHub does notify.
"""
from __future__ import annotations

import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from src.config import ROOT

TITLES = {"scanner_failed": "Scanner failed", "shortlist": "Morning shortlist", "no_trade": "No trade today",
          "recap": "Post-close recap", "scan_summary": "Scan summary (interim, until M5)", "test": "Test message"}
KEEP_IN_LATEST = 30


def folder() -> Path:
    return ROOT / "messages"


def message_path(kind: str, now: datetime, root: Optional[Path] = None) -> Path:
    root = root or folder()
    return root / f"{now:%Y}" / f"{now:%m}" / f"{now:%Y-%m-%d_%H%M}_{kind}.md"


def write(kind: str, subject: str, body: str, now: datetime, root: Optional[Path] = None) -> Path:
    """Write one message file and refresh LATEST.md. Returns the file path."""
    root = root or folder()
    p = message_path(kind, now, root)
    p.parent.mkdir(parents=True, exist_ok=True)
    n = 2
    while p.exists():  # two messages of one kind in the same minute: keep both
        p = p.with_name(f"{now:%Y-%m-%d_%H%M}_{kind}_{n}.md")
        n += 1
    p.write_text(
        f"# {subject}\n\n"
        f"- kind: `{kind}` ({TITLES.get(kind, kind)})\n"
        f"- time: {now:%Y-%m-%d %H:%M} New York ({now.isoformat()})\n\n"
        f"{body.rstrip()}\n"
    )
    update_latest(root)
    print(f"MESSAGE [{kind}] {subject} -> {p.relative_to(root.parent) if root.parent in p.parents else p}")
    return p


def all_messages(root: Optional[Path] = None) -> List[Path]:
    root = root or folder()
    return sorted((p for p in root.glob("*/*/*.md")), key=lambda p: p.name, reverse=True)


def update_latest(root: Optional[Path] = None) -> Path:
    root = root or folder()
    msgs = all_messages(root)
    out = ["# Latest messages\n", "Newest first. Every message is also kept as its own file under `messages/YYYY/MM/`.\n"]
    if msgs:
        newest = msgs[0]
        text = newest.read_text()
        text = "### " + text[2:] if text.startswith("# ") else text  # demote its title under ours
        out += [f"## Newest: [{newest.name}]({newest.relative_to(root).as_posix()})\n", text, ""]
        if len(msgs) > 1:
            out.append("## Earlier\n")
            for m in msgs[1:KEEP_IN_LATEST + 1]:
                first = m.read_text().splitlines()[0].lstrip("# ")
                out.append(f"- [{m.name}]({m.relative_to(root).as_posix()}): {first}")
    p = root / "LATEST.md"
    p.write_text("\n".join(out).rstrip() + "\n")
    return p


def already_sent_today(kind: str, now: datetime, root: Optional[Path] = None) -> bool:
    root = root or folder()
    return any((root / f"{now:%Y}" / f"{now:%m}").glob(f"{now:%Y-%m-%d}_*_{kind}*.md"))


def send(kind: str, subject: str, body: str, now: datetime) -> Path:
    """Kept as the single entry point for every communication."""
    return write(kind, subject, body, now)


def failure_body(exc: BaseException, context: str) -> str:
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-4000:]
    return f"{context}\n\n**{type(exc).__name__}: {exc}**\n\n```\n{tb.rstrip()}\n```"
