"""Isolation guard for the demo. Imported before any PTIS code; refuses to run unless the process is clean.

The demo must never touch the private PTIS installation: its database, data lake, broker accounts, alerts or files.
This module (1) forces safe settings BEFORE `config.settings` is imported, and (2) checks for anything that could
point at private state. Any failure raises and the build stops.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # the ptis-demo repository
VENDOR = ROOT / "vendor" / "ptis"
DATA = ROOT / "data"

# keys that only exist in a real trading setup - none may be present in the demo's environment
FORBIDDEN_ENV_PREFIXES = ("ANGEL_", "UPSTOX_", "GROWW_", "KITE_", "ZERODHA_", "TELEGRAM_", "AWS_", "IBKR_",
                          "ALPACA_", "POLYGON_", "LLM_API_KEY", "GROQ_", "OPENAI_", "ANTHROPIC_")
PRIVATE_MARKERS = ("strategy_specs", "scripts/live", "research_warehouse", "research_bridge/hyp/specs")


class IsolationError(RuntimeError):
    pass


def _check() -> None:
    problems = []
    for name in (".env", ".env.test", ".env.prod", ".env.local"):
        if (ROOT / name).exists() or (Path.cwd() / name).exists():
            problems.append(f"an {name} file is present (the demo has no secrets and reads none)")
    for key in os.environ:
        if key.upper().startswith(FORBIDDEN_ENV_PREFIXES):
            problems.append(f"environment variable {key} is set (no broker/alert/cloud/LLM keys in the demo)")
    db = os.environ.get("DATABASE_URL", "")
    if db and not db.startswith("sqlite"):
        problems.append(f"DATABASE_URL points at a server ({db.split('@')[-1][:40]}); the demo uses in-memory SQLite")
    for entry in sys.path:
        p = Path(entry or ".").resolve()
        if any((p / m).exists() for m in PRIVATE_MARKERS):
            problems.append(f"sys.path contains the private repository: {p}")
    if not (VENDOR / "strategy_engine").is_dir():
        problems.append("vendor/ptis is missing - run scripts/sync_vendor.py from the public export")
    if problems:
        raise IsolationError("demo isolation check failed:\n  - " + "\n  - ".join(problems))


def activate() -> None:
    """Force safe settings, verify isolation, and put the vendored PUBLIC PTIS on sys.path."""
    os.environ["PTIS_ENV"] = "demo"                     # -> settings would read ".env", which _check forbids
    os.environ.setdefault("DATABASE_URL", "sqlite://")  # in-memory; never the local Postgres
    os.environ["LAKE_PATH"] = str(DATA / "lake")
    _check()
    if str(VENDOR) not in sys.path:
        sys.path.insert(0, str(VENDOR))


activate()
