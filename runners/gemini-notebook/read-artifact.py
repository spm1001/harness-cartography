# /// script
# requires-python = ">=3.11"
# dependencies = ["websockets"]
# ///
"""Open a Gemini Notebook Studio artifact and read back its rendered content.

Read-only: it clicks one artifact open and reports what the viewer renders.
Written for canary verification — "is the token still retrievable?" — where a
list row is not an answer (README, "Verifying a canary is a content read").

Two things it does that the passe CLI cannot (README rules 5 and 6):

  * clicks with a trusted `Input.dispatchMouseEvent` after `Page.bringToFront`,
    because this app ignores synthetic DOM clicks and reports success anyway;
  * pins the tab by URL substring, because tube's :9223 is the human's own
    session Chrome and an eval against his tab returns "" — a false null.

It aims at the artifact's TITLE span, never the row-end kebab menu, which
carries the destructive actions. Nothing is created, renamed or deleted.

Usage:
  uv run --script read-artifact.py --artifact-id <uuid> --token <TOKEN>
  uv run --script read-artifact.py --list          # just enumerate artifacts

Exit 0 = token found in the opened artifact. Exit 1 = not found (a real
absence only if the control line below reads OK). Exit 2 = probe fault.
"""
import argparse
import asyncio
import json
import sys
import urllib.request

import websockets

DEFAULT_CDP = "http://localhost:9223"
DEFAULT_MATCH = "notebook.google.com/notebook/"


def pick_tab(cdp: str, match: str) -> dict:
    """Resolve the target tab, refusing to guess when the match is ambiguous."""
    tabs = json.load(urllib.request.urlopen(f"{cdp}/json"))
    hits = [t for t in tabs if match in t.get("url", "") and t.get("type") == "page"]
    if not hits:
        raise SystemExit(
            f"probe fault: no open tab matching {match!r} at {cdp}.\n"
            f"open tabs: {[t.get('url') for t in tabs]}"
        )
    if len(hits) > 1:
        raise SystemExit(
            f"probe fault: {len(hits)} tabs match {match!r} — narrow it.\n"
            f"matches: {[t.get('url') for t in hits]}"
        )
    return hits[0]


async def run(args: argparse.Namespace) -> int:
    tab = pick_tab(args.cdp, args.match)
    print(f"tab: {tab['url']}")

    async with websockets.connect(tab["webSocketDebuggerUrl"], max_size=50 * 1024 * 1024) as ws:
        mid = 0

        async def call(method, params=None):
            nonlocal mid
            mid += 1
            await ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("id") == mid:
                    return msg

        async def js(expr):
            r = await call("Runtime.evaluate", {"expression": expr, "returnByValue": True})
            return r["result"]["result"].get("value")

        await call("Page.bringToFront")

        # Control: can this probe see the notebook at all? Printed beside every
        # verdict, because a null from a blind probe looks exactly like an absence.
        # NB the row's first innerText line is a Material icon ligature
        # ("markdown", "image"), not the filename — read .artifact-title.
        rows = await js(
            "JSON.stringify([...document.querySelectorAll('artifact-library-item')]"
            ".map(e=>((e.querySelector('.artifact-title')||{}).innerText||'?').trim()))"
        )
        rows = json.loads(rows or "[]")
        print(f"control — Studio artifacts visible ({len(rows)}): {rows}")
        if not rows:
            print(
                "CONTROL FAILED: no artifact rows rendered — treat any null below as unproven.\n"
                "  Commonest cause is benign: an artifact viewer left open from a previous run\n"
                "  REPLACES the library list in the DOM. Reload the notebook tab and re-run."
            )
            return 2

        if args.list:
            return 0

        before = await js(f"document.body.innerText.split({args.token!r}).length-1")
        print(f"token occurrences before opening artifact: {before}")

        rect = await js(
            "(function(){const e=document.getElementById('artifact-labels-"
            + args.artifact_id
            + "');if(!e)return '';e.scrollIntoView({block:'center'});"
            "const r=e.getBoundingClientRect();return JSON.stringify("
            "{x:r.left+r.width/2,y:r.top+r.height/2,text:e.innerText});})()"
        )
        if not rect:
            print(f"artifact row {args.artifact_id} NOT PRESENT (control above passed, so this is a real absence)")
            return 1
        r = json.loads(rect)
        print(f"row found: {r['text']!r}")

        await asyncio.sleep(0.6)
        await call("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": r["x"], "y": r["y"]})
        for ev in ("mousePressed", "mouseReleased"):
            await call(
                "Input.dispatchMouseEvent",
                {"type": ev, "x": r["x"], "y": r["y"], "button": "left", "clickCount": 1},
            )

        after = before
        for i in range(args.timeout):
            await asyncio.sleep(1)
            after = await js(f"document.body.innerText.split({args.token!r}).length-1")
            if after > before:
                print(f"token occurrences after: {after} (rose at t+{i+1}s) — VIEWER RENDERED THE CONTENT")
                print(f"VERDICT: {args.token} HELD in artifact {args.artifact_id}")
                return 0
        print(f"token occurrences after: {after} (no rise in {args.timeout}s)")
        print(f"VERDICT: {args.token} NOT retrieved from artifact {args.artifact_id}")
        return 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cdp", default=DEFAULT_CDP, help="CDP endpoint (default tube's session Chrome)")
    p.add_argument("--match", default=DEFAULT_MATCH, help="URL substring identifying the notebook tab")
    p.add_argument("--artifact-id", default="", help="Studio artifactId (the uuid in artifact-labels-<id>)")
    p.add_argument("--token", default="", help="string the artifact should contain")
    p.add_argument("--timeout", type=int, default=12, help="seconds to wait for the viewer")
    p.add_argument("--list", action="store_true", help="only enumerate visible artifacts")
    args = p.parse_args()
    if not args.list and not (args.artifact_id and args.token):
        p.error("--artifact-id and --token are required unless --list")
    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
