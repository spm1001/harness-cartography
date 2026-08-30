# Gemini Notebook runner — first used 2026-08-23

Administers the probe letter into a Gemini Notebook chat via CDP on tube's session
Chrome (`:9223`). `administer.py` types the letter and submits; `extract.py` pulls the
chat transcript. Both are PEP 723 scripts (`uv run --script`). The notebook id is
hardcoded per run — edit before use; a parameterised runner arrives with cart-cefawo.

Four hard-won rules (full detail: notes runs/gemini-notebook-2026-08-23.md §Administration findings):

1. **`Page.bringToFront` before any input** — a background tab is input-deaf.
2. **Type with real `Input.dispatchKeyEvent`s** (Shift+Enter for newlines) — the app's
   model ignores DOM-stuffing and `Input.insertText`, however trusted.
3. **The query box silently caps ~3.9k chars** (send button just disables) — split the
   letter after item 7, one administrator's note per part.
4. **Poll the "Responding…"/stop indicator for completion** — innerText stability lies
   during thinking pauses.

Two more, both learned on the 2026-08-30 canary read, and both produced a **false null**
before they were caught — the failure mode here is a probe that answers "not there" about
a thing that is plainly there:

5. **Rule 2 generalises from typing to clicking: `passe run -c 'click …'` does not open
   this app's artifact cards.** It returns `{"verb":"click","ms":2.9}` — success, instantly —
   and nothing happens, because the Angular card ignores a synthetic DOM click exactly as
   it ignores `Input.insertText`. Use raw CDP `Input.dispatchMouseEvent`
   (`mouseMoved` → `mousePressed` → `mouseReleased`) at the element's bounding-rect centre,
   after `Page.bringToFront`. `read-artifact.py` does this. **Aim at the artifact's title
   span, never the row-end kebab (`more_vert`)** — that menu carries the destructive actions.
6. **Always pass `--tab notebook.google.com`, and read `final_url` before believing any
   result.** `passe --reuse-tab` re-anchored onto an unrelated Looker Studio tab of the
   human's — tube's `:9223` is his *session* Chrome, so his tabs and the runner's share one
   browser, and the reuse ladder can pick his. An `eval` against the wrong page returns an
   empty string, which is indistinguishable from "the element is absent".

Rules 2, 5 and 6 are passe gaps, not facts of nature — filed on the passe-partout
board as **ppt-zirehi** (2026-08-30), with the working CDP sequences pointed at from
there. *(The 2026-08-23 run's closing note cited these as "passe-hefovo"; no such item
ever existed — that board's prefix is `ppt` — so the gaps went unfiled for a week.)*

**Verifying a canary is a content read, not a list read.** The artifact's filename in the
Studio list proves a row exists; it does not prove the token survived. Worse, the token
string usually also appears in the chat transcript on the same page, so
`document.body.innerText.includes(TOKEN)` returns true either way. The discriminating
measure is the **occurrence count before vs after opening the artifact** — a rise means the
viewer rendered the content. `read-artifact.py` reports both numbers.
