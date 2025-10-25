# =============================================================================
# FED SOMA WEEKLY SUMMARY BACKFILL (BEGINNER-ANNOTATED VERSION)
# -----------------------------------------------------------------------------
# What this script does:
# 1) Builds a URL to the New York Fed "markets" site for a given as-of date.
# 2) Downloads the SOMA "summary" as CSV for one date per week (usually Wed).
# 3) Normalizes the column names and adds an "as_of_date" column.
# 4) Appends each week's data into data/soma_summary_weekly.csv (creating it if
#    it doesn't exist), then de-duplicates by as_of_date.
# 5) At the end, it also sorts/deduplicates to keep the CSV clean.
#
# How to run:
#   python soma_weekly_summary_fetch.py
#
# Notes for beginners:
# - A "DataFrame" is just a table (from pandas).
# - "as_of_date" means "the date the holdings are reported for."
# - If a week has no data (HTTP error or empty CSV), we skip it and keep going.
# =============================================================================

from __future__ import annotations
from datetime import date, timedelta
from pathlib import Path
import time
import io
import csv
import requests
import pandas as pd

# -----------------------------------------------------------------------------
# OUTPUT LOCATIONS
# -----------------------------------------------------------------------------
# OUT_DIR is the folder where we'll save our CSV. If it doesn't exist, make it.
OUT_DIR = Path("data")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Final weekly summary CSV will live here:
OUT_CSV = OUT_DIR / "soma_summary_weekly.csv"

# -----------------------------------------------------------------------------
# 1) URL BUILDER
# -----------------------------------------------------------------------------
# We define ONE function that, given an as-of date, returns the exact URL we
# need to call. The "read" pattern below is typical of the NY Fed export tool.
def url_builder(asof: date) -> str:
    """
    Build the CSV download URL for a single as-of date.

    asof: a datetime.date (e.g., date(2025, 1, 8))
    returns: a URL string pointing to a CSV for that exact date window
    """
    # IMPORTANT: This pattern is based on the Fed "read" endpoint. If your
    # DevTools → Network tab shows different query parameters, adjust them here.
    # We request format=csv so we can parse it easily.
    return (
        "https://markets.newyorkfed.org/read"
        f"?productCode=30"             # productCode may vary by dataset
        f"&query=summary"              # 'summary' indicates we want the summary table
        f"&startDt={asof.isoformat()}" # start date = the as-of date
        f"&endDt={asof.isoformat()}"   # end date   = same as start (one-day window)
        f"&format=csv"                 # ask for CSV instead of JSON/XML
    )

# If your DevTools confirms a different endpoint works on your machine, you can
# replace the above with the alternate "api" style below (commented out):
# def url_builder(asof: date) -> str:
#     return (
#         "https://markets.newyorkfed.org/api/soma/non-mbs/get/all/"
#         f"asof/{asof.isoformat()}.csv"
#     )

# -----------------------------------------------------------------------------
# 2) DATE GENERATOR (ONE DATE PER WEEK)
# -----------------------------------------------------------------------------
def weekly_dates(start: date, end: date, weekday: int = 2):
    """
    Generate one date per week between 'start' and 'end' that falls on 'weekday'.

    weekday uses Python's convention: Monday=0 ... Sunday=6.
    The SOMA "as of" is commonly a Wednesday → weekday=2 by default.

    Example:
      for d in weekly_dates(date(2025,1,1), date(2025,2,1), weekday=2):
          print(d)  # prints all Wednesdays in that period
    """
    # Start from 'start' and move forward until we land on the chosen weekday.
    d = start
    while d.weekday() != weekday:
        d += timedelta(days=1)

    # Then yield one date per week until we pass 'end'.
    while d <= end:
        yield d
        d += timedelta(days=7)

# -----------------------------------------------------------------------------
# 3) FETCH A CSV → DATAFRAME (WITH RETRIES)
# -----------------------------------------------------------------------------
def fetch_csv_df(url: str, timeout=60, retries=3, backoff=1.5) -> pd.DataFrame:
    """
    Download the CSV at 'url' and return it as a pandas DataFrame.

    - timeout: how many seconds to wait for a response before giving up.
    - retries: how many attempts to try before failing.
    - backoff: how much to increase the wait between retries (exponential).

    Raises:
      - requests.HTTPError for HTTP issues
      - ValueError if the body is empty or parses to an empty table
    """
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            # Make the HTTP GET request.
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()  # Turn 4xx/5xx into Python exceptions.

            # Ensure we actually got a body.
            if not r.content:
                raise ValueError("Empty response body")

            # Parse CSV bytes into a DataFrame (BytesIO avoids encoding confusion).
            df = pd.read_csv(io.BytesIO(r.content))

            # Some "successful" CSVs can still be empty — treat that as an error.
            if df.empty:
                raise ValueError("Empty CSV (no rows)")

            return df  # Success! Return the table.
        except Exception as e:
            last_err = e
            if attempt < retries:
                # Wait a bit longer each attempt: backoff^attempt seconds.
                time.sleep(backoff ** attempt)
            else:
                # After final attempt, re-raise the last error.
                raise last_err

