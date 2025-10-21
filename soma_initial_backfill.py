# soma_weekly_summary_fetch.py
from __future__ import annotations
from datetime import date, timedelta
from pathlib import Path
import time
import io
import csv
import requests
import pandas as pd

OUT_DIR = Path("data")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV = OUT_DIR / "soma_summary_weekly.csv"

# ──────────────────────────────────────────────────────────────────────────────
# 1) PICK YOUR URL PATTERN (edit exactly one of these url builders)
#    Use the pattern you see working in your browser DevTools.
#    A) "read" style (Export Builder style) – summary for an as-of date:
def url_builder(asof: date) -> str:
    # Adjust fields/params as needed based on the request you capture.
    # Typically you’ll see query/fields names in DevTools → Network.
    # format can be csv | json | xml (csv is easiest here).
    return (
        "https://markets.newyorkfed.org/read"
        f"?productCode=30"
        f"&query=summary"
        f"&startDt={asof.isoformat()}"
        f"&endDt={asof.isoformat()}"
        f"&format=csv"
    )

#    B) Alternate “api” style (use only if you confirm a working path on your end)
# def url_builder(asof: date) -> str:
#     # Example: non-MBS/summary endpoints sometimes expose as-of paths.
#     # Replace with the exact, working endpoint you verify.
#     return (
#         "https://markets.newyorkfed.org/api/soma/non-mbs/get/all/"
#         f"asof/{asof.isoformat()}.csv"
#     )
# ──────────────────────────────────────────────────────────────────────────────

def weekly_dates(start: date, end: date, weekday: int = 2):
    """
    Generate 1 date per week between start and end on 'weekday'.
    weekday: Mon=0 ... Sun=6; Fed SOMA as-of is usually Wednesday (2).
    """
    d = start
    while d.weekday() != weekday:
        d += timedelta(days=1)
    while d <= end:
        yield d
        d += timedelta(days=7)

def fetch_csv_df(url: str, timeout=60, retries=3, backoff=1.5) -> pd.DataFrame:
    """
    GET a CSV into a DataFrame with basic retry.
    Raises on HTTP errors or empty content.
    """
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            if not r.content:
                raise ValueError("Empty response body")
            # Some endpoints may send text/csv; read robustly from bytes.
            df = pd.read_csv(io.BytesIO(r.content))
            if df.empty:
                raise ValueError("Empty CSV (no rows)")
            return df
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(backoff ** attempt)
            else:
                raise last_err

def normalize_summary(df: pd.DataFrame, asof: date) -> pd.DataFrame:
    """
    Light normalization:
    - lower_snake_case columns
    - add as_of_date column
    """
    rename = {c: c.strip().lower().replace(" ", "_") for c in df.columns}
    df = df.rename(columns=rename)
    df["as_of_date"] = asof.isoformat()
    return df

def append_csv(df: pd.DataFrame, path: Path):
    """Append to CSV (write header if file doesn’t exist)."""
    header = not path.exists()
    df.to_csv(path, mode="a", index=False, header=header, quoting=csv.QUOTE_MINIMAL)

def dedupe_csv_inplace(path: Path, keys=("as_of_date",)):
    """Load, drop duplicates by keys, and overwrite."""
    df = pd.read_csv(path)
    df = df.drop_duplicates(subset=[k for k in keys if k in df.columns])
    df.to_csv(path, index=False)

def backfill_weekly_summaries(start: date, end: date):
    """
    Core routine:
    - For each weekly as-of date, fetch summary CSV
    - Normalize, append
    - Skip dates that 404/empty with a console note
    """
    for asof in weekly_dates(start, end, weekday=2):
        u = url_builder(asof)
        print(f"[fetch] {asof} -> {u}")
        try:
            df = fetch_csv_df(u)
        except Exception as e:
            print(f"[skip] {asof}: {e}")
            continue
        df = normalize_summary(df, asof)
        append_csv(df, OUT_CSV)
    # Deduplicate once at the end (safe even if fetched unique rows):
    dedupe_csv_inplace(OUT_CSV, keys=("as_of_date",))

if __name__ == "__main__":
    # EXAMPLE: backfill 2024-01-01 to today
    backfill_weekly_summaries(date(2007, 1, 1), date.today())
    print(f"Done. Output: {OUT_CSV.resolve()}")

import pandas as pd

path = "data/soma_summary_weekly.csv"

df = pd.read_csv(path, parse_dates=["as_of_date"])
df = df.sort_values("as_of_date")        # put earliest first
df = df.drop_duplicates(subset=["as_of_date"])  # remove dup weeks if any
df.to_csv(path, index=False)

print(f"Cleaned and sorted: {len(df)} rows saved back to {path}")
