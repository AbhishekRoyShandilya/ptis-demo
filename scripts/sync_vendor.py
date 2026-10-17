"""Copy the PTIS engine modules from the PUBLIC PTIS export into vendor/ptis (one-way: public copy -> demo; nothing flows back).

    python scripts/sync_vendor.py --from ../ptis-public

The source must be a public export (it carries the export marker). The private repository is refused outright.
Once the public repository is on GitHub, CI can check it out instead of using this vendored copy.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "vendor" / "ptis"
SKIP = {".git", "node_modules", "__pycache__", ".pytest_cache"}
# only the engine the demo runs (everything else in PTIS stays in the PTIS repository)
INCLUDE = ("strategy_engine/", "core/__init__.py", "core/enums.py", "analytics/__init__.py", "analytics/charges.py")
PRIVATE_MARKERS = ("strategy_specs", "scripts/live", "research_warehouse", "research_bridge/hyp/specs")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="src", required=True)
    src = Path(ap.parse_args().src).resolve()
    if any((src / m).exists() for m in PRIVATE_MARKERS):
        raise SystemExit(f"{src} looks like the PRIVATE repository - refusing. Sync only from the public export.")
    marker = src / ".ptis_public_export"
    if not marker.exists():
        raise SystemExit(f"{src} has no .ptis_public_export marker - not a public export.")

    if DEST.exists():
        shutil.rmtree(DEST)
    digest, n = hashlib.sha256(), 0
    for p in sorted(src.rglob("*")):
        rel = p.relative_to(src)
        if p.is_dir() or SKIP & set(rel.parts) or p.name == ".ptis_public_export":
            continue
        if not rel.as_posix().startswith(INCLUDE):
            continue
        out = DEST / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        data = p.read_bytes()
        out.write_bytes(data)
        digest.update(rel.as_posix().encode() + b"\0" + data)
        n += 1
    (ROOT / "vendor" / "VENDORED_FROM.txt").write_text(
        f"{marker.read_text(encoding='utf-8').strip()}\nfiles {n}\nsha256 {digest.hexdigest()}\n", encoding="utf-8")
    print(f"vendored {n} files from {src} -> {DEST}")


if __name__ == "__main__":
    main()