# -----------------------------------------------------------------------------
# 4) LIGHT DATA CLEANUP / NORMALIZATION
# -----------------------------------------------------------------------------
def normalize_summary(df: pd.DataFrame, asof: date) -> pd.DataFrame:
    """
    Make column names lowercase_with_underscores and add an 'as_of_date' column.

    Why normalize?
    - Consistent column names make downstream code simpler and less brittle.
    - Storing the as-of date inside the table makes it easy to filter/layer data.
    """
    # Convert "Column Name" → "column_name"
    rename = {c: c.strip().lower().replace(" ", "_") for c in df.columns}
    df = df.rename(columns=rename)

    # Add an explicit as_of_date column (ISO string is compact and unambiguous).
    df["as_of_date"] = asof.isoformat()
    return df

# -----------------------------------------------------------------------------
# 5) APPEND TO OUR MASTER CSV
# -----------------------------------------------------------------------------
def append_csv(df: pd.DataFrame, path: Path):
    """
    Append 'df' to the CSV at 'path'.
    - If the file doesn't exist yet, write the header.
    - If it does, just append rows.
    """
    header = not path.exists()
    df.to_csv(path, mode="a", index=False, header=header, quoting=csv.QUOTE_MINIMAL)

# -----------------------------------------------------------------------------
# 6) DEDUPE THE CSV IN-PLACE
# -----------------------------------------------------------------------------
def dedupe_csv_inplace(path: Path, keys=("as_of_date",)):
    """
    Load CSV at 'path', remove duplicate rows based on 'keys', and overwrite it.

    Default key is 'as_of_date' because we only want one row-set per as-of week.
    If your CSV is per-asset or per-bucket, you can expand 'keys' to include
    more columns to define "uniqueness."
    """
    df = pd.read_csv(path)
    df = df.drop_duplicates(subset=[k for k in keys if k in df.columns])
    df.to_csv(path, index=False)

# -----------------------------------------------------------------------------
# 7) MAIN BACKFILL DRIVER
# -----------------------------------------------------------------------------
def backfill_weekly_summaries(start: date, end: date):
    """
    For each "as-of" date (one per week between start and end):
      - Build the URL
      - Fetch the CSV into a DataFrame
      - Normalize it (columns + as_of_date)
      - Append to our master CSV

    If a given week fails (e.g., 404 or empty), we log and continue,
    so one bad week doesn't stop the whole backfill.
    """
    for asof in weekly_dates(start, end, weekday=2):  # weekday=2 → Wednesday
        u = url_builder(asof)
        print(f"[fetch] {asof} -> {u}")
        try:
            df = fetch_csv_df(u)
        except Exception as e:
            print(f"[skip] {asof}: {e}")
            continue  # Skip this week and move on.

        df = normalize_summary(df, asof)
        append_csv(df, OUT_CSV)

    # After we finish all weeks, remove any duplicates just to be safe.
    dedupe_csv_inplace(OUT_CSV, keys=("as_of_date",))

# -----------------------------------------------------------------------------
# 8) RUN THE BACKFILL (only when you execute this file directly)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Example: backfill from Jan 1, 2025 through today.
    # You can change the start date if you want more history.
    backfill_weekly_summaries(date(2025, 1, 1), date.today())
    print(f"Done. Output: {OUT_CSV.resolve()}")

    # -------------------------------------------------------------------------
    # Optional cleanup pass:
    # Read the CSV we just built, parse as_of_date as real dates, sort, drop dups,
    # and write it back out. This keeps the file tidy for downstream analysis.
    # -------------------------------------------------------------------------
    path = OUT_CSV  # "data/soma_summary_weekly.csv"
    df = pd.read_csv(path, parse_dates=["as_of_date"])

    # Sort so earliest weeks appear first (helps with plotting time series).
    df = df.sort_values("as_of_date")

    # If somehow duplicates snuck in, drop them again to be sure.
    df = df.drop_duplicates(subset=["as_of_date"])

    # Save back over the same file.
    df.to_csv(path, index=False)

    print(f"Cleaned and sorted: {len(df)} rows saved back to {path}")
