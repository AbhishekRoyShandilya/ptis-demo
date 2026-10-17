"""Fail (exit 1) when the published data is stale: the newest session is more than 4 calendar days old.
Run after the nightly build so a blocked or broken download shows up as a red run, not as quietly old numbers."""
from __future__ import annotations

import json
import sys
from datetime import date

from demo.config import SITE_DATA

meta = json.loads((SITE_DATA / "meta.json").read_text(encoding="utf-8"))
age = (date.today() - date.fromisoformat(meta["data_as_of"])).days
print(f"data as of {meta['data_as_of']} ({age} days old); downloads this run: {meta['download']}")
sys.exit(1 if age > 4 else 0)
