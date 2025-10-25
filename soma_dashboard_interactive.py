# =============================================================================
# soma_dashboard_interactive.py  —  BEGINNER-ANNOTATED VERSION
# -----------------------------------------------------------------------------
# Purpose: Build ONE self-contained HTML dashboard (using Plotly) from your
#          weekly SOMA summary CSV and save it to data/soma_dashboard.html.
#
# Input  : data/soma_summary_weekly.csv  (columns: as_of_date, total, mbs, tips, ...)
# Output : data/soma_dashboard.html      (open this file in a browser)
#
# What you get (charts):
# 1) Weekly change bars + a smoother rolling-average line
# 2) Cumulative change since an anchor date (e.g., QT start)
# 3) Composition by category (stacked areas) over the last N years
# 4) Composition as % shares (stacked to 100%) over the last N years
# 5) Total holdings over the last N years
#
# Extra polish:
# - Date range slider + quick range buttons (6M, 1Y, 2Y, All)
# - Dollar formatting on the y-axis
# - "Last updated" timestamp on the page
# - A vertical line + label for a chosen anchor date (e.g., QT start)
#
# How to run:
#   python soma_dashboard_interactive.py
#
# Notes for beginners:
# - Plotly "Figure" = a chart object. We add traces (bars/lines) to it.
# - We wrap multiple figures into one HTML page so you only open one file.
# - If CSV has other categories, they’ll automatically show up in composition charts.
# =============================================================================

from pathlib import Path
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

# --------- CONFIG (easy things you may change) ---------
DATA_DIR = Path("data")                               # where CSV lives and HTML will be written
WIDE_CSV = DATA_DIR / "soma_summary_weekly.csv"       # input CSV (wide format)
OUT_HTML = DATA_DIR / "soma_dashboard.html"           # output HTML dashboard

ANCHOR_DATE = pd.Timestamp("2017-06-01")  # baseline date for "cumulative" and vertical line
ROLL_W = 4                                # rolling window (in weeks) to smooth weekly change
ZOOM_YEARS = 5                            # only show the most recent N years in some charts
# ------------------------------------------------------


# ====== Helpers (small utility functions) ======

def load_wide() -> pd.DataFrame:
    """
    Read the weekly CSV, ensure dates are real dates, sort by date,
    and convert all non-date columns to numbers (fill blanks with 0).
    We also enforce that a 'total' column must exist.
    """
    df = pd.read_csv(WIDE_CSV, parse_dates=["as_of_date"]).sort_values("as_of_date")
    value_cols = [c for c in df.columns if c != "as_of_date"]
    # Convert every value column to numeric; if something is not numeric, make it 0 instead of NaN
    df[value_cols] = df[value_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    if "total" not in df.columns:
        raise RuntimeError(f"'total' column not found. Columns: {df.columns.tolist()}")
    return df

def dollars_axis_layout(fig: go.Figure, trillions=False):
    """
    Make the y-axis show dollars with commas. If 'trillions' is True, show T units.
    Example: $1,234 or $1.2T
    """
    fig.update_yaxes(tickformat="$,.1fT" if trillions else "$,.0f")

def add_ranges(fig: go.Figure):
    """
    Add quick date buttons and a draggable date range slider to the x-axis.
    Buttons: last 6 months, 1 year, 2 years, or All.
    """
    fig.update_xaxes(
        rangeselector=dict(
            buttons=list([
                dict(count=6,  label="6M", step="month", stepmode="backward"),
                dict(count=1,  label="1Y", step="year",  stepmode="backward"),
                dict(count=2,  label="2Y", step="year",  stepmode="backward"),
                dict(step="all", label="All"),
            ])
        ),
        rangeslider=dict(visible=True),
        type="date"
    )

def last_n_years(df: pd.DataFrame, years: int) -> pd.DataFrame:
    """
    Keep only the rows where as_of_date is within the last 'years' years.
    Useful to avoid drawing extremely long histories in some charts.
    """
    if df.empty:
        return df
    cutoff = df["as_of_date"].max() - pd.DateOffset(years=years)
    return df[df["as_of_date"] >= cutoff]

def _to_py_dt(x):
    """
    Convert different timestamp types (pandas/NumPy/string) into a plain Python datetime.
    This makes Plotly's annotation API happier.
    """
    from datetime import datetime as _dt
    if hasattr(x, "to_pydatetime"):
        return x.to_pydatetime()
    if isinstance(x, pd.Timestamp):
        return x.to_pydatetime()
    if isinstance(x, _dt):
        return x
    return pd.to_datetime(x).to_pydatetime()

def qt_annotation(fig: go.Figure, anchor, text="QT start", x_min=None, x_max=None):
    """
    Draw a thin vertical dotted line at 'anchor' (e.g., QT start),
    but only if that date is within the current data range [x_min, x_max].
    Also add a small label at the top of the plot.
    """
    try:
        x = _to_py_dt(anchor)
    except Exception:
        return  # if we can't parse the date, silently skip

    if x_min is not None and x < _to_py_dt(x_min):
        return
    if x_max is not None and x > _to_py_dt(x_max):
        return

    fig.add_vline(x=x, line_width=1, line_dash="dot", line_color="gray")
    fig.add_annotation(
        x=x, y=1.0, xref="x", yref="paper",      # yref="paper" pins it to top of the plotting area
        text=text, showarrow=False,
        xanchor="left", yanchor="bottom",
        bgcolor="rgba(255,255,255,0.6)", bordercolor="gray", borderwidth=1
    )

def fig_to_section(fig: go.Figure, title: str) -> str:
    """
    Convert a Plotly figure into a chunk of HTML we can stitch into our single page.
    We include a <h2> title above each figure for clarity.
    """
    return f"""
<section style="margin: 20px 0;">
  <h2 style="font-family: system-ui, -apple-system, Segoe UI, Roboto; margin: 8px 0 0 6px;">
    {title}
  </h2>
  {pio.to_html(fig, full_html=False, include_plotlyjs=False)}
</section>
"""


# ====== Figures (each function builds one chart) ======

def fig_weekly_change(df: pd.DataFrame) -> go.Figure:
    """
    Chart 1: Weekly change bars + rolling average line.
    - We take the 'total' series and compute the week-over-week difference (diff).
    - Then we compute a rolling mean of that diff to make a smoother trend line.
    """
    s = df.set_index("as_of_date")["total"].sort_index()
    wow = s.diff()                                # week-over-week change (this week - last week)
    wow_roll = wow.rolling(ROLL_W, min_periods=1).mean()  # smooth line over ROLL_W weeks

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=wow.index, y=wow.values, name="Weekly Δ (WoW)",
        hovertemplate="%{x|%Y-%m-%d}<br>Δ: $%{y:,.0f}<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=wow_roll.index, y=wow_roll.values, name=f"Rolling {ROLL_W}-week", mode="lines"
    ))
    fig.add_hline(y=0, line_width=1, line_color="gray")  # zero line for reference

    dollars_axis_layout(fig, trillions=False)
    add_ranges(fig)

    # Add the QT anchor if it lies within our dates:
    xs = wow.index
    if len(xs):
        qt_annotation(fig, ANCHOR_DATE, "QT start",
                      x_min=xs.min().to_pydatetime(), x_max=xs.max().to_pydatetime())

    fig.update_layout(
        title="Fed SOMA Net Weekly Change (bars) with Rolling Trend",
        legend_title=None, margin=dict(l=40, r=20, t=60, b=40), hovermode="x unified",
    )
    fig.update_xaxes(title="")
    fig.update_yaxes(title="Δ Holdings (USD)")
    return fig

