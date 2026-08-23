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
