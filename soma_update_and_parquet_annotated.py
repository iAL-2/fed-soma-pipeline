from __future__ import annotations
from datetime import date, timedelta
from pathlib import Path
import io
import csv
import time
import requests
import pandas as pd

OUT_DIR = Path("data")
OUT_DIR.mkdir(parents=True, exist_ok=True)

CSV_WIDE = OUT_DIR / "soma_summary_weekly.csv"
PARQ_WIDE = OUT_DIR / "soma_summary_weekly.parquet"
CSV_LONG = OUT_DIR / "soma_summary_long.csv"
PARQ_LONG = OUT_DIR / "soma_summary_long.parquet"


def url_builder(asof: date) -> str:
    return (
        "https://markets.newyorkfed.org/read"
        f"?productCode=30&query=summary"
        f"&startDt={asof.isoformat()}&endDt={asof.isoformat()}&format=csv"
    )


def fetch_csv_df(url: str, timeout=60, retries=3, backoff=1.5) -> pd.DataFrame:
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


def append_csv(df: pd.DataFrame, path: Path):
    header = not path.exists()
    df.to_csv(path, mode="a", index=False, header=header, quoting=csv.QUOTE_MINIMAL)

def dedupe_sort_wide_inplace(path: Path):
    df = pd.read_csv(path, parse_dates=["as_of_date"])
    df = df.sort_values("as_of_date")
    df = df.drop_duplicates(subset=["as_of_date"])
    df.to_csv(path, index=False)


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
    while d.weekday() != 2: 
        d += timedelta(days=1)
    return d

def weekly_wednesdays(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=7)


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
            print(f"[skip] {asof}: {e}")
            continue

        if "as_of_date" not in df.columns:
            df["as_of_date"] = asof.isoformat()

        df = df.rename(columns={c: c.strip() for c in df.columns})

        append_csv(df, CSV_WIDE)

    dedupe_sort_wide_inplace(CSV_WIDE)
    print(f"[ok] CSV (wide) updated: {CSV_WIDE.resolve()}")


def _pick_parquet_engine():
    for eng in ("pyarrow", "fastparquet"):
        try:
            __import__(eng)
            return eng
        except ImportError:
            pass
    return None


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


def make_long_from_wide():
    wide = pd.read_csv(CSV_WIDE, parse_dates=["as_of_date"])
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

if __name__ == "__main__":
    update_wide_csv()
    refresh_wide_parquet()
    make_long_from_wide()
    refresh_long_parquet()
