#!/usr/bin/env python3
"""Record each creator's YouTube subscriber count in seasons.json ("subs").

Only used for the default POV order (most-followed first), so the rounded
figure YouTube shows on the channel page is plenty. Re-run occasionally.
"""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

CFG = Path(__file__).resolve().parent / "seasons.json"
# The channel's own figure sits in the header metadata; the bare "simpleText" ones are featured channels.
COUNT = re.compile(r'"metadataParts":\[\{"text":\{"content":"([\d.]+)([KM]?) subscribers"')
MULT = {"": 1, "K": 1_000, "M": 1_000_000}


def subs(handle):
    req = urllib.request.Request(f"https://www.youtube.com/@{handle}",
                                 headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en"})
    with urllib.request.urlopen(req, timeout=20) as r:
        m = COUNT.search(r.read().decode("utf-8", "replace"))
    return round(float(m.group(1)) * MULT[m.group(2)]) if m else None


def main():
    cfg = json.loads(CFG.read_text())
    for c in cfg["creators"]:
        try:
            n = subs(c["handle"])
        except Exception as exc:
            n = None
            print(f"{c['name']}: FAILED {exc}", file=sys.stderr)
        if n:
            c["subs"] = n
        print(f"{c['name']:8} {c.get('subs')}")
        time.sleep(1)
    CFG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
