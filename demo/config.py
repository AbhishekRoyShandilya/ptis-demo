"""Demo configuration: universe, dates, capital. Everything here is public and illustrative."""
from __future__ import annotations

from datetime import date

from demo.guard import DATA, ROOT

EOD_DIR = DATA / "eod"                 # one parquet per session, downloaded from NSE's public archive
SITE_DATA = ROOT / "web" / "public" / "data"   # JSON the static site reads

HISTORY_START = date(2025, 6, 1)       # enough history for 200-day indicators before the paper start
PAPER_START = date(2026, 1, 1)         # the virtual trader starts trading here
VIRTUAL_CAPITAL = 1_000_000.0          # illustrative paper capital (INR)
MAX_POSITIONS = 5

# The universe is NSE's official NIFTY 50 list, downloaded each night (demo/eod.py -> data/universe_nifty50.csv).
