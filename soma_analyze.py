# soma_analyze.py
import pandas as pd
import matplotlib.pyplot as plt

CSV = "data/soma_summary_weekly.csv"
df = pd.read_csv(CSV, parse_dates=["as_of_date"])

# choose available total column
VALUE_COLS = ["par_value","market_value","par","market"]
val = next((c for c in VALUE_COLS if c in df.columns), None)
if not val:
    raise RuntimeError(f"No value col among {VALUE_COLS}. Got: {df.columns.tolist()}")

# normalize column names likely present in summary feeds
# e.g., security_type / asset_class might differ; try a few
TYPE_COLS = ["security_type","asset_class","category","security_class"]
typ = next((c for c in TYPE_COLS if c in df.columns), None)

# TOTAL over time (momentum baseline)
tot = df.groupby("as_of_date")[val].sum().sort_index()

# Week-over-week change
wow = tot.diff()

# Plot 1: Total holdings (level)
tot.plot(title="SOMA Total Holdings (Weekly)")
plt.tight_layout(); plt.savefig("data/plot_total.png"); plt.close()

# Plot 2: Week-over-week change (momentum)
wow.plot(title="SOMA Holdings – Week-over-Week Change")
plt.axhline(0)
plt.tight_layout(); plt.savefig("data/plot_wow.png"); plt.close()

# Optional: composition over time (if a type column exists)
if typ:
    comp = df.groupby(["as_of_date", typ])[val].sum().unstack(fill_value=0).sort_index()
    # area stack shows shifting mix without picking colors/styles
    comp.plot.area(title="SOMA Composition by Security Type")
    plt.tight_layout(); plt.savefig("data/plot_composition.png"); plt.close()

print("Wrote: data/plot_total.png, data/plot_wow.png", "(+ data/plot_composition.png if available)")
