#!/usr/bin/env python3
"""Bump the cache-bust token (?v=) on design.css / theme.js across all live HTML pages.

Safari and intermediate proxies hold a stale cached build of design.css /
theme.js between deploys. The site already appends ?v=XXXXXXXX to those two
asset URLs; changing that token forces every browser to refetch.

Run this BEFORE each release commit so the new build is never served stale:

    python3 tools/bump_cache.py                # token = YYYYMMDDHHMM (UTC)
    python3 tools/bump_cache.py 202609031742    # explicit token

Scans every *.html under the repo (excluding _archive/ node_modules/ .git/ doc/)
and rewrites   design.css?v=NNNN  and  theme.js?v=NNNN   in place.
Stdlib only — no dependencies, runs on the managed Python.
"""
import os
import re
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCLUDE = {"_archive", "node_modules", ".git", "doc"}

# matches the asset basename right before ?v=NNNN, whatever the relative path
PATTERN = re.compile(r"(design\.css|theme\.js)\?v=\d+")


def main() -> int:
    token = sys.argv[1] if len(sys.argv) > 1 else datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    changed = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE]
        for fn in files:
            if not fn.endswith(".html"):
                continue
            path = os.path.join(base, fn)
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            new = PATTERN.sub(lambda m: f"{m.group(1)}?v={token}", text)
            if new != text:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new)
                changed.append(os.path.relpath(path, ROOT))

    if changed:
        print(f"Bumped ?v= -> {token} in:")
        for c in changed:
            print("  ", c)
        return 0
    print(f"No ?v= tokens to bump (already {token}?).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
