# soma_analyze.py
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

CSV_WIDE = Path("data/soma_summary_weekly.csv")
CSV_LONG = Path("data/soma_summary_long.csv")
OUT = Path("data")

def plot_from_wide():
    df = pd.read_csv(CSV_WIDE, parse_dates=["as_of_date"]).sort_values("as_of_date")
    if "total" not in df.columns:
        raise RuntimeError(f"'total' not found in {CSV_WIDE}. Columns: {df.columns.tolist()}")

    # Total level
    tot = df.set_index("as_of_date")["total"]
    tot.plot(title="SOMA Total Holdings (Weekly)")
    plt.tight_layout(); plt.savefig(OUT/"plot_total.png"); plt.close()

    # Week-over-week change
    wow = tot.diff()
    wow.plot(title="SOMA Total Holdings – Week-over-Week Change")
    plt.axhline(0)
    plt.tight_layout(); plt.savefig(OUT/"plot_wow.png"); plt.close()

    # Composition: all parts except total
    parts = [c for c in df.columns if c not in ("as_of_date","total")]
    if parts:
        comp = df.set_index("as_of_date")[parts]
        comp.plot.area(title="SOMA Composition by Category")
        plt.tight_layout(); plt.savefig(OUT/"plot_composition.png"); plt.close()

    print("Wrote plots from WIDE: plot_total.png, plot_wow.png, plot_composition.png")

def plot_from_long():
    df = pd.read_csv(CSV_LONG, parse_dates=["as_of_date"])
    # Separate total vs components
    is_total = df["category"].str.lower().eq("total")
    tot = (df[is_total]
           .set_index("as_of_date")["amount"]
           .sort_index())
    # Total level
    tot.plot(title="SOMA Total Holdings (Weekly)")
    plt.tight_layout(); plt.savefig(OUT/"plot_total.png"); plt.close()

    # WoW change
    wow = tot.diff()
    wow.plot(title="SOMA Total Holdings – Week-over-Week Change")
    plt.axhline(0)
    plt.tight_layout(); plt.savefig(OUT/"plot_wow.png"); plt.close()

    # Composition (exclude total)
    parts = df[~is_total]
    comp = (parts
            .pivot(index="as_of_date", columns="category", values="amount")
            .fillna(0)
            .sort_index())
    if not comp.empty:
        comp.plot.area(title="SOMA Composition by Category")
        plt.tight_layout(); plt.savefig(OUT/"plot_composition.png"); plt.close()

    print("Wrote plots from LONG: plot_total.png, plot_wow.png, plot_composition.png")

if __name__ == "__main__":
    if CSV_LONG.exists():
        plot_from_long()
    elif CSV_WIDE.exists():
        plot_from_wide()
    else:
        raise SystemExit("No data files found. Run the updater first.")
