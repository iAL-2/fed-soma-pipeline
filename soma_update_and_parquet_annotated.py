# soma_update_and_parquet_annotated.py
"""
PURPOSE
-------
Weekly maintenance for SOMA SUMMARY data (not CUSIP detail):
1) Append new weekly rows (as-of Wednesdays) to the master *wide* CSV.
2) Keep the wide CSV clean: sorted by as_of_date and deduped.
3) Refresh a *wide* Parquet copy (fast to load, compact on disk).
4) Produce a *long/tidy* CSV via melt (as_of_date, category, amount).
5) Refresh a *long* Parquet copy.

USAGE
-----
Run after your initial backfill has created `data/soma_summary_weekly.csv`:
    python soma_update_and_parquet_annotated.py

NOTES
-----
- We fetch ONE date (Wednesday) per request → robust and friendly to the server.
- “Wide” summary schema: one row per week; columns like:
    as_of_date, total, mbs, tips, frn, bills, agencies, cmbs, ...
- “Long/tidy” schema: one row per (as_of_date, category); columns:
    as_of_date, category, amount
- Keep this as a teaching copy; you can also maintain a lean “production” copy.
"""

from __future__ import annotations
from datetime import date, timedelta
from pathlib import Path
import io
import csv
import time
import requests
import pandas as pd

# ──────────────────────────────────────────────────────────────────────────────
# FILE LOCATIONS
# - All outputs go under ./data/
# - WIDE = master weekly summary (CSV + Parquet)
# - LONG = melted tidy table (CSV + Parquet)
# ──────────────────────────────────────────────────────────────────────────────
OUT_DIR = Path("data")
OUT_DIR.mkdir(parents=True, exist_ok=True)

CSV_WIDE = OUT_DIR / "soma_summary_weekly.csv"
PARQ_WIDE = OUT_DIR / "soma_summary_weekly.parquet"
CSV_LONG = OUT_DIR / "soma_summary_long.csv"
PARQ_LONG = OUT_DIR / "soma_summary_long.parquet"


# ──────────────────────────────────────────────────────────────────────────────
# ENDPOINT BUILDER
# - Edit this if you confirm a different working summary endpoint via DevTools.
# - We request exactly one as-of date (startDt=endDt) to avoid range caps.
# - format=csv so we can ingest directly with pandas.read_csv.
# ──────────────────────────────────────────────────────────────────────────────
def url_builder(asof: date) -> str:
    return (
        "https://markets.newyorkfed.org/read"
        f"?productCode=30&query=summary"
        f"&startDt={asof.isoformat()}&endDt={asof.isoformat()}&format=csv"
    )


# ──────────────────────────────────────────────────────────────────────────────
# FETCHING
# - Robust GET with small retry loop.
# - Returns a pandas DataFrame.
# - Raises on HTTP errors or empty/invalid CSV responses.
# ──────────────────────────────────────────────────────────────────────────────
def fetch_csv_df(url: str, timeout=60, retries=3, backoff=1.5) -> pd.DataFrame:
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()          # HTTP 4xx/5xx → error
            if not r.content:
                raise ValueError("Empty response body")
            df = pd.read_csv(io.BytesIO(r.content))
            if df.empty:
                raise ValueError("Empty CSV (no rows)")
            return df
        except Exception as e:
            last_err = e
            # Exponential backoff between retries: 1.5^attempt seconds
            if attempt < retries:
                time.sleep(backoff ** attempt)
            else:
                # After final attempt, surface the error
                raise last_err


# ──────────────────────────────────────────────────────────────────────────────
# CSV APPEND + HOUSEKEEPING
# - append_csv: appends a DataFrame to CSV, writing header if file is new.
# - dedupe_sort_wide_inplace: sort ascending by as_of_date and drop duplicate
#   weeks (idempotency; safe to re-run).
# ──────────────────────────────────────────────────────────────────────────────
def append_csv(df: pd.DataFrame, path: Path):
    header = not path.exists()
    df.to_csv(path, mode="a", index=False, header=header, quoting=csv.QUOTE_MINIMAL)

def dedupe_sort_wide_inplace(path: Path):
    df = pd.read_csv(path, parse_dates=["as_of_date"])
    # Ensure ascending chronology
    df = df.sort_values("as_of_date")
    # Drop duplicate weeks if we happen to re-fetch any
    df = df.drop_duplicates(subset=["as_of_date"])
    df.to_csv(path, index=False)


# ──────────────────────────────────────────────────────────────────────────────
# DATE HELPERS
# - last_asof_or_none: read the most recent as_of_date from existing CSV.
# - next_wednesday: returns the first Wednesday strictly AFTER the given date.
# - weekly_wednesdays: yield Wednesdays from start..end inclusive.
#   (Fed SOMA as-of date is typically Wednesday; data released Thu.)
# ──────────────────────────────────────────────────────────────────────────────
def last_asof_or_none(path: Path):
    if not path.exists():
        return None
    df = pd.read_csv(path, usecols=["as_of_date"])
    if df.empty:
        return None
    df["as_of_date"] = pd.to_datetime(df["as_of_date"]).dt.date
    return df["as_of_date"].max()

