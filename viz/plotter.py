# viz/plotter.py

import io
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for faster rendering
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from config.settings import DAY_MINUTES


def calculate_daily_totals(wide) -> dict:
    """Calculate total minutes per category per day and overall totals."""
    daily_totals = {}  # {date: {category: minutes}}
    category_totals = {}  # {category: total_minutes}

    for row in wide.itertuples():
        date_str = row.Date.strftime("%Y-%m-%d")
        daily_totals[date_str] = {}

        for start, duration, source in row.intervals:
            if source not in daily_totals[date_str]:
                daily_totals[date_str][source] = 0
            daily_totals[date_str][source] += duration

            if source not in category_totals:
                category_totals[source] = 0
            category_totals[source] += duration

    return {
        "daily": daily_totals,
        "totals": category_totals,
        "num_days": len(wide),
    }


def format_duration(minutes: float) -> str:
    """Format minutes as hours and minutes string."""
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    if hours > 0 and mins > 0:
        return f"{hours}h{mins}m"
    elif hours > 0:
        return f"{hours}h"
    else:
        return f"{mins}m"


def render_timeline_png(wide) -> tuple[bytes, dict]:
    """
    Render timeline chart with summary table.
    Returns (png_bytes, stats_dict) where stats_dict contains daily and total stats.
    """
    sources = pd.unique(
        pd.Series(src for day in wide["intervals"] for _, _, src in day)
    )

    color_map = dict(zip(sources, plt.cm.tab10.colors))
    color_map["Sleep"] = "lightpink"

    # Calculate stats for summary
    stats = calculate_daily_totals(wide)
    categories = sorted(stats["totals"].keys())

    # Create figure with extra space for summary table
    num_days = len(wide)
    fig_height = max(6, 1.5 + num_days * 0.5 + 1.5)  # Extra space for table
    fig, (ax, ax_table) = plt.subplots(
        2, 1,
        figsize=(14, fig_height),
        gridspec_kw={"height_ratios": [num_days, 2], "hspace": 0.3}
    )

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

    ax.legend(handles=legend, loc="upper right")
    ax.set_title("Daily Activity Timeline")

    # Create summary table
    ax_table.axis("off")

    if categories:
        # Build table data
        col_labels = [""] + categories
        row_labels = ["Total", "Avg/day"]

        totals_row = ["Total"] + [format_duration(stats["totals"].get(c, 0)) for c in categories]
        avg_row = ["Avg/day"] + [
            format_duration(stats["totals"].get(c, 0) / max(1, stats["num_days"]))
            for c in categories
        ]

        table_data = [totals_row[1:], avg_row[1:]]

        # Get colors for columns
        col_colors = ["white"] + [color_map.get(c, "white") for c in categories]

        table = ax_table.table(
            cellText=table_data,
            rowLabels=["Total", "Avg/day"],
            colLabels=categories,
            colColours=[color_map.get(c, "lightgray") for c in categories],
            cellLoc="center",
            loc="center",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 1.5)

        ax_table.set_title("Summary", fontsize=11, fontweight="bold")

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)

    return buf.getvalue(), stats
