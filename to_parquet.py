# to_parquet.py
import pandas as pd
df = pd.read_csv("data/soma_summary_weekly.csv", parse_dates=["as_of_date"])
df.to_parquet("data/soma_summary_weekly.parquet", index=False)
print("Parquet ready.")
