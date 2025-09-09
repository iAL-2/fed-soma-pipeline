# soma_dashboard_interactive.py
"""
Build a single interactive HTML dashboard (Plotly) for SOMA summary data.
- Input:  data/soma_summary_weekly.csv  (WIDE format: as_of_date, total, mbs, tips, frn, bills, agencies, cmbs, ...)
- Output: data/soma_dashboard.html       (open in your browser)

Charts:
1) Net weekly change (bars) + rolling trend
2) Cumulative change since ANCHOR_DATE
3) Composition by category (levels, last N years)
4) Composition share % (last N years)
5) Total (last N years)

Polish:
- Range slider + quick buttons
- $ formatting
- “Last updated” timestamp
- QT anchor annotation (safe for pandas.Timestamp)
"""

from pathlib import Path
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

# --------- CONFIG ---------
DATA_DIR = Path("data")
WIDE_CSV = DATA_DIR / "soma_summary_weekly.csv"
OUT_HTML = DATA_DIR / "soma_dashboard.html"

ANCHOR_DATE = pd.Timestamp("2017-06-01")  # change if you want a different baseline
ROLL_W = 4                                # rolling window for trend line (weeks)
ZOOM_YEARS = 6                            # “recent” window on the composition/total charts
# -----------------------------------------


# ===== Helpers =====
def load_wide() -> pd.DataFrame:
    df = pd.read_csv(WIDE_CSV, parse_dates=["as_of_date"]).sort_values("as_of_date")
    # force numeric for all non-date columns
    value_cols = [c for c in df.columns if c != "as_of_date"]
    df[value_cols] = df[value_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    if "total" not in df.columns:
        raise RuntimeError(f"'total' column not found. Columns: {df.columns.tolist()}")
    return df

def dollars_axis_layout(fig: go.Figure, trillions=False):
    fig.update_yaxes(tickformat="$,.1fT" if trillions else "$,.0f")

def add_ranges(fig: go.Figure):
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
    if df.empty:
        return df
    cutoff = df["as_of_date"].max() - pd.DateOffset(years=years)
    return df[df["as_of_date"] >= cutoff]

def _to_py_dt(x):
    """Convert pandas/NumPy timestamps (or strings) into plain Python datetime."""
    if hasattr(x, "to_pydatetime"):
        return x.to_pydatetime()
    if isinstance(x, pd.Timestamp):
        return x.to_pydatetime()
    if isinstance(x, datetime):
        return x
    return pd.to_datetime(x).to_pydatetime()

def qt_annotation(fig: go.Figure, anchor, text="QT start", x_min=None, x_max=None):
    """Add a vertical line at 'anchor' only if it’s within [x_min, x_max].
    Uses a separate add_annotation so datetimes are safe.
    """
    try:
        x = _to_py_dt(anchor)
    except Exception:
        return  # skip if unparseable

    if x_min is not None and x < _to_py_dt(x_min):
        return
    if x_max is not None and x > _to_py_dt(x_max):
        return

    # Draw the vertical line
    fig.add_vline(x=x, line_width=1, line_dash="dot", line_color="gray")

    # Add a label pinned to the top of the plotting area (paper coords on Y)
    fig.add_annotation(
        x=x, y=1.0, xref="x", yref="paper",
        text=text, showarrow=False,
        xanchor="left", yanchor="bottom",
        bgcolor="rgba(255,255,255,0.6)", bordercolor="gray", borderwidth=1
    )


def fig_to_section(fig: go.Figure, title: str) -> str:
    # produce partial HTML to embed all figures in one page
    return f"""
<section style="margin: 20px 0;">
  <h2 style="font-family: system-ui, -apple-system, Segoe UI, Roboto; margin: 8px 0 0 6px;">
    {title}
  </h2>
  {pio.to_html(fig, full_html=False, include_plotlyjs=False)}
</section>
"""


# ===== Figures =====
def fig_weekly_change(df: pd.DataFrame) -> go.Figure:
    s = df.set_index("as_of_date")["total"].sort_index()
    wow = s.diff()
    wow_roll = wow.rolling(ROLL_W, min_periods=1).mean()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=wow.index, y=wow.values, name="Weekly Δ (WoW)",
        hovertemplate="%{x|%Y-%m-%d}<br>Δ: $%{y:,.0f}<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=wow_roll.index, y=wow_roll.values, name=f"Rolling {ROLL_W}-week", mode="lines"
    ))
    fig.add_hline(y=0, line_width=1, line_color="gray")

    dollars_axis_layout(fig, trillions=False)
    add_ranges(fig)
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
    s = df.set_index("as_of_date")["total"].sort_index()
    s = s[s.index >= ANCHOR_DATE] if (s.index >= ANCHOR_DATE).any() else s
    anchor_date = s.index.min()
    cum = s - s.iloc[0]

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
    parts = [c for c in df.columns if c not in ("as_of_date", "total")]
    if not parts:
        return go.Figure()
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
    parts = [c for c in df.columns if c not in ("as_of_date", "total")]
    if not parts:
        return go.Figure()
    sub = last_n_years(df[["as_of_date", "total"] + parts], ZOOM_YEARS).copy()
    sub["total"] = sub["total"].replace(0, pd.NA)
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


# ===== Main =====
def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    wide = load_wide()

    # Build figures
    f1 = fig_weekly_change(wide)
    f2 = fig_cumulative(wide)
    f3 = fig_composition_levels_last2y(wide)
    f4 = fig_composition_share_last2y(wide)
    f5 = fig_total_last2y(wide)

    # Wrap in a simple HTML page and write once
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
    body = (
        fig_to_section(f1, "Net Weekly Change (WoW) + Rolling Trend") +
        fig_to_section(f2, f"Cumulative Change Since {max(ANCHOR_DATE, wide['as_of_date'].min()).date()}") +
        fig_to_section(f3, f"Composition by Category — Levels (Last {ZOOM_YEARS} Years)") +
        fig_to_section(f4, f"Composition Share (Last {ZOOM_YEARS} Years)") +
        fig_to_section(f5, f"Total Holdings (Last {ZOOM_YEARS} Years)")
    )

    html = head + body + "\n</body>\n</html>"
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT_HTML.resolve()} — open it in your browser.")

if __name__ == "__main__":
    main()
