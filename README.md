# Life Series — Watch Order

A fan-made page that merges every creator's Life Series episodes into one
watch order, session by session. Pick a season and the POVs you follow, tick
what you've seen, and "Continue" opens the next episodes as a YouTube queue.

Unofficial. Not affiliated with the Life Series creators, Mojang or YouTube.

## How it works

- `seasons.json` lists the creators, the seasons (a title pattern each) and
  any manual `overrides`.
- `build.py` reads each creator's YouTube RSS feed (no API key), adds new
  uploads to the listings in `state/`, sorts titles into seasons and sessions,
  and writes `site/data.json`. Standard library only.
- `site/` is the static page. Progress lives in the visitor's browser
  (`localStorage`); nothing is sent anywhere.
- A GitHub Action runs `build.py` four times a day and publishes `site/` to
  GitHub Pages.

## Maintenance

- **A video is missing or in the wrong session:** add it to `overrides` in
  `seasons.json`: `"<videoId>": {"season": "wild-life", "session": 5}`, or
  `"<videoId>": null` to hide one.
- **A new creator:** add them to `creators`, then backfill their uploads once
  with `fetch_channels.py <handle>` (needs `yt-dlp` in `.venv`).
- **A new season:** add it to `seasons` with a title pattern and a colour.
- **Player heads:** `fetch_heads.py` (needs Pillow) saves each creator's face
  to `site/heads/`. A skin file at `skins/<Name>.png` wins over the creator's
  current Mojang skin.

## Credits

Fonts: Pixelify Sans and Silkscreen, both under the SIL Open Font License.
Thumbnails are loaded from YouTube. Minecraft skins belong to their creators.
