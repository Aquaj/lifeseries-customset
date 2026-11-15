#!/usr/bin/env python3
"""Download each creator's current Minecraft skin from Mojang and save the
face (with hat layer) as site/heads/<name>.png. Run with the venv python
(needs Pillow). Skins change between seasons; re-run to refresh.
"""
import base64
import io
import json
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "site" / "heads"


def get(url, tries=5):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                return r.read()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def head(username):
    uuid = json.loads(get(f"https://api.mojang.com/users/profiles/minecraft/{username}"))["id"]
    profile = json.loads(get(f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid}"))
    textures = json.loads(base64.b64decode(profile["properties"][0]["value"]))
    skin = Image.open(io.BytesIO(get(textures["textures"]["SKIN"]["url"]))).convert("RGBA")
    face = skin.crop((8, 8, 16, 16))
    face.alpha_composite(skin.crop((40, 8, 48, 16)))  # hat / overlay layer
    return face.resize((64, 64), Image.NEAREST)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for c in json.loads((ROOT / "seasons.json").read_text())["creators"]:
        if not c.get("mc"):
            continue
        try:
            head(c["mc"]).save(OUT / f"{c['name']}.png", optimize=True)
            print(f"{c['name']}: ok ({c['mc']})")
        except Exception as exc:
            print(f"{c['name']}: FAILED {exc}", file=sys.stderr)
        time.sleep(1)


if __name__ == "__main__":
    main()
