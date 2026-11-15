#!/usr/bin/env python3
"""Build site/data.json from each creator's full upload listing.

Backfill: fetch_channels.py stores state/channels/<handle>.json (newest first).
Refresh: this script reads each channel's RSS feed (no API key, no quota),
prepends unseen uploads to the listing and records their publish dates.
"""
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHANNELS = ROOT / "state" / "channels"
DATES = ROOT / "state" / "dates.json"
OUT = ROOT / "site" / "data.json"
FEED = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
N = r"(\d{1,3}(?:\.\d)?)"
# "Episode 3", "Ep.3", "Ep 01", "#3", and Cleo's "TITLE - 02.5 - LAST LIFE" / "- 03 (Part 1) -"
EP_NUM = re.compile(rf"\b(?:episode|ep)\.?\s*{N}|#{N}\b|\s-\s{N}\s+(?:-|\()", re.I)
FINALE = re.compile(r"\bfinale\b|\bfinal\s*:", re.I)
EP_MARK = r"(?:\s*smp)?\s*[-–:|]*\s*(?:episode|ep\b|ep\.|ep\d|#|final)"


def refresh(listing, dates):
    req = urllib.request.Request(FEED.format(listing["channel"]), headers={"User-Agent": "lifeseries-order/0.2"})
    with urllib.request.urlopen(req, timeout=20) as r:
        root = ET.fromstring(r.read())
    known = {v[0] for v in listing["videos"]}
    new = []
    for e in root.findall("a:entry", NS):  # newest first, like the listing
        vid = e.find("yt:videoId", NS).text
        dates[vid] = e.find("a:published", NS).text
        if vid not in known:
            new.append([vid, e.find("a:title", NS).text])
    listing["videos"] = new + listing["videos"]
    return len(new)


def classify(title, seasons, exclude):
    """Season id for a title, or None. Prefer a season name followed by an episode marker."""
    if exclude.search(title):
        return None
    hits = [(m.start(), s) for s in seasons for m in s["_re"].finditer(title)]
    if not hits:
        return None
    marked = [h for h in hits if h[1]["_mark"].match(title, h[0])]
    return min(marked or hits, key=lambda h: h[0])[1]["id"]


def main():
    cfg = json.loads((ROOT / "seasons.json").read_text())
    dates = json.loads(DATES.read_text()) if DATES.exists() else {}
    seasons = cfg["seasons"]
    for s in seasons:
        s["_re"] = re.compile(s["pattern"], re.I)
        s["_mark"] = re.compile(s["pattern"] + EP_MARK, re.I)
    exclude = re.compile("|".join(cfg["exclude"]), re.I)
    overrides = cfg.get("overrides", {})
    eps = {s["id"]: [] for s in seasons}
    failures = 0

    for c in cfg["creators"]:
        path = CHANNELS / f"{c['handle']}.json"
        if not path.exists():
            print(f"warn: no listing for {c['handle']} (run fetch_channels.py)", file=sys.stderr)
            continue
        listing = json.loads(path.read_text())
        try:
            if refresh(listing, dates):
                path.write_text(json.dumps(listing))
        except Exception as exc:
            failures += 1
            print(f"warn: RSS {c['handle']}: {exc}", file=sys.stderr)

        found = {}  # season -> [(vid, title, number or None, override)] oldest first
        for vid, title in reversed(listing["videos"]):
            ov = overrides.get(vid, {})
            if ov is None:
                continue
            sid = ov.get("season") or classify(title, seasons, exclude)
            if sid:
                m = EP_NUM.search(title)
                num = float(next(g for g in m.groups() if g)) if m else None
                found.setdefault(sid, []).append((vid, title, num, ov))

        for sid, vids in found.items():
            # A creator who numbers their episodes: unnumbered extras (recaps,
            # movies, reactions) are dropped. One who never does (Bdubs): keep all.
            numbered = any(n is not None or FINALE.search(t) for _, t, n, _ in vids)
            last = 0
            for vid, title, num, ov in vids:
                if numbered and num is None and not FINALE.search(title) and "session" not in ov:
                    continue
                session = ov.get("session") or num or int(last) + 1
                session = int(session) if float(session).is_integer() else session
                last = session
                eps[sid].append({"id": vid, "title": title, "creator": c["name"], "session": session,
                                 "published": dates.get(vid)})

    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=14)).isoformat()  # a season with uploads this recent is airing
    out = {"generated": now.isoformat(timespec="seconds"), "seasons": []}
    for s in reversed(seasons):  # newest season first
        cast = [c for c in cfg["creators"] if any(e["creator"] == c["name"] for e in eps[s["id"]])]
        if not cast:
            continue
        out["seasons"].append({
            "id": s["id"], "name": s["name"], "year": s.get("year"),
            "color": s.get("color"), "blurb": s.get("blurb"),
            "airing": any((e["published"] or "") >= cutoff for e in eps[s["id"]]),
            "creators": [{"name": c["name"], "color": c["color"],
                          "head": (ROOT / "site" / "heads" / f"{c['name']}.png").exists()} for c in cast],
            "episodes": sorted(eps[s["id"]], key=lambda e: e["session"]),
        })

    DATES.write_text(json.dumps(dates, indent=0, sort_keys=True))
    OUT.write_text(json.dumps(out, separators=(",", ":")))
    for s in out["seasons"]:
        print(f"{s['name']:13} {len(s['creators']):2} creators {len(s['episodes']):4} videos")
    print(f"{failures} RSS failure(s)")


if __name__ == "__main__":
    main()
