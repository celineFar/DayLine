# app/preview_service.py

from infra.activity_repo import load_activities
from domain.timeline import build_wide_intervals
from viz.plotter import render_timeline_png as render_plot_png


def render_timeline_png(start_date=None, end_date=None) -> bytes:
    df = load_activities(start_date, end_date)
    wide = build_wide_intervals(df)
    return render_plot_png(wide)
