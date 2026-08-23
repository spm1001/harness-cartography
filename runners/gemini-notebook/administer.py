# /// script
# requires-python = ">=3.11"
# dependencies = ["websockets"]
# ///
"""Administer the probe letter into a Gemini Notebook chat via raw CDP.

Edit NOTEBOOK_MATCH and LETTER_PATH per run. Types the letter with real key
events (the app's model ignores DOM-stuffing and Input.insertText), splitting
after item 8's marker if it exceeds the ~3.9k query cap. Completion is judged
by the page's own Responding/stop indicator, never innerText stability
(README rule 4 — stability lies during thinking pauses)."""
import asyncio, json, pathlib, urllib.request
import websockets

NOTEBOOK_MATCH = 'notebook.google.com/notebook/6a6f999b'   # substring of the target tab URL
LETTER_PATH = '/home/modha/notes/practices/harness-cartography/letter-v2.md'
SPLIT_MARKER = '8. **Draw.**'
CAP_SAFE = 3800

body = '\n'.join(pathlib.Path(LETTER_PATH).read_text().splitlines()[1:]).strip()
if len(body) > CAP_SAFE:
    at = body.index(SPLIT_MARKER)
    parts = [
        ("(Administrator's note: this letter arrives in two messages — the second ends with \"not of us.\" Please read both before reporting; a brief acknowledgement of this first half is fine.)\n\n" + body[:at].rstrip()),
        ("(Administrator's note: second and final message of the letter.)\n\n" + body[at:]),
    ]
    assert all(len(p) < CAP_SAFE for p in parts), [len(p) for p in parts]
else:
    parts = [body]

tabs = json.load(urllib.request.urlopen('http://localhost:9223/json'))
tab = next(t for t in tabs if NOTEBOOK_MATCH in t.get('url', ''))

async def main():
    async with websockets.connect(tab['webSocketDebuggerUrl'], max_size=50*1024*1024) as ws:
        mid = 0
        async def call(method, params=None):
            nonlocal mid
            mid += 1
            await ws.send(json.dumps({'id': mid, 'method': method, 'params': params or {}}))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get('id') == mid:
                    return msg
        async def js(expr):
            r = await call('Runtime.evaluate', {'expression': expr})
            return r['result']['result'].get('value')
        async def type_text(text):
            for ch in text:
                if ch == '\n':
                    await call('Input.dispatchKeyEvent', {'type':'keyDown','key':'Enter','code':'Enter','modifiers':8,'text':'\r','windowsVirtualKeyCode':13})
                    await call('Input.dispatchKeyEvent', {'type':'keyUp','key':'Enter','code':'Enter','modifiers':8,'windowsVirtualKeyCode':13})
                else:
                    await call('Input.dispatchKeyEvent', {'type':'keyDown','key':ch,'text':ch})
                    await call('Input.dispatchKeyEvent', {'type':'keyUp','key':ch})
        async def submit_and_wait(label, maxwait_s=300):
            state = json.loads(await js("(function(){const t=document.querySelector('textarea[aria-label=\"Query box\"]');const b=t.closest('form').querySelector('button[aria-label=\"Submit\"]');return JSON.stringify({len:t.value.length,dis:b.disabled});})()"))
            print(label, 'pre-submit:', state)
            if state['dis']:
                print('GATED — abort'); return False
            await js("(function(){const b=document.querySelector('textarea[aria-label=\"Query box\"]').closest('form').querySelector('button[aria-label=\"Submit\"]');b.click();return 1;})()")
            await asyncio.sleep(5)   # let generation begin so the indicator exists
            for _ in range(maxwait_s // 5):
                responding = await js("document.body.innerText.includes('Responding') || !!document.querySelector('[aria-label=\"Stop\"], .stop-button')")
                if not responding:
                    print(label, 'response complete'); return True
                await asyncio.sleep(5)
            print(label, f'still responding after {maxwait_s}s'); return False

        await call('Page.bringToFront')          # README rule 1: background tabs are input-deaf
        await asyncio.sleep(0.5)
        await js("(function(){const t=document.querySelector('textarea[aria-label=\"Query box\"]');t.focus();t.select();return 1;})()")
        await call('Input.dispatchKeyEvent', {'type':'keyDown','key':'Backspace','code':'Backspace','windowsVirtualKeyCode':8})
        await call('Input.dispatchKeyEvent', {'type':'keyUp','key':'Backspace','code':'Backspace','windowsVirtualKeyCode':8})
        await asyncio.sleep(0.3)
        for n, part in enumerate(parts, 1):
            await type_text(part)
            await asyncio.sleep(1.5)
            if not await submit_and_wait(f'PART{n}'):
                return
            await js("(function(){const t=document.querySelector('textarea[aria-label=\"Query box\"]');t.focus();return 1;})()")
        print('ADMINISTERED')

asyncio.run(main())
