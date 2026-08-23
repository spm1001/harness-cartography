# /// script
# requires-python = ">=3.11"
# dependencies = ["websockets"]
# ///
import asyncio, json, pathlib, urllib.request
import websockets

body = '\n'.join(pathlib.Path('/home/modha/notes/practices/harness-cartography/letter-v2.md').read_text().splitlines()[1:]).strip()
split_at = body.index('8. **Draw.**')
part1 = ("(Administrator's note: this letter arrives in two messages — the second ends with \"not of us.\" Please read both before reporting; a brief acknowledgement of this first half is fine.)\n\n" + body[:split_at].rstrip())
part2 = "(Administrator's note: second and final message of the letter.)\n\n" + body[split_at:]
assert len(part1) < 3800 and len(part2) < 3800, (len(part1), len(part2))
print(f'part1={len(part1)} part2={len(part2)}')

tabs = json.load(urllib.request.urlopen('http://localhost:9223/json'))
tab = next(t for t in tabs if 'notebook.google.com/notebook/6a6f999b' in t.get('url',''))

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
        async def submit_and_wait(label, maxpolls=24):
            state = json.loads(await js("(function(){const t=document.querySelector('textarea[aria-label=\"Query box\"]');const b=t.closest('form').querySelector('button[aria-label=\"Submit\"]');return JSON.stringify({len:t.value.length,dis:b.disabled});})()"))
            print(label, 'pre-submit:', state)
            if state['dis']:
                print('GATED — abort'); return False
            await js("(function(){const b=document.querySelector('textarea[aria-label=\"Query box\"]').closest('form').querySelector('button[aria-label=\"Submit\"]');b.click();return 1;})()")
            prev, stable = -1, 0
            for i in range(maxpolls):
                await asyncio.sleep(5)
                cur = await js("document.body.innerText.length")
                stable = stable + 1 if cur == prev else 0
                prev = cur
                if stable >= 3:
                    break
            print(label, f'response settled at {prev} chars')
            return True

        await call('Page.bringToFront')
        await asyncio.sleep(0.3)
        await js("(function(){const t=document.querySelector('textarea[aria-label=\"Query box\"]');t.focus();t.select();return 1;})()")
        await call('Input.dispatchKeyEvent', {'type':'keyDown','key':'Backspace','code':'Backspace','windowsVirtualKeyCode':8})
        await call('Input.dispatchKeyEvent', {'type':'keyUp','key':'Backspace','code':'Backspace','windowsVirtualKeyCode':8})
        await asyncio.sleep(0.3)
        await type_text(part1)
        await asyncio.sleep(1.5)
        if not await submit_and_wait('PART1'): return
        await js("(function(){const t=document.querySelector('textarea[aria-label=\"Query box\"]');t.focus();return 1;})()")
        await type_text(part2)
        await asyncio.sleep(1.5)
        if not await submit_and_wait('PART2', maxpolls=36): return
        print('ADMINISTERED')

asyncio.run(main())
