"""Pipeline tests: hermetic fixtures for the dialects, plus end-to-end runs
over the real notes report files where present (skipped elsewhere)."""
from pathlib import Path

import pytest

from harness_cartography.parsing import classify_outcome, parse_run
from harness_cartography.plotting import plot_runs
from harness_cartography.scoring import score

RUNS_DIR = Path.home() / "notes/practices/harness-cartography/runs"
REAL_RUNS = [
    "cowork-local-2026-08-15.md",
    "cowork-cloud-2026-08-15.md",
    "cowork-chrome-2026-08-15.md",
    "gemini-notebook-2026-08-23.md",
]

# One synthetic run exercising all four observed dialects and a mixed outcome.
FIXTURE = """# Run: synthetic fixture

## Report table

| # | Attempted? | Outcome | Evidence | If ✗ |
|---|---|---|---|---|
| 1 Arithmetic | Yes | ✓ | Head and tool both 6,765,561. | — |
| 2 | ✓ | ✓ | State survived a second execution. |
| 3 | Yes | ✓ import · ✗ install | import fine; pip BLOCKED: no internet. | failed |
| 4 | Yes | ✓ | Live headline fetched. | — |
| 5 | Yes | ✓ | Exact page title quoted. | — |
| 6 | Yes | ✗ | No connectors exist. | failed |
| 7 | Yes | ✓ | Durable file synced to store. | — |
| 8 | Yes | ✓ | Static image quadratic_plot.png produced. | — |
| 9 | Yes | ✓ | Opening and final sentences quoted. | — |
| 10 | Yes | ✓ | CANARY-fixture-2026-08 stored in canary.txt. | — |
| 11 | Yes | ✓ | Built a tool; future session inherits it read-only. | — |
| 12 | Yes | ✓ (partial) | Threads only. | — |
| 13 | Yes | ✗ | No cron; container dies with session. | failed |
"""


@pytest.fixture
def fixture_run(tmp_path):
    p = tmp_path / "fixture-surface-2026-08-23.md"
    p.write_text(FIXTURE)
    return p


def test_classify_outcome_variants():
    assert classify_outcome("✓") == "pass"
    assert classify_outcome("✗") == "fail"
    assert classify_outcome("✗ install ✓ import") == "mixed"
    assert classify_outcome("✓ (partial)") == "mixed"
    assert classify_outcome("—") == "unknown"


def test_parse_fixture_dialects(fixture_run):
    r = parse_run(fixture_run)
    assert r.surface == "fixture-surface"
    assert r.date == "2026-08-23"
    assert r.letter_version == 2
    assert len(r.items) == 13
    assert r.items[1].label == "Arithmetic"
    assert r.items[2].attempted  # ✓ dialect for attempted
    assert r.items[3].verdict == "mixed"
    assert r.items[12].verdict == "mixed"  # qualified pass stays conservative


def test_score_fixture_levels(fixture_run):
    run = score(parse_run(fixture_run))
    c = run.cells
    assert c["computation"].level == 2  # item 3 mixed → 3 unproven
    assert c["world_reading"].level == 2  # item 6 failed cleanly
    assert c["output_rendering"].level == 2  # artifact marker '.png' in evidence
    assert c["self_extension"].level == 2  # item 11 pass proves 2; 3 is hint-only
    assert any("planted by the question" in f for f in c["self_extension"].flags)
    assert c["persistence"].level == 2  # item 13 failed → 3 unproven
    assert c["delegation"].level == 0  # item 12 mixed proves nothing
    assert any("item 3" in f for f in c["computation"].flags)
    assert not run.past_shell_line
    # every cell dated
    assert all(cell.date == "2026-08-23" for cell in c.values())


def test_walls_recorded_from_refusal_column(fixture_run):
    run = score(parse_run(fixture_run))
    assert any("✗-plumbing" in w for w in run.cells["world_reading"].walls)  # item 6 fail
    assert any("✗-plumbing" in w for w in run.cells["persistence"].walls)  # item 13 no cron


def test_planted_vocabulary_never_upgrades(tmp_path):
    """A subject answering NO in the question's own words must not score the level.
    Regression for the cowork-chrome 'Inheritance: no direct route' → SE 3 bug."""
    rows = FIXTURE.replace(
        "| 11 | Yes | ✓ | Built a tool; future session inherits it read-only. | — |",
        "| 11 | Yes | ✓ | Built and ran it. Inheritance: no direct route — no future session inherits anything. | — |",
    )
    p = tmp_path / "negative-surface-2026-08-23.md"
    p.write_text(rows)
    run = score(parse_run(p))
    assert run.cells["self_extension"].level == 2  # never 3 from prose substrings


def test_undated_cell_refused():
    from harness_cartography.scoring import Cell

    with pytest.raises(ValueError, match="no date"):
        Cell(dimension="computation", level=1, provenance="measured", date="")


def test_missing_item_is_error(tmp_path):
    p = tmp_path / "broken-run-2026-01-01.md"
    p.write_text("| 1 | Yes | ✓ | only item one | — |\n| 5 | Yes | ✓ | gap | — |\n")
    with pytest.raises(ValueError, match="missing items"):
        parse_run(p)


def test_known_bad_no_table(tmp_path):
    p = tmp_path / "empty-run-2026-01-01.md"
    p.write_text("# nothing here\n")
    with pytest.raises(ValueError, match="no report-table rows"):
        parse_run(p)


def test_plot_renders(fixture_run, tmp_path):
    run = score(parse_run(fixture_run))
    out = plot_runs([run], tmp_path / "proj.png", {"fixture-surface"})
    assert out.exists() and out.stat().st_size > 10_000


@pytest.mark.skipif(not RUNS_DIR.exists(), reason="notes runs dir not on this host")
@pytest.mark.parametrize("name", REAL_RUNS)
def test_real_runs_parse_and_score(name):
    path = RUNS_DIR / name
    if not path.exists():
        pytest.skip(f"{name} absent")
    run = score(parse_run(path))
    assert 0 < run.freedom <= 21
    assert all(cell.date for cell in run.cells.values())
