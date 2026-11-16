#!/usr/bin/env python3
"""Generate the favicon and app icons (a pixel heart) into site/. Needs Pillow.

The link-preview image is a screenshot of tools/og-card.html:
  .venv/bin/python tools/shot.py site/og.png --root . --path /tools/og-card.html --width 1200 --height 630
"""
from pathlib import Path

from PIL import Image

SITE = Path(__file__).resolve().parent.parent / "site"
BG, OUTLINE, RED, LIGHT, SHADE = (16, 17, 20), (0, 0, 0), (232, 69, 60), (246, 180, 175), (181, 54, 47)
# 9x8 pixel heart, same shape as the masthead hearts: o outline, r fill, w highlight, s shade
HEART = ["_ooo_ooo_",
         "orrrorrro",
         "orwrrrrso",
         "orrrrrrso",
         "orrrrrrso",
         "_orrrrso_",
         "__orsso__",
         "___ooo___"]
COLORS = {"o": OUTLINE, "r": RED, "w": LIGHT, "s": SHADE}


def heart(scale):
    img = Image.new("RGBA", (9 * scale, 8 * scale), (0, 0, 0, 0))
    for y, row in enumerate(HEART):
        for x, ch in enumerate(row):
            if ch != "_":
                img.paste(COLORS[ch] + (255,), (x * scale, y * scale, (x + 1) * scale, (y + 1) * scale))
    return img


def icon(size, fill=0.62, background=True):
    scale = max(1, int(size * fill) // 9)
    h = heart(scale)
    img = Image.new("RGBA", (size, size), BG + (255,) if background else (0, 0, 0, 0))
    img.alpha_composite(h, ((size - h.width) // 2, (size - h.height) // 2))
    return img


def main():
    icon(180).convert("RGB").save(SITE / "apple-touch-icon.png", optimize=True)
    icon(192).save(SITE / "icon-192.png", optimize=True)
    icon(512).save(SITE / "icon-512.png", optimize=True)
    icon(32, fill=1, background=False).save(SITE / "favicon-32.png", optimize=True)
    icon(48, fill=1, background=False).save(SITE / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    rects = "".join(f'<rect x="{x}" y="{y}" width="1" height="1" fill="#{"%02x%02x%02x" % COLORS[ch]}"/>'
                    for y, row in enumerate(HEART) for x, ch in enumerate(row) if ch != "_")
    (SITE / "favicon.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -0.5 9 9" shape-rendering="crispEdges">{rects}</svg>\n')
    print("icons written to", SITE)


if __name__ == "__main__":
    main()
