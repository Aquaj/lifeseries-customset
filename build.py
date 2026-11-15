#!/usr/bin/env python3
"""Fetch each creator's uploads via YouTube RSS (no API key, no quota),
accumulate season videos in state/videos.json, and emit site/data.json.

RSS only exposes a channel's latest 15 uploads, so run this regularly:
anything seen once is kept in the state file.
"""
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "state" / "videos.json"
OUT = ROOT / "site" / "data.json"
FEED = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
EP_RE = re.compile(r"(?:episode|ep\.?|#)\s*(\d+)", re.I)


def fetch(channel):
    req = urllib.request.Request(FEED.format(channel), headers={"User-Agent": "lifeseries-order/0.1"})
    with urllib.request.urlopen(req, timeout=20) as r:
        root = ET.fromstring(r.read())
    for e in root.findall("a:entry", NS):
        yield {
            "id": e.find("yt:videoId", NS).text,
            "title": e.find("a:title", NS).text,
            "published": e.find("a:published", NS).text,
        }


def assign_sessions(videos, overrides):
    """Episode number from the title when present, else upload rank."""
    videos.sort(key=lambda v: v["published"])
    for rank, v in enumerate(videos, 1):
        m = EP_RE.search(v["title"])
        v["session"] = int(m.group(1)) if m else rank
    for v in videos:
        if v["id"] in overrides:
            v["session"] = overrides[v["id"]]
    return [v for v in videos if v["session"] is not None]


def main():
    cfg = json.loads((ROOT / "seasons.json").read_text())
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    out = {"seasons": []}
    failures = 0

    for s in cfg["seasons"]:
        match = re.compile(s["match"], re.I)
        known = state.setdefault(s["id"], {})
        for c in s["creators"]:
            try:
                for v in fetch(c["channel"]):
                    if match.search(v["title"]) and v["published"][:10] >= s["started"]:
                        known[v["id"]] = {**known.get(v["id"], {}), **v, "creator": c["name"]}
            except Exception as exc:  # keep going; state still holds older videos
                failures += 1
                print(f"warn: {s['id']}/{c['name']}: {exc}", file=sys.stderr)

        episodes = []
        for c in s["creators"]:
            mine = [dict(v) for v in known.values() if v["creator"] == c["name"]]
            episodes += assign_sessions(mine, s.get("overrides", {}))
        episodes.sort(key=lambda v: (v["session"], v["published"]))
        out["seasons"].append({
            "id": s["id"],
            "name": s["name"],
            "creators": [{"name": c["name"], "color": c["color"]} for c in s["creators"]],
            "episodes": [{k: v[k] for k in ("id", "title", "published", "creator", "session")} for v in episodes],
        })

    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1, sort_keys=True))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, separators=(",", ":")))
    total = sum(len(s["episodes"]) for s in out["seasons"])
    print(f"{total} episodes across {len(out['seasons'])} season(s), {failures} feed failure(s)")


if __name__ == "__main__":
    main()
