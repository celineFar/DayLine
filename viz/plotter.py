# viz/plotter.py

import io
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from config.settings import DAY_MINUTES


def render_timeline_png(wide) -> bytes:
    sources = pd.unique(
        pd.Series(src for day in wide["intervals"] for _, _, src in day)
    )

    color_map = dict(zip(sources, plt.cm.tab10.colors))
    color_map["Sleep"] = "lightpink"

    fig, ax = plt.subplots(figsize=(14, 6))
    bar_height = 0.6

    for y, row in enumerate(wide.itertuples()):
        intervals = sorted(row.intervals)
        last_end = 0

        for start, duration, _ in intervals:
            if start > last_end:
                ax.broken_barh(
                    [(last_end, start - last_end)],
                    (y - bar_height / 2, bar_height),
                    color="lightgray",
                )
            last_end = start + duration

        if last_end < DAY_MINUTES:
            ax.broken_barh(
                [(last_end, DAY_MINUTES - last_end)],
                (y - bar_height / 2, bar_height),
                color="lightgray",
            )

        for start, duration, src in intervals:
            ax.broken_barh(
                [(start, duration)],
                (y - bar_height / 2, bar_height),
                color=color_map[src],
            )

    for m in range(0, DAY_MINUTES + 1, 60):
        ax.axvline(m, color="#b8c4d6", linewidth=0.8, alpha=0.8)

    ticks = np.arange(0, DAY_MINUTES + 1, 30)
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{m//60:02d}:{m%60:02d}" for m in ticks], rotation=45)

    ax.set_xlim(0, DAY_MINUTES)
    ax.set_yticks(range(len(wide)))
    ax.set_yticklabels(wide["Date"].dt.strftime("%Y-%m-%d"))
    ax.invert_yaxis()

    legend = (
        [Patch(color=color_map[s], label=s) for s in color_map]
        + [Patch(color="lightgray", label="Idle")]
    )

    ax.legend(handles=legend)
    ax.set_title("Daily Activity Timeline (Sleep ≤ 04:00)")
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    return buf.getvalue()
