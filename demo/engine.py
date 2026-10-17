"""Daily bars -> PTIS MarketSnapshot -> PTIS StrategyMatcher. The ranking and the condition checklist are produced by
the public PTIS strategy engine itself; this module only prepares its inputs from end-of-day data.

Causality: everything for session t is computed from rows dated <= t (indicators are recursive/rolling over the
past only), and the paper trader acts on the NEXT session's open.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from demo import guard  # noqa: F401  (isolation first)

import strategy_engine.conditions.candle_conditions  # noqa: F401  (conditions self-register on import)
import strategy_engine.conditions.indicator_conditions  # noqa: F401
import strategy_engine.conditions.price_conditions  # noqa: F401
import strategy_engine.conditions.structure_conditions  # noqa: F401
import strategy_engine.conditions.volume_conditions  # noqa: F401
from core.enums import MarketRegime, TradeDirection
from strategy_engine.conditions.base_condition import MarketSnapshot, TradeContext
from strategy_engine.indicators import IndicatorEngine
from strategy_engine.regime_detector import MarketRegimeDetector
from strategy_engine.strategy_matcher import StrategyMatcher, StrategyMatchResult
from strategy_engine.strategy_registry import StrategyRegistry

logging.getLogger("strategy_engine").setLevel(logging.WARNING)

STRATEGY_DIR = Path(__file__).resolve().parent / "strategy"
STRATEGY_ID = "demo_ema_pullback_daily"
MIN_BARS = 60
REGIME_WINDOW = 120


def load_registry() -> StrategyRegistry:
    reg = StrategyRegistry(str(STRATEGY_DIR))
    reg.initialize()
    if reg.get(STRATEGY_ID) is None:
        raise RuntimeError(f"strategy {STRATEGY_ID} did not load from {STRATEGY_DIR}")
    return reg


def add_indicators(g: pd.DataFrame) -> pd.DataFrame:
    """Per-symbol indicators via PTIS's IndicatorEngine (all causal: EMA/Wilder recursions and trailing windows)."""
    g = g.sort_values("date").reset_index(drop=True).copy()
    ie = IndicatorEngine()
    for p in (9, 20, 50, 200):
        g[f"ema_{p}"] = ie.ema(g["close"], p)
    g["atr_14"] = ie.atr(g, 14)
    g["rsi_14"] = ie.rsi(g["close"], 14)
    g["avg_volume_20"] = g["volume"].rolling(20, min_periods=10).mean().shift(1)
    return g


_regime = MarketRegimeDetector()


def regime_at(g: pd.DataFrame, i: int) -> tuple[MarketRegime, float, str]:
    window = g.iloc[max(0, i - REGIME_WINDOW + 1): i + 1][["open", "high", "low", "close", "volume"]]
    if len(window) < 50:
        return MarketRegime.UNKNOWN, 0.0, "not enough history"
    try:
        r = _regime.detect(window.reset_index(drop=True))
        return r.regime, float(r.confidence), r.description
    except Exception as e:                                # the detector is strict about inputs; never crash a build
        return MarketRegime.UNKNOWN, 0.0, f"regime unavailable ({type(e).__name__})"


def snapshot_at(g: pd.DataFrame, i: int, regime: MarketRegime) -> MarketSnapshot:
    row = g.iloc[i]
    recent = g.iloc[max(0, i - 29): i + 1].iloc[::-1]       # most recent first, as PTIS expects
    candles = [{"open": r.open, "high": r.high, "low": r.low, "close": r.close, "volume": r.volume,
                "timestamp": r.date.isoformat()} for r in recent.itertuples()]
    ind = {k: float(row[k]) for k in ("ema_9", "ema_20", "ema_50", "ema_200", "atr_14", "rsi_14")
           if pd.notna(row[k])}
    avg_vol = float(row["avg_volume_20"]) if pd.notna(row["avg_volume_20"]) else None
    prev = g.iloc[i - 1] if i > 0 else row
    return MarketSnapshot(
        symbol=row["symbol"], timestamp=datetime.combine(row["date"].date(), datetime.min.time()),
        open=row["open"], high=row["high"], low=row["low"], close=row["close"], volume=row["volume"],
        indicators=ind, recent_candles=candles,
        prev_day_high=float(prev["high"]), prev_day_low=float(prev["low"]), prev_day_close=float(prev["close"]),
        # daily bars: the session's full range stands in for the intraday opening range
        opening_range_high=float(row["high"]), opening_range_low=float(row["low"]),
        avg_volume=avg_vol, relative_volume=(row["volume"] / avg_vol) if avg_vol else None,
        regime=regime,
    )


@dataclass
class Evaluation:
    symbol: str
    date: pd.Timestamp
    close: float
    regime: MarketRegime
    regime_confidence: float
    regime_note: str
    result: StrategyMatchResult

    def to_dict(self) -> dict:
        d = self.result.to_dict()
        return {"symbol": self.symbol, "date": f"{self.date:%Y-%m-%d}", "close": round(self.close, 2),
                "regime": self.regime.value, "regime_confidence": round(self.regime_confidence, 2),
                "regime_note": self.regime_note, "score": d["score"], "valid": d["is_valid_match"],
                "required_met": d["required_met"], "required_total": d["required_total"],
                "supporting_met": d["supporting_met"], "supporting_total": d["supporting_total"],
                "avoid_triggered": d["avoid_triggered"], "disqualified": d["disqualified"],
                "disqualification_reason": d["disqualification_reason"], "conditions": d["conditions"]}


class Scanner:
    def __init__(self, registry: StrategyRegistry | None = None):
        self.registry = registry or load_registry()
        self.matcher = StrategyMatcher(self.registry)

    def evaluate(self, g: pd.DataFrame, i: int) -> Evaluation | None:
        if i < MIN_BARS - 1:
            return None
        regime, conf, note = regime_at(g, i)
        snap = snapshot_at(g, i, regime)
        row = g.iloc[i]
        trade = TradeContext(symbol=row["symbol"], direction=TradeDirection.LONG, entry_price=float(row["close"]),
                             entry_time=snap.timestamp, position_size=1.0, market_regime=regime)
        res = self.matcher.match_single(STRATEGY_ID, trade, snap)
        return Evaluation(row["symbol"], row["date"], float(row["close"]), regime, conf, note, res)


def rank(evals: list[Evaluation]) -> list[Evaluation]:
    """Valid matches first, by the matcher's score; then the rest by score (near misses are informative too)."""
    return sorted(evals, key=lambda e: (not e.result.is_valid_match, -e.result.match_score, e.symbol))


def frames(panel: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {s: add_indicators(g) for s, g in panel.groupby("symbol")}


def swing_low_stop(g: pd.DataFrame, i: int, lookback: int, buffer_atr: float) -> float | None:
    lo = g["low"].iloc[max(0, i - lookback + 1): i + 1].min()
    atr = g["atr_14"].iloc[i]
    if not np.isfinite(lo) or not np.isfinite(atr):
        return None
    return float(lo - buffer_atr * atr)
