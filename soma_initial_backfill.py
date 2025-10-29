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

def url_builder(asof: date) -> str:
    """
    Build the CSV download URL for a single as-of date.

    asof: a datetime.date (e.g., date(2025, 1, 8))
    returns: a URL string pointing to a CSV for that exact date window
    """

    return (
        "https://markets.newyorkfed.org/read"
        f"?productCode=30"             
        f"&query=summary"              
        f"&startDt={asof.isoformat()}" 
        f"&endDt={asof.isoformat()}"  
        f"&format=csv"                 
    )

def weekly_dates(start: date, end: date, weekday: int = 2):
    """
    Generate one date per week between 'start' and 'end' that falls on 'weekday'.

    weekday uses Python's convention: Monday=0 ... Sunday=6.
    The SOMA "as of" is commonly a Wednesday → weekday=2 by default.

    Example:
      for d in weekly_dates(date(2025,1,1), date(2025,2,1), weekday=2):
          print(d)  # prints all Wednesdays in that period
    """
    d = start
    while d.weekday() != weekday:
        d += timedelta(days=1)

    while d <= end:
        yield d
        d += timedelta(days=7)


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
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()  

            if not r.content:
                raise ValueError("Empty response body")

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
    Make column names lowercase_with_underscores and add an 'as_of_date' column.

    Why normalize?
    - Consistent column names make downstream code simpler and less brittle.
    - Storing the as-of date inside the table makes it easy to filter/layer data.
    """
    rename = {c: c.strip().lower().replace(" ", "_") for c in df.columns}
    df = df.rename(columns=rename)

    df["as_of_date"] = asof.isoformat()
    return df


def append_csv(df: pd.DataFrame, path: Path):
    """
    Append 'df' to the CSV at 'path'.
    - If the file doesn't exist yet, write the header.
    - If it does, just append rows.
    """
    header = not path.exists()
    df.to_csv(path, mode="a", index=False, header=header, quoting=csv.QUOTE_MINIMAL)


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

    dedupe_csv_inplace(OUT_CSV, keys=("as_of_date",))


if __name__ == "__main__":
    backfill_weekly_summaries(date(2025, 1, 1), date.today())
    print(f"Done. Output: {OUT_CSV.resolve()}")

    path = OUT_CSV  
    df = pd.read_csv(path, parse_dates=["as_of_date"])

    df = df.sort_values("as_of_date")

    df = df.drop_duplicates(subset=["as_of_date"])
    
    df.to_csv(path, index=False)

    print(f"Cleaned and sorted: {len(df)} rows saved back to {path}")