def fig_cumulative(df: pd.DataFrame) -> go.Figure:
    """
    Chart 2: Cumulative change since the anchor.
    - Pick the first date at/after ANCHOR_DATE.
    - Subtract the starting value from every point to show change since that start.
    """
    s = df.set_index("as_of_date")["total"].sort_index()
    s = s[s.index >= ANCHOR_DATE] if (s.index >= ANCHOR_DATE).any() else s
    anchor_date = s.index.min()            # actual first date used as baseline
    cum = s - s.iloc[0]                    # value minus the starting value

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=cum.index, y=cum.values, mode="lines", name="Cumulative Δ",
        hovertemplate="%{x|%Y-%m-%d}<br>Δ since anchor: $%{y:,.0f}<extra></extra>"
    ))
    fig.add_hline(y=0, line_width=1, line_color="gray")

    dollars_axis_layout(fig, trillions=False)
    add_ranges(fig)

    xs = cum.index
    if len(xs):
        qt_annotation(fig, anchor_date, f"Anchor: {anchor_date.date()}",
                      x_min=xs.min().to_pydatetime(), x_max=xs.max().to_pydatetime())

    fig.update_layout(
        title=f"Cumulative Change Since {anchor_date.date()}",
        legend_title=None, margin=dict(l=40, r=20, t=60, b=40), hovermode="x unified",
    )
    fig.update_xaxes(title="")
    fig.update_yaxes(title="Δ vs anchor (USD)")
    return fig

def fig_composition_levels_last2y(df: pd.DataFrame) -> go.Figure:
    """
    Chart 3: Composition by category — levels (stacked areas) for last N years.
    - We drop 'as_of_date' and 'total' to get component columns (e.g., mbs, tips).
    - Stacked areas show how each category contributes to the total over time.
    """
    parts = [c for c in df.columns if c not in ("as_of_date", "total")]
    if not parts:
        return go.Figure()  # nothing to plot if no components
    sub = last_n_years(df[["as_of_date"] + parts], ZOOM_YEARS).set_index("as_of_date")

    fig = go.Figure()
    for c in parts:
        fig.add_trace(go.Scatter(
            x=sub.index, y=sub[c], name=c.replace("_", " ").title(),
            stackgroup="one", mode="lines",
            hovertemplate="%{x|%Y-%m-%d}<br>" + c + ": $%{y:,.0f}<extra></extra>"
        ))
    dollars_axis_layout(fig, trillions=False)
    add_ranges(fig)
    fig.update_layout(
        title=f"Composition by Category — Levels (Last {ZOOM_YEARS} Years)",
        legend_title=None, margin=dict(l=40, r=20, t=60, b=40), hovermode="x unified",
    )
    fig.update_xaxes(title="")
    fig.update_yaxes(title="Amount (USD)")
    return fig

