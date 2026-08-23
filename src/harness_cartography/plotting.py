"""Project scored runs onto the Freedom/Furniture plane.

One point per surface. The two thresholds from the instrument are drawn as
annotations: surfaces past the shell line (computation 3) get a distinct
marker, and browser-line crossings — a fact about the run's topology that no
report table carries — are supplied explicitly by the caller and shown as a
ring. The plot is a projection of the cell table; regenerate, never edit.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .scoring import ScoredRun


def plot_runs(
    runs: list[ScoredRun],
    out_path: str | Path,
    browser_line_surfaces: set[str] | None = None,
) -> Path:
    browser = browser_line_surfaces or set()
    fig, ax = plt.subplots(figsize=(9, 6))

    # Rule-scored levels are coarse, so distinct surfaces routinely land on the
    # same (freedom, furniture) point; dodge coincident points vertically and
    # stagger labels so every surface stays visible.
    seen: dict[tuple[int, int], int] = {}
    for run in runs:
        key = (run.freedom, run.furniture)
        rank = seen.get(key, 0)
        seen[key] = rank + 1
        y = run.furniture + rank * 0.14
        marker = "^" if run.past_shell_line else "o"
        ax.scatter(
            run.freedom,
            y,
            marker=marker,
            s=180,
            zorder=3,
            edgecolors="black" if run.surface in browser else "none",
            linewidths=2.5,
        )
        side = -1 if rank % 2 else 1
        ax.annotate(
            f"{run.surface} ({run.date})",
            (run.freedom, y),
            textcoords="offset points",
            xytext=(12, 4 + side * 6 * rank),
            fontsize=8,
        )

    ax.set_xlabel("Freedom — sum of the 7 primitive dimensions (max 21)")
    ax.set_ylabel("Furniture — output rendering level (max 3)")
    ax.set_xlim(-0.5, 21.5)
    ax.set_ylim(-0.3, 3.5)
    ax.set_title("Harness cartography — Freedom vs Furniture (rule-scored cells)")
    ax.grid(True, alpha=0.3, zorder=0)

    handles = [
        plt.Line2D([], [], marker="^", linestyle="", markersize=10, color="grey", label="past the shell line (computation 3)"),
        plt.Line2D([], [], marker="o", linestyle="", markersize=10, color="grey", label="below the shell line"),
        plt.Line2D([], [], marker="s", linestyle="", markersize=10, markerfacecolor="lightgrey", markeredgecolor="black", markeredgewidth=2.5, label="black edge = crosses the browser line (either shape)"),
    ]
    ax.legend(handles=handles, loc="upper left", fontsize=8)

    out_path = Path(out_path)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path