def next_wednesday(d: date) -> date:
    d = d + timedelta(days=1)
    while d.weekday() != 2:  # Monday=0, Tuesday=1, Wednesday=2
        d += timedelta(days=1)
    return d

def weekly_wednesdays(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=7)


# ──────────────────────────────────────────────────────────────────────────────
# UPDATE: WIDE CSV
# - Requires the initial backfill file to exist (we build on top of it).
# - Fetch each missing Wednesday from last_asof+1w up to today.
# - Append to wide CSV.
# - Sort + dedupe at the end for a clean master file.
# ──────────────────────────────────────────────────────────────────────────────
def update_wide_csv():
    if not CSV_WIDE.exists():
        raise FileNotFoundError(f"Missing {CSV_WIDE}. Run your initial backfill first.")

    last = last_asof_or_none(CSV_WIDE)
    if last is None:
        raise RuntimeError("CSV exists but contains no as_of_date values.")

    start = next_wednesday(last)
    today = date.today()

    if start > today:
        print("No new weeks to fetch.")
        return

    for asof in weekly_wednesdays(start, today):
        url = url_builder(asof)
        print(f"[fetch] {asof} -> {url}")
        try:
            df = fetch_csv_df(url)
        except Exception as e:
            # We log and continue (e.g., holiday/no release week)
            print(f"[skip] {asof}: {e}")
            continue

        # Many summary feeds already include as_of_date; but if not, we add it.
        if "as_of_date" not in df.columns:
            df["as_of_date"] = asof.isoformat()

        # Light normalization (optional): trim header whitespace
        df = df.rename(columns={c: c.strip() for c in df.columns})

        append_csv(df, CSV_WIDE)

    # Keep the master wide CSV tidy and chronological after appending
    dedupe_sort_wide_inplace(CSV_WIDE)
    print(f"[ok] CSV (wide) updated: {CSV_WIDE.resolve()}")


# ──────────────────────────────────────────────────────────────────────────────
# PARQUET ENGINES
# - Pandas can write Parquet using either 'pyarrow' or 'fastparquet'.
# - We detect whichever is installed to avoid forcing a specific dependency.
# ──────────────────────────────────────────────────────────────────────────────
def _pick_parquet_engine():
    for eng in ("pyarrow", "fastparquet"):
        try:
            __import__(eng)
            return eng
        except ImportError:
            pass
    return None


# ──────────────────────────────────────────────────────────────────────────────
# PARQUET REFRESHERS
# - Refresh both wide and long Parquet files (if engine available).
# - Parquet loads much faster than CSV and preserves dtypes better.
# ──────────────────────────────────────────────────────────────────────────────
def refresh_wide_parquet():
    eng = _pick_parquet_engine()
    if not eng:
        print("[warn] pyarrow/fastparquet not installed; skipping wide Parquet.")
        return
    df = pd.read_csv(CSV_WIDE, parse_dates=["as_of_date"])
    df.to_parquet(PARQ_WIDE, index=False, engine=eng)
    print(f"[ok] Parquet (wide) refreshed: {PARQ_WIDE.resolve()} (engine={eng})")

def refresh_long_parquet():
    eng = _pick_parquet_engine()
    if not eng:
        print("[warn] pyarrow/fastparquet not installed; skipping long Parquet.")
        return
    df = pd.read_csv(CSV_LONG, parse_dates=["as_of_date"])
    df.to_parquet(PARQ_LONG, index=False, engine=eng)
    print(f"[ok] Parquet (long) refreshed: {PARQ_LONG.resolve()} (engine={eng})")


# ──────────────────────────────────────────────────────────────────────────────
# WIDE → LONG (TIDY) CONVERSION
# - Wide has columns: as_of_date, total, mbs, tips, frn, bills, agencies, ...
# - Long has rows:    as_of_date, category, amount
# - Long format is “tidy” → flexible analysis/plotting (groupby/pivot easy).
# ──────────────────────────────────────────────────────────────────────────────
def make_long_from_wide():
    wide = pd.read_csv(CSV_WIDE, parse_dates=["as_of_date"])
    # All columns except the date are numeric categories in the summary feed
    value_cols = [c for c in wide.columns if c != "as_of_date"]
    long = wide.melt(
        id_vars=["as_of_date"],          # keep as key column
        value_vars=value_cols,           # melt all categories
        var_name="category",             # category name from column header
        value_name="amount"              # numeric value from cell
    )
    long.to_csv(CSV_LONG, index=False)
    print(f"[ok] CSV (long) written: {CSV_LONG.resolve()}")
    return CSV_LONG


# ──────────────────────────────────────────────────────────────────────────────
# ENTRYPOINT
# - Order matters:
#   1) Update WIDE CSV (append, sort, dedupe)
#   2) Refresh WIDE Parquet
#   3) Generate LONG CSV from WIDE (melt)
#   4) Refresh LONG Parquet
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    update_wide_csv()
    refresh_wide_parquet()
    make_long_from_wide()
    refresh_long_parquet()
