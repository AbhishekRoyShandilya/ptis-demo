"""Demo safety tests: isolation, corporate-action adjustment, and a truncation (no look-ahead) test."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from demo import guard  # noqa: E402
from demo import eod  # noqa: E402


# ── isolation ────────────────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("env", [{"TELEGRAM_BOT_TOKEN": "x"}, {"ANGEL_API_KEY": "x"},
                                 {"DATABASE_URL": "postgresql://ptis:ptis@localhost:5432/ptis"}])
def test_guard_refuses_private_state(env):
    clean = {k: v for k, v in os.environ.items() if not k.upper().startswith(guard.FORBIDDEN_ENV_PREFIXES)
             and k != "DATABASE_URL"}
    r = subprocess.run([sys.executable, "-c", "import demo.guard"], cwd=ROOT, env={**clean, **env},
                       capture_output=True, text=True)
    assert r.returncode != 0 and "isolation check failed" in r.stderr


def test_guard_forces_in_memory_database():
    assert os.environ["DATABASE_URL"].startswith("sqlite")
    assert Path(os.environ["LAKE_PATH"]).resolve().is_relative_to(ROOT)


# ── corporate actions ────────────────────────────────────────────────────────────────────────────────────────────
def _write_sessions(tmp_path, rows):
    for d, g in pd.DataFrame(rows).groupby("date"):
        g.to_parquet(tmp_path / f"{d}.parquet", index=False)


def test_split_is_adjusted_but_a_real_crash_is_not(tmp_path, monkeypatch):
    rows = []
    for i, d in enumerate(pd.bdate_range("2026-01-01", periods=6)):
        split = i >= 3                        # 1:2 split from day 3 -> prices halve
        crash = i >= 4                        # a real 30% fall on day 4 for the other stock
        rows.append(dict(date=d.date(), symbol="AAA", isin="X1", open=50 if split else 100, high=51 if split else 101,
                         low=49 if split else 99, close=50 if split else 100, prev_close=100, volume=1000, value=0))
        rows.append(dict(date=d.date(), symbol="BBB", isin="X2", open=70 if crash else 100, high=71 if crash else 101,
                         low=69 if crash else 99, close=70 if crash else 100, prev_close=100, volume=1000, value=0))
    _write_sessions(tmp_path, rows)
    monkeypatch.setattr(eod, "EOD_DIR", tmp_path)
    monkeypatch.setattr(eod, "load_universe", lambda refresh=False: ["AAA", "BBB"])
    panel, adjustments = eod.build_panel()
    assert [(a["symbol"], a["ratio"]) for a in adjustments] == [("AAA", 0.5)]
    aaa = panel[panel.symbol == "AAA"]
    assert aaa["close"].round(6).nunique() == 1              # history scaled to the post-split level
    assert aaa["volume"].iloc[0] == 2000                     # volume scaled the other way
    bbb = panel[panel.symbol == "BBB"]
    assert bbb["close"].iloc[0] == 100 and bbb["close"].iloc[-1] == 70


# ── no look-ahead: decisions made with data up to T must not change when later data exists ────────────────────────
@pytest.mark.skipif(not eod.PANEL_FILE.exists(), reason="run `python -m demo.eod` first")
def test_truncation_paper_trader_is_causal():
    from demo import paper
    from demo.engine import frames

    panel = pd.read_parquet(eod.PANEL_FILE)
    keep = sorted(panel["symbol"].unique())[:10]
    panel = panel[panel["symbol"].isin(keep)]
    cut = pd.Timestamp("2026-06-15")
    full = paper.run(frames(panel))
    trunc = paper.run(frames(panel[panel["date"] <= cut]))

    def upto(rows, key):
        return [r for r in rows if pd.Timestamp(r[key]) <= cut]

    assert upto(full["signals"], "date") == trunc["signals"]
    assert upto(full["closed"], "exit_date") == trunc["closed"]
    assert upto(full["equity_curve"], "date") == trunc["equity_curve"]
    assert len(trunc["signals"]) > 0, "the test window must contain signals to be meaningful"


@pytest.mark.skipif(not eod.PANEL_FILE.exists(), reason="run `python -m demo.eod` first")
def test_truncation_test_catches_a_planted_leak(monkeypatch):
    """Positive control: the same comparison must FAIL when an indicator peeks at the future."""
    from demo import engine, paper

    real = engine.add_indicators

    def leaky(g):
        g = real(g)
        g["ema_20"] = g["close"].rolling(21, center=True, min_periods=1).mean()   # uses the next 10 sessions
        return g

    monkeypatch.setattr(engine, "add_indicators", leaky)
    panel = pd.read_parquet(eod.PANEL_FILE)
    panel = panel[panel["symbol"].isin(sorted(panel["symbol"].unique())[:10])]
    cut = pd.Timestamp("2026-06-15")
    full = paper.run(engine.frames(panel))
    trunc = paper.run(engine.frames(panel[panel["date"] <= cut]))
    same_signals = [r for r in full["signals"] if pd.Timestamp(r["date"]) <= cut] == trunc["signals"]
    same_equity = [r for r in full["equity_curve"] if pd.Timestamp(r["date"]) <= cut] == trunc["equity_curve"]
    assert not (same_signals and same_equity), "the truncation test failed to detect a planted look-ahead"
