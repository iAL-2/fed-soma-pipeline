# sanity_check.py
import pandas as pd
p = "data/soma_summary_weekly.csv"
df = pd.read_csv(p, parse_dates=["as_of_date"])

# columns vary by endpoint; pick a value column that exists
VALUE_COLS = ["par_value","market_value","par","market"]
value_col = next((c for c in VALUE_COLS if c in df.columns), None)
assert value_col, f"None of {VALUE_COLS} found. Columns: {df.columns.tolist()}"

assert df["as_of_date"].is_monotonic_increasing, "Dates not sorted ascending."
assert len(df) > 0 and df[value_col].ge(0).all(), "Bad/negative values present."
print("OK:", p, "value_col:", value_col)
