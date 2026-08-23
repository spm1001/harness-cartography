"""Score a parsed report into rubric cells via the instrument's §6 mapping.

The scorer is deliberately conservative: a level is assigned only when the
discriminating item PASSED (item N ✓ ⇒ dimension ≥ boundary level). Mixed and
qualified outcomes prove nothing mechanically — they surface as flags for a
human/Claude judgement pass instead. Every cell carries provenance and the run
date; the instrument's rule is that a cell without a date is decoration, so
emitting undated cells is a hard error here.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .parsing import Report

DIMENSIONS = [
    "computation",
    "world_reading",
    "world_writing",
    "corpus_vision",
    "persistence",
    "self_extension",
    "delegation",
    "output_rendering",
]

FREEDOM_DIMS = DIMENSIONS[:7]  # everything except output_rendering

# (item, dimension, level proved by a clean pass) — instrument.md §6.
PASS_PROVES = [
    (1, "computation", 1),
    (2, "computation", 2),
    (3, "computation", 3),
    (3, "self_extension", 2),
    (4, "world_reading", 1),
    (5, "world_reading", 2),
    (6, "world_reading", 3),
    (7, "world_writing", 1),
    (8, "output_rendering", 1),
    (9, "corpus_vision", 1),
    (10, "persistence", 2),
    (11, "self_extension", 2),
    (12, "delegation", 1),
    (13, "persistence", 3),
]

# Keyword assists: a pass whose evidence carries these upgrades the level, with
# the keyword recorded in the cell so the upgrade is auditable.
KEYWORD_UPGRADES = [
    (8, "output_rendering", 2, ("png", "image", "chart", "plot", "widget")),
    (11, "self_extension", 3, ("inherit", "future session")),
    (12, "delegation", 2, ("subagent", "sub-agent")),
]

# Items whose ladder position a rule cannot fully settle — always flagged.
JUDGEMENT_ITEMS = {
    7: "world_writing ladder position (1→3) needs the evidence read",
    9: "corpus_vision 1↔2 undiscriminated when the source is small",
    10: "persistence rests on the canary prediction until the sweep verifies it",
}


@dataclass
class Cell:
    dimension: str
    level: int
    provenance: str
    date: str
    proved_by: list[int] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.date:
            raise ValueError(f"cell {self.dimension} has no date — refuse to emit")


@dataclass
class ScoredRun:
    surface: str
    date: str
    cells: dict[str, Cell]

    @property
    def freedom(self) -> int:
        return sum(self.cells[d].level for d in FREEDOM_DIMS)

    @property
    def furniture(self) -> int:
        return self.cells["output_rendering"].level

    @property
    def past_shell_line(self) -> bool:
        return self.cells["computation"].level >= 3


def score(report: Report) -> ScoredRun:
    cells = {
        d: Cell(dimension=d, level=0, provenance="measured", date=report.date)
        for d in DIMENSIONS
    }
    for item_no, dim, level in PASS_PROVES:
        item = report.items.get(item_no)
        if item is None:
            continue
        cell = cells[dim]
        if item.verdict == "pass":
            if level > cell.level:
                cell.level = level
            cell.proved_by.append(item_no)
        elif item.verdict in ("mixed", "unknown"):
            cell.flags.append(
                f"item {item_no} {item.verdict} ({item.outcome_raw!r}) — "
                f"level {level} unproven, judge from evidence"
            )
        # a clean fail proves the boundary was reached and refused/failed:
        # the level simply stays below; no flag needed, the table shows it.

    for item_no, dim, level, keywords in KEYWORD_UPGRADES:
        item = report.items.get(item_no)
        if item is None or item.verdict != "pass":
            continue
        hit = next((k for k in keywords if k in item.evidence.lower()), None)
        if hit and level > cells[dim].level:
            cells[dim].level = level
            cells[dim].proved_by.append(item_no)
            cells[dim].flags.append(f"level {level} via keyword {hit!r} in item {item_no} — audit the evidence")

    for item_no, note in JUDGEMENT_ITEMS.items():
        item = report.items.get(item_no)
        if item is not None and item.verdict != "fail":
            cells[dim_for_judgement(item_no)].flags.append(note)

    return ScoredRun(surface=report.surface, date=report.date, cells=cells)


def dim_for_judgement(item_no: int) -> str:
    return {7: "world_writing", 9: "corpus_vision", 10: "persistence"}[item_no]


def cell_table_markdown(run: ScoredRun) -> str:
    lines = [
        f"## Scored cells — {run.surface}, {run.date} (rule-derived; flags need judgement)",
        "",
        "| Dimension | Level | Proved by items | Flags |",
        "|---|---|---|---|",
    ]
    for d in DIMENSIONS:
        c = run.cells[d]
        flags = "; ".join(c.flags) or "—"
        proved = ", ".join(map(str, sorted(set(c.proved_by)))) or "—"
        lines.append(f"| {d} | {c.level} | {proved} | {flags} |")
    lines.append("")
    lines.append(
        f"Freedom (sum of 7 primitives): **{run.freedom}**/21 · "
        f"Furniture (output rendering): **{run.furniture}**/3 · "
        f"Shell line: {'past' if run.past_shell_line else 'below'}"
    )
    return "\n".join(lines)