def fig_composition_share_last2y(df: pd.DataFrame) -> go.Figure:
    """
    Chart 4: Composition as % shares (stacked to 100%) for last N years.
    - Divide each component by 'total' to get its share.
    - Replace division-by-zero cases with 0.
    """
    parts = [c for c in df.columns if c not in ("as_of_date", "total")]
    if not parts:
        return go.Figure()
    sub = last_n_years(df[["as_of_date", "total"] + parts], ZOOM_YEARS).copy()
    sub["total"] = sub["total"].replace(0, pd.NA)  # avoid divide-by-zero
    for c in parts:
        sub[c] = (sub[c] / sub["total"]).fillna(0.0)

    fig = go.Figure()
    for c in parts:
        fig.add_trace(go.Scatter(
            x=sub["as_of_date"], y=sub[c], name=c.replace("_", " ").title(),
            stackgroup="one", mode="lines",
            hovertemplate="%{x|%Y-%m-%d}<br>" + c + ": %{y:.1%}<extra></extra>"
        ))
    fig.update_yaxes(tickformat=".0%")
    add_ranges(fig)
    fig.update_layout(
        title=f"Composition Share by Category (Last {ZOOM_YEARS} Years)",
        legend_title=None, margin=dict(l=40, r=20, t=60, b=40), hovermode="x unified",
    )
    fig.update_xaxes(title="")
    fig.update_yaxes(title="Share of Total")
    return fig

def fig_total_last2y(df: pd.DataFrame) -> go.Figure:
    """
    Chart 5: Total holdings line over the last N years.
    - Simple line chart of 'total' with the QT anchor marked (if in range).
    """
    sub = last_n_years(df[["as_of_date", "total"]], ZOOM_YEARS)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sub["as_of_date"], y=sub["total"], mode="lines", name="Total",
        hovertemplate="%{x|%Y-%m-%d}<br>Total: $%{y:,.0f}<extra></extra>"
    ))
    dollars_axis_layout(fig, trillions=False)
    add_ranges(fig)

    xs = sub["as_of_date"]
    if len(xs):
        qt_annotation(fig, ANCHOR_DATE, "QT start",
                      x_min=xs.min().to_pydatetime(), x_max=xs.max().to_pydatetime())

    fig.update_layout(
        title=f"SOMA Total Holdings (Last {ZOOM_YEARS} Years)",
        legend_title=None, margin=dict(l=40, r=20, t=60, b=40), hovermode="x unified",
    )
    fig.update_xaxes(title="")
    fig.update_yaxes(title="Total (USD)")
    return fig


# ====== Main (puts it all together into one HTML file) ======

def main():
    """
    - Ensure the data folder exists
    - Load the CSV
    - Build all figures
    - Assemble a small HTML page with a header + timestamp + all figures
    - Write the HTML to disk
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    wide = load_wide()

    # Build each chart (functions above return Plotly Figures)
    f1 = fig_weekly_change(wide)
    f2 = fig_cumulative(wide)
    f3 = fig_composition_levels_last2y(wide)
    f4 = fig_composition_share_last2y(wide)
    f5 = fig_total_last2y(wide)

    # Create the page header (once). We load Plotly JS from a CDN so the file stays small.
    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M")
    head = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Fed SOMA Dashboard</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 18px; }
    h1 { margin: 0 0 4px 6px; font-weight: 650; }
    .sub { color: #666; margin: 0 0 18px 6px; }
    section { border: 1px solid #eee; border-radius: 12px; padding: 8px; }
  </style>
</head>
<body>
  <h1>Fed SOMA Dashboard</h1>
  <div class="sub">Last updated: """ + last_updated + """</div>
"""

    # Convert figures to HTML sections and glue them together
    body = (
        fig_to_section(f1, "Net Weekly Change (WoW) + Rolling Trend") +
        fig_to_section(f2, f"Cumulative Change Since {max(ANCHOR_DATE, wide['as_of_date'].min()).date()}") +
        fig_to_section(f3, f"Composition by Category — Levels (Last {ZOOM_YEARS} Years)") +
        fig_to_section(f4, f"Composition Share (Last {ZOOM_YEARS} Years)") +
        fig_to_section(f5, f"Total Holdings (Last {ZOOM_YEARS} Years)")
    )

    # Wrap up into a full HTML document and write it to disk
    html = head + body + "\n</body>\n</html>"
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT_HTML.resolve()} — open it in your browser.")

# Run main() only when this file is executed directly (not when imported)
if __name__ == "__main__":
    main()
