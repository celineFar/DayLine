# app/preview_service.py

from infra.activity_repo import load_activities
from domain.timeline import build_wide_intervals
from viz.plotter import render_timeline_png as render_plot_png, format_duration


def render_timeline_png(start_date=None, end_date=None) -> tuple[bytes, str]:
    """
    Render timeline chart and generate text summary.
    Returns (png_bytes, summary_text).
    """
    df = load_activities(start_date, end_date)
    wide = build_wide_intervals(df)
    png_bytes, stats = render_plot_png(wide)

    # Generate text summary
    summary = _generate_text_summary(stats)

    return png_bytes, summary


def _generate_text_summary(stats: dict) -> str:
    """Generate a text summary of daily activity totals."""
    if not stats["daily"]:
        return ""

    lines = ["📊 *Daily Summary*"]

    # Sort dates
    sorted_dates = sorted(stats["daily"].keys())

    for date in sorted_dates:
        day_data = stats["daily"][date]
        if not day_data:
            continue

        # Sort categories for consistent display
        parts = []
        for category in sorted(day_data.keys()):
            minutes = day_data[category]
            parts.append(f"{category}: {format_duration(minutes)}")

        lines.append(f"`{date}`: {', '.join(parts)}")

    return "\n".join(lines)
