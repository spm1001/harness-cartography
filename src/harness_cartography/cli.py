"""score — parse, score and plot harness-cartography run files.

Usage:
    score run1.md [run2.md ...] [--plot out.png] [--browser-line surface ...]

Prints one cell table per run (markdown). With --plot, also renders the
Freedom/Furniture projection. Browser-line crossings are run topology the
report table cannot carry, so they are named explicitly by the administrator.
"""
from __future__ import annotations

import argparse
import sys

from .parsing import parse_run
from .plotting import plot_runs
from .scoring import cell_table_markdown, score


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="score", description=__doc__)
    ap.add_argument("runs", nargs="+", help="run report .md files (<surface>-<date>.md)")
    ap.add_argument("--plot", help="write the Freedom/Furniture projection PNG here")
    ap.add_argument(
        "--browser-line",
        nargs="*",
        default=[],
        help="surfaces that cross the browser line (administrator-supplied)",
    )
    args = ap.parse_args(argv)

    scored = []
    for path in args.runs:
        report = parse_run(path)
        run = score(report)
        scored.append(run)
        print(cell_table_markdown(run))
        print()

    if args.plot:
        out = plot_runs(scored, args.plot, set(args.browser_line))
        print(f"plot written: {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
