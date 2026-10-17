"""Nightly build: data -> PTIS engine -> JSON for the static site.

    python -m demo.build              # full run (download missing sessions, scan, paper-trade, publish JSON)
    python -m demo.build --offline    # reuse cached sessions only

Outputs (web/public/data/): meta.json, strategy.json, scan.json, paper.json, market.json, series/<SYMBOL>.json,
adjustments.json.
"""
from __future__ import annotations

import argparse
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from demo import guard
from demo import eod
from demo.config import MAX_POSITIONS, PAPER_START, SITE_DATA, VIRTUAL_CAPITAL
from demo.engine import STRATEGY_DIR, STRATEGY_ID, Scanner, frames as build_frames
from demo import paper


def _write(name: str, obj) -> None:
    path = SITE_DATA / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, separators=(",", ":"), default=str), encoding="utf-8")


def _num(x, nd=2):
    return None if x is None or pd.isna(x) else round(float(x), nd)


def data_quality(panel: pd.DataFrame) -> dict:
    """Bars worth a second look. Nothing is changed; they are listed so results that depend on them are explainable.
    - isolated opening prints: the open is >4% away from BOTH the previous close and the same day's close
    - zero-volume sessions."""
    p = panel.sort_values(["symbol", "date"]).copy()
    p["prev_close"] = p.groupby("symbol")["close"].shift(1)
    away_prev = (p["open"] / p["prev_close"] - 1).abs() > 0.04
    away_close = (p["open"] / p["close"] - 1).abs() > 0.04
    spikes = p[away_prev & away_close]
    return {
        "open_prints": [{"symbol": r.symbol, "date": f"{r.date:%Y-%m-%d}", "prev_close": _num(r.prev_close),
                         "open": _num(r.open), "low": _num(r.low), "high": _num(r.high), "close": _num(r.close)}
                        for r in spikes.itertuples()],
        "zero_volume": [{"symbol": r.symbol, "date": f"{r.date:%Y-%m-%d}"} for r in p[p["volume"] <= 0].itertuples()],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    t0 = time.perf_counter()
    timings = {}

    counts = {"skipped": "offline"} if a.offline else eod.update()
    panel, adjustments = eod.build_panel()
    panel.to_parquet(eod.PANEL_FILE, index=False)
    timings["data_s"] = round(time.perf_counter() - t0, 1)

    t1 = time.perf_counter()
    fr = build_frames(panel)
    scanner = Scanner()
    result = paper.run(fr, scanner)
    st = paper.stats(result, fr)
    timings["engine_s"] = round(time.perf_counter() - t1, 1)

    as_of = panel["date"].max()
    latest = [e.to_dict() for e in result.pop("latest_evaluations")]

    # market overview + per-symbol series (last ~250 sessions, with the strategy's EMAs)
    market = []
    for s, g in fr.items():
        last, prev = g.iloc[-1], g.iloc[-2] if len(g) > 1 else g.iloc[-1]
        ev = next((x for x in latest if x["symbol"] == s), None)
        market.append({"symbol": s, "date": f"{last['date']:%Y-%m-%d}", "close": _num(last["close"]),
                       "change_pct": _num((last["close"] / prev["close"] - 1) * 100),
                       "ema_20": _num(last["ema_20"]), "ema_50": _num(last["ema_50"]),
                       "ema_200": _num(last["ema_200"]), "rsi_14": _num(last["rsi_14"], 1),
                       "regime": ev["regime"] if ev else None, "score": ev["score"] if ev else None,
                       "valid": ev["valid"] if ev else False,
                       "spark": [_num(v) for v in g["close"].tail(60)]})
        tail = g.tail(250)
        _write(f"series/{s}.json", {"symbol": s, "bars": [
            {"d": f"{r.date:%Y-%m-%d}", "o": _num(r.open), "h": _num(r.high), "l": _num(r.low), "c": _num(r.close),
             "v": int(r.volume), "e20": _num(r.ema_20), "e50": _num(r.ema_50)} for r in tail.itertuples()]})

    raw_yaml = (STRATEGY_DIR / "ema_pullback_daily.yaml").read_text(encoding="utf-8")
    tpl = scanner.registry.get(STRATEGY_ID)
    _write("strategy.json", {
        "id": tpl.id, "name": tpl.name, "description": tpl.description, "yaml": raw_yaml,
        "direction": tpl.direction,
        "regimes": {"preferred": [r.value for r in tpl.preferred_regimes],
                    "avoid": [r.value for r in tpl.avoid_regimes]},
        "confirmations": [{"type": c.type, "required": c.required, "weight": c.weight,
                           "description": c.description, "params": c.params} for c in tpl.entry_confirmations],
        "avoid_conditions": [{"type": c.type, "description": c.description, "params": c.params}
                             for c in tpl.avoid_conditions],
        "exit": {"stop": {"type": tpl.exit_rules.stop_loss.type, "params": tpl.exit_rules.stop_loss.params},
                 "targets": [{"r": t.r_multiple, "size_pct": t.size_pct} for t in tpl.exit_rules.targets],
                 "max_sessions": paper.MAX_SESSIONS},
        "risk": {"max_risk_pct": tpl.risk_rules.max_risk_pct}})
    _write("scan.json", {"as_of": f"{as_of:%Y-%m-%d}", "evaluations": latest,
                         "next_session_entries": result["next_session"]})
    _write("paper.json", {"stats": st, "rules": {"capital": VIRTUAL_CAPITAL, "max_positions": MAX_POSITIONS,
                                                "paper_start": str(PAPER_START)}, **result})
    _write("market.json", {"as_of": f"{as_of:%Y-%m-%d}", "stocks": sorted(market, key=lambda m: m["symbol"])})
    _write("adjustments.json", adjustments)
    _write("data_quality.json", data_quality(panel))

    vendored = (guard.ROOT / "vendor" / "VENDORED_FROM.txt").read_text(encoding="utf-8").strip().splitlines()
    timings["total_s"] = round(time.perf_counter() - t0, 1)
    _write("meta.json", {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_as_of": f"{as_of:%Y-%m-%d}", "sessions": int(panel["date"].nunique()),
        "symbols": int(panel["symbol"].nunique()), "rows": int(len(panel)),
        "first_session": f"{panel['date'].min():%Y-%m-%d}", "download": counts,
        "adjustments": len(adjustments), "timings": timings,
        "engine_source": vendored, "python": platform.python_version(),
        "evaluations_today": len(latest), "valid_signals_today": sum(1 for e in latest if e["valid"])})
    print(f"built site data as of {as_of:%Y-%m-%d} in {timings['total_s']}s: {st}")


if __name__ == "__main__":
    main()
