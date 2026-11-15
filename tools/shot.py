#!/usr/bin/env python3
"""Screenshot the local site in headless Chromium (docker), for design checks.

  .venv/bin/python tools/shot.py out.png [--width 390] [--height 844] [--full]
                                         [--js "code run after load"] [--path /]

Serves site/ on 127.0.0.1, starts chromedp/headless-shell bound to localhost,
drives it over CDP. Needs `websockets` in the venv.
"""
import argparse
import asyncio
import base64
import functools
import http.server
import json
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

import websockets

ROOT = Path(__file__).resolve().parent.parent
PORT, CDP, NAME = 8765, 9333, "lso-shot"


def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / "site"))
    handler.log_message = lambda *a: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()


def chrome():
    subprocess.run(["docker", "rm", "-f", NAME], capture_output=True)
    subprocess.run(["docker", "run", "-d", "--rm", "--network", "host", "--name", NAME,
                    "chromedp/headless-shell", "--remote-debugging-address=127.0.0.1",
                    f"--remote-debugging-port={CDP}", "--hide-scrollbars"], check=True, capture_output=True)
    for _ in range(50):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{CDP}/json/version", timeout=1) as r:
                return json.load(r)["webSocketDebuggerUrl"]
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("chrome did not start")


async def run(a):
    ws_url = chrome()
    try:
        async with websockets.connect(ws_url, max_size=None) as ws:
            n = 0

            async def call(method, params=None, session=None):
                nonlocal n
                n += 1
                msg = {"id": n, "method": method, "params": params or {}}
                if session:
                    msg["sessionId"] = session
                await ws.send(json.dumps(msg))
                while True:
                    r = json.loads(await ws.recv())
                    if r.get("id") == n:
                        if "error" in r:
                            raise RuntimeError(r["error"])
                        return r["result"]

            target = (await call("Target.createTarget", {"url": "about:blank"}))["targetId"]
            s = (await call("Target.attachToTarget", {"targetId": target, "flatten": True}))["sessionId"]
            await call("Emulation.setDeviceMetricsOverride",
                       {"width": a.width, "height": a.height, "deviceScaleFactor": a.scale, "mobile": a.width < 600}, s)
            await call("Page.enable", session=s)
            await call("Page.navigate", {"url": f"http://127.0.0.1:{PORT}{a.path}"}, s)
            await asyncio.sleep(a.wait)
            if a.js:
                r = await call("Runtime.evaluate", {"expression": a.js, "awaitPromise": True, "returnByValue": True}, s)
                if "exceptionDetails" in r:
                    print("JS error:", r["exceptionDetails"].get("exception", {}).get("description"))
                elif r["result"].get("value") is not None:
                    print("JS:", r["result"]["value"])
                await asyncio.sleep(a.wait)
            shot = await call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": a.full}
                              | ({"clip": {"x": 0, "y": 0, "width": a.width, "scale": 1, "height": (await call(
                                  "Runtime.evaluate", {"expression": "document.documentElement.scrollHeight",
                                                       "returnByValue": True}, s))["result"]["value"]}} if a.full else {}), s)
            Path(a.out).write_bytes(base64.b64decode(shot["data"]))
            print("wrote", a.out)
    finally:
        subprocess.run(["docker", "rm", "-f", NAME], capture_output=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("out")
    p.add_argument("--width", type=int, default=390)
    p.add_argument("--height", type=int, default=844)
    p.add_argument("--scale", type=float, default=1)
    p.add_argument("--full", action="store_true")
    p.add_argument("--js")
    p.add_argument("--path", default="/")
    p.add_argument("--wait", type=float, default=2.5)
    args = p.parse_args()
    serve()
    asyncio.run(run(args))
