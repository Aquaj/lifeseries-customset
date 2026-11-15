#!/usr/bin/env python3
"""Full upload listing per creator (no API key) via yt-dlp flat extraction.

Writes state/channels/<handle>.json: {"channel": UC…, "videos": [[id, title], …]}
newest first, as YouTube's /videos tab lists them. Slow-ish (one request per
~30 videos) but only needed for backfill; build.py's RSS pass keeps it fresh.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "state" / "channels"
YTDLP = ROOT / ".venv" / "bin" / "yt-dlp"


def listing(handle):
    r = subprocess.run(
        [str(YTDLP), "--flat-playlist", "-J", "--sleep-requests", "0.5", f"https://www.youtube.com/@{handle}/videos"],
        capture_output=True, text=True, timeout=1800,
    )
    if r.returncode:
        raise RuntimeError(r.stderr.strip().splitlines()[-1] if r.stderr else "yt-dlp failed")
    d = json.loads(r.stdout)
    return {"channel": d.get("channel_id"), "name": d.get("channel"),
            "videos": [[e["id"], e["title"]] for e in d["entries"]]}


def main(handles):
    OUT.mkdir(parents=True, exist_ok=True)
    for h in handles:
        try:
            data = listing(h)
        except Exception as exc:
            print(f"{h}: FAILED {exc}", flush=True)
            continue
        (OUT / f"{h}.json").write_text(json.dumps(data))
        print(f"{h}: {data['name']} {data['channel']} {len(data['videos'])} videos", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
