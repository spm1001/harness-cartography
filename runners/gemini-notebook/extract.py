# /// script
# requires-python = ">=3.11"
# dependencies = ["websockets"]
# ///
import asyncio, json, pathlib, urllib.request
import websockets
tabs = json.load(urllib.request.urlopen('http://localhost:9223/json'))
tab = next(t for t in tabs if 'notebook.google.com/notebook/6a6f999b' in t.get('url',''))
async def main():
    async with websockets.connect(tab['webSocketDebuggerUrl'], max_size=50*1024*1024) as ws:
        await ws.send(json.dumps({'id':1,'method':'Runtime.evaluate','params':{'expression':
            "(function(){const msgs=[...document.querySelectorAll('chat-message,[class*=\"chat-message\"],.message-content')];if(msgs.length)return msgs.map((m,i)=>'=== MESSAGE '+i+' ===\\n'+m.innerText).join('\\n\\n');const p=document.querySelector('chat-panel,[class*=\"chat-panel\"]');return p?p.innerText:'NO PANEL';})()",'returnByValue':True}}))
        while True:
            msg = json.loads(await ws.recv())
            if msg.get('id')==1:
                text = msg['result']['result']['value']
                pathlib.Path('/tmp/notebook-transcript.txt').write_text(text)
                print('saved', len(text), 'chars')
                break
asyncio.run(main())
