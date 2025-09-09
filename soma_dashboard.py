import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timedelta

# --------- CONFIG ---------
DATA_DIR = Path("data")
WIDE_CSV = DATA_DIR / "soma_summary_weekly.csv"
LONG_CSV = DATA_DIR / "soma_summary_long.csv"

# Choose the anchor date to accumulate from (QT-era default).
ANCHOR_DATE = pd.Timestamp("2022-06-01")  # change anytime

# Rolling window (in weeks) for smoothing WoW bars
ROLL_W = 4

# Zoom window for “recent” charts (last N years)
ZOOM_YEARS = 2
# --------------------------

def load_wide():
    df = pd.read_csv(WIDE_CSV, parse_dates=["as_of_date"]).sort_values("as_of_date")
    # Ensure numeric columns
    num_cols = [c for c in df.columns if c != "as_of_date"]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    if "total" not in df.columns:
        raise RuntimeError(f"'total' column not found in {WIDE_CSV}. Columns: {df.columns.tolist()}")
    return df

def maybe_load_long():
    if LONG_CSV.exists():
        df = pd.read_csv(LONG_CSV, parse_dates=["as_of_date"]).sort_values(["as_of_date","category"])
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
        return df
    return None

def last_n_years_mask(index, years=2):
    if len(index) == 0:
        return index == index  # empty
    cutoff = index.max() - pd.DateOffset(years=years)
    return index >= cutoff

def plot_wow_bars(total_series: pd.Series, out_path: Path, roll_w=4):
    # Net weekly change
    wow = total_series.diff()
    # Rolling mean for a smoother “trend” line
    wow_roll = wow.rolling(roll_w, min_periods=1).mean()

    ax = wow.plot(kind="bar", title=f"SOMA Net Weekly Change (WoW)  —  rolling {roll_w}-week trend", figsize=(12, 5))
    # Overlay rolling line
    wow_roll.plot(ax=ax)

    ax.axhline(0)
    ax.set_xlabel("Week")
    ax.set_ylabel("Δ Holdings (same units as 'total')")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()

def plot_cumulative_since(total_series: pd.Series, anchor: pd.Timestamp, out_path: Path):
    s = total_series.copy()
    s = s[s.index >= anchor]
    if s.empty:
        # Fallback: start at first available date
        s = total_series
        anchor = s.index.min()
    cum = (s - s.iloc[0])
    ax = cum.plot(title=f"Cumulative Change Since {anchor.date()}", figsize=(12, 5))
    ax.axhline(0)
    ax.set_xlabel("Week")
    ax.set_ylabel("Change vs anchor")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()

def plot_total_zoom(total_series: pd.Series, out_path: Path, years=2):
    mask = last_n_years_mask(total_series.index, years)
    s = total_series[mask]
    title = f"SOMA Total Holdings (Last {years} Years)" if len(s) else "SOMA Total Holdings"
    ax = s.plot(title=title, figsize=(12, 5))
    ax.set_xlabel("Week")
    ax.set_ylabel("Total")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()

def plot_composition_levels_last2y(wide_df: pd.DataFrame, out_path: Path, years=2):
    parts = [c for c in wide_df.columns if c not in ("as_of_date", "total")]
    if not parts:
        return
    df = wide_df.set_index("as_of_date")[parts]
    df = df[df.index >= (df.index.max() - pd.DateOffset(years=years))]
    ax = df.plot.area(title=f"Composition by Category (Levels, Last {years} Years)", figsize=(12, 6))
    ax.set_xlabel("Week")
    ax.set_ylabel("Amount")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()

def plot_composition_share_last2y(wide_df: pd.DataFrame, out_path: Path, years=2):
    parts = [c for c in wide_df.columns if c not in ("as_of_date", "total")]
    if not parts or "total" not in wide_df.columns:
        return
    df = wide_df.set_index("as_of_date")
    df = df[df.index >= (df.index.max() - pd.DateOffset(years=years))]
    # Avoid divide-by-zero
    share = df[parts].div(df["total"].replace(0, pd.NA), axis=0).fillna(0)
    ax = share.plot.area(title=f"Composition Share (Last {years} Years)", figsize=(12, 6))
    ax.set_xlabel("Week")
    ax.set_ylabel("Share of Total")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()

def main():
    DATA_DIR.mkdir(exist_ok=True, parents=True)

    wide = load_wide()
    long_df = maybe_load_long()  # currently optional; kept for future extensions

    # Build total series
    total = wide.set_index("as_of_date")["total"].sort_index()

    # 1) Net weekly change (bars) + rolling trend
    plot_wow_bars(total, DATA_DIR / "dash_wow_bars.png", roll_w=ROLL_W)

    # 2) Cumulative change since anchor
    plot_cumulative_since(total, ANCHOR_DATE, DATA_DIR / "dash_cum_change_since_anchor.png")

    # 3) Composition (levels) last 2 years
    plot_composition_levels_last2y(wide, DATA_DIR / "dash_composition_levels_last2y.png", years=ZOOM_YEARS)

    # 4) Composition (share %) last 2 years
    plot_composition_share_last2y(wide, DATA_DIR / "dash_composition_share_last2y.png", years=ZOOM_YEARS)

    # 5) Total zoom last 2 years
    plot_total_zoom(total, DATA_DIR / "dash_total_last2y.png", years=ZOOM_YEARS)

    print("Wrote:")
    for f in [
        "dash_wow_bars.png",
        "dash_cum_change_since_anchor.png",
        "dash_composition_levels_last2y.png",
        "dash_composition_share_last2y.png",
        "dash_total_last2y.png",
    ]:
        print("  -", DATA_DIR / f)

if __name__ == "__main__":
    main()
