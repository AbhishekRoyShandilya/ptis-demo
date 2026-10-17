"""Daily paper trader for the demo strategy, built on PTIS's PositionSizer and CostModel.

Rules (all causal):
- A signal is formed on session t's close (the scanner sees rows <= t). Entry is at session t+1's OPEN.
- Stop = swing low of the last 10 sessions minus 0.25 ATR (from the template). If t+1 opens at/below the stop,
  the trade is skipped ("gapped through stop").
- Size from PTIS PositionSizer: 1% risk, drawdown scaling, portfolio-heat cap; never more than the free cash.
- Exits per daily bar, in this order: gap below stop -> exit at open; low <= stop -> exit at stop; otherwise half at
  1.5R and the rest at 3R; after 20 sessions -> exit at close. If a bar touches both the stop and a target, the
  STOP is assumed to come first (daily bars cannot tell; this is the conservative choice).
- Costs: PTIS CostModel with delivery-equity parameters (STT on both legs folded into the sell side, 5 bps slippage
  per side).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from demo import guard  # noqa: F401
from demo.config import MAX_POSITIONS, PAPER_START, VIRTUAL_CAPITAL
from demo.engine import Evaluation, Scanner, rank, swing_low_stop

from analytics.charges import CostModel
from core.enums import VolatilityRegime
from strategy_engine.position_sizer import PositionSizer

STOP_LOOKBACK, STOP_BUFFER_ATR = 10, 0.25
T1_R, T2_R, MAX_SESSIONS = 1.5, 3.0, 20

DELIVERY_COSTS = CostModel(brokerage_pct=0.0, brokerage_cap=0.0, stt_sell_pct=0.002, exch_txn_pct=0.0000297,
                           sebi_pct=0.000001, stamp_buy_pct=0.00015, gst_pct=0.18, slippage_bps=5.0)


@dataclass
class Position:
    symbol: str
    entry_date: pd.Timestamp
    entry: float
    qty: int
    stop: float
    risk_per_share: float
    signal_score: float
    qty_left: int = 0
    half_taken: bool = False
    sessions: int = 0
    realised: float = 0.0
    fills: list = field(default_factory=list)

    @property
    def t1(self) -> float:
        return self.entry + T1_R * self.risk_per_share

    @property
    def t2(self) -> float:
        return self.entry + T2_R * self.risk_per_share


def _sell(p: Position, qty: int, price: float, date: pd.Timestamp, reason: str) -> None:
    qty = min(qty, p.qty_left)
    if qty <= 0:
        return
    cost = DELIVERY_COSTS.round_trip_cost(p.entry, price, qty)
    p.realised += (price - p.entry) * qty - cost
    p.qty_left -= qty
    p.fills.append({"date": f"{date:%Y-%m-%d}", "qty": qty, "price": round(price, 2), "reason": reason,
                    "cost": round(cost, 2)})


def run(frames: dict[str, pd.DataFrame], scanner: Scanner | None = None) -> dict:
    scanner = scanner or Scanner()
    sizer = PositionSizer()
    dates = sorted({d for g in frames.values() for d in g["date"]})
    by_sym_idx = {s: {d: i for i, d in enumerate(g["date"])} for s, g in frames.items()}

    cash, peak = VIRTUAL_CAPITAL, VIRTUAL_CAPITAL
    open_pos: dict[str, Position] = {}
    closed: list[dict] = []
    equity_curve, skipped, signal_log = [], [], []
    pending: list[tuple[Evaluation, float]] = []          # (signal, stop) waiting for the next open
    last_evals: list[Evaluation] = []

    start = pd.Timestamp(PAPER_START)
    for d in dates:
        bar = {s: frames[s].iloc[by_sym_idx[s][d]] for s in frames if d in by_sym_idx[s]}

        # 1) entries at today's open, from yesterday's signals
        equity_prev = equity_curve[-1]["equity"] if equity_curve else VIRTUAL_CAPITAL
        for ev, stop in pending:
            s = ev.symbol
            if s in open_pos or s not in bar or len(open_pos) >= MAX_POSITIONS:
                continue
            o = float(bar[s]["open"])
            if o <= stop:
                skipped.append({"date": f"{d:%Y-%m-%d}", "symbol": s, "reason": "gapped through stop"})
                continue
            open_risk = sum(p.risk_per_share * p.qty_left for p in open_pos.values()) / equity_prev * 100
            size = sizer.compute(account_balance=equity_prev, entry=o, stop_loss=stop,
                                 atr=float(frames[s]["atr_14"].iloc[by_sym_idx[s][d]]),
                                 vol_regime=VolatilityRegime.AVERAGE,
                                 drawdown_pct=max(0.0, 1 - equity_prev / peak), open_risk_pct=open_risk)
            by_risk, by_cash = math.floor(size.shares), math.floor(cash / o)
            qty = int(min(by_risk, by_cash))
            if size.blocked or qty <= 0:
                if size.blocked:
                    reason = "sizer blocked: " + "; ".join(size.warnings)
                elif by_cash <= 0:
                    reason = "no free cash (capital already in open positions)"
                else:
                    reason = "risk budget allows 0 shares"
                skipped.append({"date": f"{d:%Y-%m-%d}", "symbol": s, "reason": reason})
                continue
            cash -= o * qty
            open_pos[s] = Position(s, d, o, qty, stop, o - stop, ev.result.match_score, qty_left=qty)
        pending = []

        # 2) manage open positions on today's bar
        for s, p in list(open_pos.items()):
            if s not in bar:
                continue
            b = bar[s]
            o, h, lo, c = float(b["open"]), float(b["high"]), float(b["low"]), float(b["close"])
            entered_today = p.entry_date == d
            if not entered_today and o <= p.stop:
                _sell(p, p.qty_left, o, d, "gap below stop")
            elif lo <= p.stop:
                _sell(p, p.qty_left, p.stop, d, "stop")
            else:
                if not p.half_taken and h >= p.t1:
                    _sell(p, p.qty // 2, max(p.t1, o) if not entered_today else p.t1, d, "target 1.5R")
                    p.half_taken = True
                if p.qty_left and h >= p.t2:
                    _sell(p, p.qty_left, max(p.t2, o) if not entered_today else p.t2, d, "target 3R")
            p.sessions += 1
            if p.qty_left and p.sessions >= MAX_SESSIONS:
                _sell(p, p.qty_left, c, d, "time exit (20 sessions)")
            if p.qty_left == 0:
                cash += p.realised + p.entry * p.qty
                closed.append({"symbol": s, "entry_date": f"{p.entry_date:%Y-%m-%d}", "entry": round(p.entry, 2),
                               "qty": p.qty, "stop": round(p.stop, 2), "exit_date": f"{d:%Y-%m-%d}",
                               "pnl": round(p.realised, 2), "r": round(p.realised / (p.risk_per_share * p.qty), 2),
                               "sessions": p.sessions, "signal_score": round(p.signal_score, 3), "fills": p.fills})
                del open_pos[s]

        # 3) mark to market
        mtm = sum(p.qty_left * float(bar[s]["close"]) if s in bar else p.qty_left * p.entry
                  for s, p in open_pos.items())
        realised_open = sum(p.realised + (p.qty - p.qty_left) * p.entry for p in open_pos.values())
        equity = cash + mtm + realised_open
        peak = max(peak, equity)
        if d >= start:
            equity_curve.append({"date": f"{d:%Y-%m-%d}", "equity": round(equity, 2),
                                 "drawdown_pct": round((equity / peak - 1) * 100, 2), "positions": len(open_pos)})

        # 4) today's signals (on the close) -> tomorrow's entries
        evals = [e for s, g in frames.items() if d in by_sym_idx[s]
                 for e in [scanner.evaluate(g, by_sym_idx[s][d])] if e is not None]
        last_evals = rank(evals)
        if d >= start:
            for ev in last_evals:
                if not ev.result.is_valid_match or ev.symbol in open_pos:
                    continue
                g = frames[ev.symbol]
                stop = swing_low_stop(g, by_sym_idx[ev.symbol][d], STOP_LOOKBACK, STOP_BUFFER_ATR)
                if stop is not None and stop < ev.close:
                    pending.append((ev, stop))
                    signal_log.append({"date": f"{d:%Y-%m-%d}", "symbol": ev.symbol, "close": round(ev.close, 2),
                                       "score": round(ev.result.match_score, 3), "stop": round(stop, 2)})

    open_rows = []
    for s, p in open_pos.items():
        last = float(frames[s]["close"].iloc[-1])
        open_rows.append({"symbol": s, "entry_date": f"{p.entry_date:%Y-%m-%d}", "entry": round(p.entry, 2),
                          "qty": p.qty, "qty_left": p.qty_left, "stop": round(p.stop, 2),
                          "t1": round(p.t1, 2), "t2": round(p.t2, 2), "last": round(last, 2),
                          "unrealised": round((last - p.entry) * p.qty_left, 2), "sessions": p.sessions,
                          "fills": p.fills})
    return {"equity_curve": equity_curve, "closed": closed, "open": open_rows, "skipped": skipped,
            "signals": signal_log, "next_session": [{"symbol": ev.symbol, "score": round(ev.result.match_score, 3),
                                                     "stop": round(st, 2), "close": round(ev.close, 2)}
                                                    for ev, st in pending],
            "latest_evaluations": last_evals}


def stats(result: dict, frames: dict[str, pd.DataFrame]) -> dict:
    """Headline numbers WITH their weaknesses (sample size, median trade, concentration)."""
    eq = pd.DataFrame(result["equity_curve"])
    trades = pd.DataFrame(result["closed"])
    out = {"start": eq["date"].iloc[0] if len(eq) else None, "end": eq["date"].iloc[-1] if len(eq) else None,
           "start_equity": VIRTUAL_CAPITAL, "end_equity": float(eq["equity"].iloc[-1]) if len(eq) else VIRTUAL_CAPITAL,
           "max_drawdown_pct": float(eq["drawdown_pct"].min()) if len(eq) else 0.0,
           "trades": int(len(trades)), "open_positions": len(result["open"])}
    out["return_pct"] = round((out["end_equity"] / VIRTUAL_CAPITAL - 1) * 100, 2)
    if len(trades):
        r = trades["r"]
        wins = trades.loc[trades["pnl"] > 0, "pnl"].sort_values(ascending=False)
        out.update(win_rate_pct=round((r > 0).mean() * 100, 1), avg_r=round(r.mean(), 2),
                   median_r=round(r.median(), 2), best_r=round(r.max(), 2), worst_r=round(r.min(), 2),
                   top3_share_of_gross_profit_pct=round(wins.head(3).sum() / wins.sum() * 100, 1)
                   if wins.sum() > 0 else None)
    # benchmark: equal-weight buy & hold of the same universe over the same window
    if len(eq):
        s, e = pd.Timestamp(out["start"]), pd.Timestamp(out["end"])
        rets = []
        for g in frames.values():
            w = g[(g["date"] >= s) & (g["date"] <= e)]
            if len(w) > 1:
                rets.append(w["close"].iloc[-1] / w["close"].iloc[0] - 1)
        out["benchmark_equal_weight_return_pct"] = round(float(np.mean(rets)) * 100, 2) if rets else None
    return out
