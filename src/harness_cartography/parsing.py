"""Parse a run report .md into a structured report.

Five runs exist in four table dialects (2026-08-23 survey):
  | 1 | ✓ | ✓ | evidence |                      cowork-local / cowork-cloud
  | 1 Arithmetic | Yes | ✓ | evidence | — |      cowork-chrome
  | 1 | Yes | ✓ (partial) | evidence |           claude-code-stock
  | 1 | Yes | ✗ install ... ✓ (Files) | ... | — | gemini-notebook (mixed outcomes)

The parser is deliberately tolerant: an item row is any table row whose first
cell begins with an integer. Attempted is truthy for ✓/Yes/Y; the outcome cell
is kept raw and classified into pass / fail / mixed / unknown.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

ITEM_ROW = re.compile(r"^\|\s*(\d+)\b([^|]*)\|")
FILENAME = re.compile(r"^(?P<surface>[a-z0-9-]+)-(?P<date>\d{4}-\d{2}-\d{2})\.md$")


@dataclass
class Item:
    number: int
    label: str
    attempted: bool
    outcome_raw: str
    verdict: str  # 'pass' | 'fail' | 'mixed' | 'unknown'
    evidence: str
    refusal: str = ""


@dataclass
class Report:
    surface: str
    date: str
    path: str
    items: dict[int, Item] = field(default_factory=dict)

    @property
    def letter_version(self) -> int:
        """13 items means v2; 12 means v1. Anything else is a parse smell."""
        return 2 if 13 in self.items else 1


def classify_outcome(cell: str) -> str:
    has_pass = "✓" in cell
    has_fail = "✗" in cell
    if has_pass and has_fail:
        return "mixed"
    if has_pass:
        # '✓ (partial)' etc. still demonstrated the capability at least once,
        # but flag qualified passes as mixed so the scorer stays conservative.
        return "mixed" if "partial" in cell.lower() else "pass"
    if has_fail:
        return "fail"
    return "unknown"


def parse_row(line: str) -> Item | None:
    m = ITEM_ROW.match(line)
    if not m:
        return None
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) < 4:
        return None
    number = int(m.group(1))
    label = m.group(2).strip()
    attempted = bool(re.search(r"✓|yes|^y$", cells[1], re.IGNORECASE))
    outcome_raw = cells[2]
    evidence = cells[3]
    refusal = cells[4] if len(cells) > 4 else ""
    return Item(
        number=number,
        label=label,
        attempted=attempted,
        outcome_raw=outcome_raw,
        verdict=classify_outcome(outcome_raw),
        evidence=evidence,
        refusal=refusal,
    )


def parse_run(path: str | Path) -> Report:
    path = Path(path)
    m = FILENAME.match(path.name)
    if not m:
        raise ValueError(f"run filename must be <surface>-<YYYY-MM-DD>.md: {path.name}")
    report = Report(surface=m.group("surface"), date=m.group("date"), path=str(path))
    for line in path.read_text().splitlines():
        item = parse_row(line)
        # First occurrence wins: some files quote the letter (or other tables)
        # after the report table; item numbers never repeat inside one table.
        if item is not None and item.number not in report.items and item.number <= 13:
            report.items[item.number] = item
    if not report.items:
        raise ValueError(f"no report-table rows found in {path}")
    expected = 13 if 13 in report.items else 12
    missing = sorted(set(range(1, expected + 1)) - set(report.items))
    if missing:
        raise ValueError(f"{path.name}: report table missing items {missing}")
    return report
