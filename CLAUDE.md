# Harness-cartography

Kinetic layer for harness cartography — administers the probe letter across surfaces (passe runners) and scores the reports into cell tables and plots.

**The knowledge lives in `~/notes/practices/harness-cartography/`** — the instrument (rubric, surface inventory, probe letter), the dated run reports, and the frame. This repo is the code that acts on it, split per the lozuko boundary (knowledge in notes, code near its tests). Read the room's `CLAUDE.md` → Status before working here: it says which runs exist, what's unfrozen, and what's due.

## Quick Commands

```bash
uv run --group dev pytest          # run tests
uv pip install -e .                # editable install
```

## Module Map

| Module | Role |
|--------|------|
| *(none yet)* | Scaffolded 2026-08-23; first modules arrive with the scoring automation (cart board) |

Planned shape, from the room's instrument.md §7:

| Planned module | Role |
|--------|------|
| `scoring` | Parse a run report's item table → rubric cell table (level, friction, wall type, provenance, date) |
| `plotting` | Cell table → Freedom/Furniture projection with shell-line and browser-line markers |
| `runners/` | Passe scripts that administer the letter inside browser surfaces (Gemini Notebook first) |

## Key Conventions

- **Run reports stay in notes** (`practices/harness-cartography/runs/`, one file per surface per date). This repo reads them by path; it never becomes the canonical store. The report table format is defined in the letter itself (instrument.md §5) — if parsing needs the format to change, that's a letter edit, which is a notes-side decision.
- **`tools/canary-sweep.py` and `tools/room-census.py` currently live room-side** (in notes, minted by probe subjects mid-run). Migrating them here is tracked on the cart board — don't duplicate them; if you improve one, decide its home first.
- **Provenance discipline is the product.** Every scored cell carries level + friction + wall type + provenance + date. A cell without a date is decoration (instrument.md §1). Scoring code must refuse to emit undated cells rather than defaulting.
- **Probes run in-situ only.** Never administer the letter through an API stand-in — the API is a different harness. Passe drives tube's logged-in Chrome for browser surfaces.
- Python means `uv`; PEP 723 for standalone runners, the package for shared parsing/scoring logic.
