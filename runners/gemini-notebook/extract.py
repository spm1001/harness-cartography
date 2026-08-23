# /// script
# requires-python = ">=3.11"
# dependencies = ["websockets"]
# ///
"""Extract the chat from a Gemini Notebook tab via raw CDP.

Writes two files: <out>-transcript.txt (every chat-message element, may contain
nested duplicates) and <out>-final.txt (the last message alone — usually the
report). Edit NOTEBOOK_MATCH per run; out prefix is argv[1], default /tmp/notebook."""
import asyncio, json, pathlib, sys, urllib.request
import websockets

NOTEBOOK_MATCH = 'notebook.google.com/notebook/6a6f999b'
OUT = sys.argv[1] if len(sys.argv) > 1 else '/tmp/notebook'

tabs = json.load(urllib.request.urlopen('http://localhost:9223/json'))
tab = next(t for t in tabs if NOTEBOOK_MATCH in t.get('url', ''))

async def main():
    async with websockets.connect(tab['webSocketDebuggerUrl'], max_size=50*1024*1024) as ws:
        mid = 0
        async def js(expr):
            nonlocal mid
            mid += 1
            await ws.send(json.dumps({'id': mid, 'method': 'Runtime.evaluate',
                                      'params': {'expression': expr, 'returnByValue': True}}))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get('id') == mid:
                    return msg['result']['result']['value']
        full = await js("[...document.querySelectorAll('chat-message,[class*=\"chat-message\"],.message-content')].map((m,i)=>'=== MESSAGE '+i+' ===\\n'+m.innerText).join('\\n\\n') || 'NO MESSAGES'")
        last = await js("(function(){const m=[...document.querySelectorAll('chat-message')];return m.length?m[m.length-1].innerText:'NONE';})()")
        pathlib.Path(OUT + '-transcript.txt').write_text(full)
        pathlib.Path(OUT + '-final.txt').write_text(last)
        print('wrote', OUT + '-transcript.txt', len(full), 'chars;', OUT + '-final.txt', len(last), 'chars')

asyncio.run(main())
