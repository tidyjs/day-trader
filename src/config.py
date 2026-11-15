from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_env(path: Optional[Path] = None) -> None:
    """Load KEY=VALUE lines from .env without overriding real env vars."""
    env = path or ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_config(path: Optional[Path] = None) -> Dict[str, Any]:
    with open(path or ROOT / "config.yaml") as f:
        return yaml.safe_load(f)
