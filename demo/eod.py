"""End-of-day prices from NSE's public bhavcopy archive -> a split/bonus-adjusted daily panel.

    python -m demo.eod            # download any missing sessions, rebuild data/panel.parquet

- One file per session is cached in data/eod/ (only the universe's EQ rows). Holidays (404) are remembered once
  they are older than a few days, so a not-yet-published file is retried the next night.
- The archive's previous close is NOT adjusted for splits or bonuses (BAJFINANCE 2025-06-16: open 956 after a
  "previous close" of 9,331). A gap is treated as a corporate action only when open/previous-close lands within 3%
  of a standard split/bonus ratio; the history before it is then scaled. Every adjustment is logged and published.
"""
from __future__ import annotations

import io
import json
import time
import zipfile
from datetime import date, timedelta

import pandas as pd
import requests

from demo import guard  # noqa: F401  (isolation first)
from demo.config import DATA, EOD_DIR, HISTORY_START

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0 Safari/537.36")
BHAV_URL = "https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{d:%Y%m%d}_F_0000.csv.zip"
NIFTY50_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv"
UNIVERSE_FILE = DATA / "universe_nifty50.csv"
MISSING_FILE = EOD_DIR / "_no_session.json"
PANEL_FILE = DATA / "panel.parquet"
ADJ_FILE = DATA / "adjustments.json"

# price ratio after/before for common Indian corporate actions: splits 1:k and bonuses a:b (b/(a+b))
STANDARD_RATIOS = sorted({1 / 2, 1 / 3, 1 / 4, 1 / 5, 1 / 10, 2 / 3, 3 / 4, 4 / 5, 2 / 5, 3 / 5, 1 / 20})
RATIO_TOL = 0.03

_session = requests.Session()
_session.headers.update({"User-Agent": UA, "Accept": "*/*"})


def _get(url: str, tries: int = 3) -> requests.Response | None:
    for k in range(tries):
        try:
            r = _session.get(url, timeout=30)
            if r.status_code in (200, 404):
                return r
        except requests.RequestException:
            pass
        time.sleep(2 * (k + 1))
    return None


def load_universe(refresh: bool = True) -> list[str]:
    """The official NIFTY 50 list; the last saved copy is the fallback if NSE is unreachable."""
    if refresh:
        r = _get(NIFTY50_URL)
        if r is not None and r.status_code == 200 and b"Symbol" in r.content[:200]:
            UNIVERSE_FILE.parent.mkdir(parents=True, exist_ok=True)
            UNIVERSE_FILE.write_bytes(r.content)
    return pd.read_csv(UNIVERSE_FILE)["Symbol"].str.strip().tolist()


def _no_session() -> set[str]:
    return set(json.loads(MISSING_FILE.read_text())) if MISSING_FILE.exists() else set()


def fetch_session(d: date, universe: set[str]) -> str:
    """Download one session into the cache. Returns 'cached' | 'saved' | 'holiday' | 'failed'."""
    out = EOD_DIR / f"{d:%Y-%m-%d}.parquet"
    if out.exists():
        return "cached"
    r = _get(BHAV_URL.format(d=d))
    if r is None:
        return "failed"
    if r.status_code == 404:
        return "holiday"
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        raw = pd.read_csv(z.open(z.namelist()[0]))
    eq = raw[(raw["SctySrs"] == "EQ") & (raw["TckrSymb"].isin(universe))]
    df = pd.DataFrame({
        "date": pd.to_datetime(eq["TradDt"]).dt.date,
        "symbol": eq["TckrSymb"].values,
        "isin": eq["ISIN"].values,
        "open": eq["OpnPric"].astype(float).values,
        "high": eq["HghPric"].astype(float).values,
        "low": eq["LwPric"].astype(float).values,
        "close": eq["ClsPric"].astype(float).values,
        "prev_close": eq["PrvsClsgPric"].astype(float).values,
        "volume": eq["TtlTradgVol"].astype(float).values,
        "value": eq["TtlTrfVal"].astype(float).values,
    })
    EOD_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    return "saved"


def update(today: date | None = None) -> dict:
    today = today or date.today()
    universe = set(load_universe())
    skip = _no_session()
    counts = {"cached": 0, "saved": 0, "holiday": 0, "failed": 0}
    d = HISTORY_START
    while d <= today:
        key = f"{d:%Y-%m-%d}"
        if d.weekday() < 5 and key not in skip:
            status = fetch_session(d, universe)
            counts[status] += 1
            if status == "holiday" and (today - d).days > 3:
                skip.add(key)
            if status == "saved":
                time.sleep(0.4)                       # be polite to the archive
        d += timedelta(days=1)
    MISSING_FILE.parent.mkdir(parents=True, exist_ok=True)
    MISSING_FILE.write_text(json.dumps(sorted(skip)))
    return counts


def _nearest_standard(ratio: float) -> float | None:
    best = min(STANDARD_RATIOS, key=lambda s: abs(ratio / s - 1))
    return best if abs(ratio / best - 1) <= RATIO_TOL else None


def build_panel() -> tuple[pd.DataFrame, list[dict]]:
    """Concatenate sessions, back-adjust standard splits/bonuses, and return (panel, adjustments)."""
    files = sorted(p for p in EOD_DIR.glob("*.parquet"))
    raw = pd.concat([pd.read_parquet(p) for p in files], ignore_index=True)
    raw = raw.sort_values(["symbol", "date"]).reset_index(drop=True)
    universe = set(load_universe(refresh=False))
    raw = raw[raw["symbol"].isin(universe)]

    panels, adjustments = [], []
    for sym, g in raw.groupby("symbol", sort=True):
        g = g.reset_index(drop=True).copy()
        factor = pd.Series(1.0, index=g.index)
        for i in range(1, len(g)):
            prev_close = g.at[i - 1, "close"]
            ratio = g.at[i, "open"] / prev_close if prev_close else 1.0
            if 0.75 < ratio < 1.33:
                continue
            std = _nearest_standard(ratio)
            if std is None:
                continue                              # a real move: leave it alone
            factor.iloc[:i] *= std
            adjustments.append({"symbol": sym, "date": str(g.at[i, "date"]), "ratio": round(std, 4),
                                "open": float(g.at[i, "open"]), "prev_close": float(prev_close),
                                "isin_changed": bool(g.at[i, "isin"] != g.at[i - 1, "isin"])})
        for col in ("open", "high", "low", "close"):
            g[col] = g[col] * factor
        g["volume"] = g["volume"] / factor
        panels.append(g.drop(columns=["prev_close"]))
    panel = pd.concat(panels, ignore_index=True)
    panel["date"] = pd.to_datetime(panel["date"])
    return panel, adjustments


def main() -> None:
    counts = update()
    panel, adjustments = build_panel()
    panel.to_parquet(PANEL_FILE, index=False)
    ADJ_FILE.write_text(json.dumps(adjustments, indent=1, default=str))
    print(f"sessions {counts} -> panel {len(panel):,} rows, {panel['symbol'].nunique()} symbols, "
          f"{panel['date'].min():%Y-%m-%d}..{panel['date'].max():%Y-%m-%d}; {len(adjustments)} adjustments")
    for a in adjustments:
        print("  adjusted", a)


if __name__ == "__main__":
    main()
