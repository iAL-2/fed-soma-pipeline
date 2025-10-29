```python
# =============================================================================
# sanity_check.py  —  BEGINNER-ANNOTATED VERSION
# -----------------------------------------------------------------------------
# Goal: Make sure your two CSV files ("wide" and "long" shapes) look sane.
# - "Wide" CSV: one row per as_of_date, with many numeric columns (buckets + total)
# - "Long" CSV: many rows per date, with columns: as_of_date, category, amount
#
# This script:
#   1) Opens each CSV
#   2) Checks basic assumptions (columns exist, dates sorted, numbers are numbers)
#   3) Disallows negative TOTAL but *allows* negative component buckets (warn only)
#   4) Optionally checks if sum(components) ≈ total within a small tolerance
#
# How to run:
#   python sanity_check.py
#
# Notes:
# - We intentionally keep "negative components" as warnings because some sources
#   have adjustments that go negative, which can be normal.
# - We fail (raise AssertionError) if TOTAL is negative or if key columns are missing.
# =============================================================================

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------
# File paths (change if your CSVs live elsewhere)
# ---------------------------------------------------------------------
P_WIDE = "data/soma_summary_weekly.csv"  # table with many columns per date
P_LONG = "data/soma_summary_long.csv"    # table with 3 key columns: date, category, amount

# ---------------------------------------------------------------------
# Checker for the WIDE file
# ---------------------------------------------------------------------
def check_wide(path):
    """
    Validate the 'wide' CSV:
      - has 'as_of_date' and 'total' columns
      - dates go from oldest to newest
      - all non-date columns are numeric
      - 'total' is never negative
      - component columns can be negative → print a warning if found
      - optional: sum(components) ≈ total (within a small tolerance)
    """
    # Read CSV; tell pandas to parse 'as_of_date' as a real date type.
    df = pd.read_csv(path, parse_dates=["as_of_date"]).sort_values("as_of_date")

    # Make sure important columns exist.
    assert "as_of_date" in df.columns, "Missing as_of_date"
    assert "total" in df.columns, f"Expected 'total' column. Got: {df.columns.tolist()}"

    # Check that dates are sorted ascending (older → newer).
    assert df["as_of_date"].is_monotonic_increasing, "Dates not sorted ascending (wide)"

    # We expect every non-date column to be numeric (floats/ints).
    # Convert them to numeric; if conversion fails, we'll get NaN → that's an error for us.
    num_cols = [c for c in df.columns if c != "as_of_date"]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce")

    # If any numeric column has NaNs after conversion, report which columns/rows are bad.
    if df[num_cols].isna().any().any():
        bad = {
            c: int(df[c].isna().sum())
            for c in num_cols if df[c].isna().any()
        }
        raise AssertionError(f"Non-numeric values after coercion: {bad}")

    # Rule: TOTAL must never be negative.
    if (df["total"] < 0).any():
        rows = df.loc[df["total"] < 0, ["as_of_date","total"]]
        raise AssertionError(f"'total' has negatives at:\n{rows.to_string(index=False)}")

    # Component columns = every numeric column except TOTAL.
    # These may be negative in the source data (normal for some adjustments).
    component_cols = [c for c in num_cols if c.lower() != "total"]
    neg_report = []
    for c in component_cols:
        nneg = int((df[c] < 0).sum())
        if nneg > 0:
            neg_min = df.loc[df[c] < 0, c].min()
            neg_report.append((c, nneg, neg_min))

    # Warn (do not fail) if any component has negatives.
    if neg_report:
        print("[warn] Negative component amounts detected (this can be normal):")
        for c, nneg, neg_min in neg_report:
            print(f"  - {c}: {nneg} rows (min={neg_min})")

    # Optional check: do the components approximately add up to TOTAL?
    # We allow a small absolute (atol) and relative (rtol) wiggle room.
    comps_sum = df[component_cols].sum(axis=1)
    atols = 1e3   # absolute tolerance (e.g., allow up to $1,000 mismatch)
    rtols = 5e-3  # relative tolerance (0.5%)
    diff = comps_sum - df["total"]
    off = ~np.isclose(comps_sum, df["total"], atol=atols, rtol=rtols)
    off_count = int(off.sum())
    if off_count > 0:
        worst = diff[off].abs().max()
        print(f"[warn] Component sum != total within tolerances "
              f"(atol={atols}, rtol={rtols}). Off rows: {off_count}, worst |diff|={worst}")

    print(f"[OK] Wide: rows={len(df)} cols={df.columns.tolist()}")
```

# known
- read the csv, parse the dates with pandas datetime64
- assert that the as_of_date and total are in the column list, include an error message if the assert fails
- assert that the dates are sorted with .is_monotonic_increasing. if i had to write the logic i would try something like .min() == df["as_of_date"][0]. include error message if assert fails
- apply numeric conversion to all the columns that are not dates. done with .apply(pd.to_numeric, errors="coerce")
- build a list if any of the columns have NaNs in them. dictionary will report which columns/rows are bad based on logic. then raise an assertionerror with the dictionary as part of the error message
- check if any of the rows in "total" are negative. if so, report which of the rows have negatives in them, with .loc to find the exact cells
- check every numeric column except total to find if any of the columns have negatives. then assemble a list to see which rows are negative. warn the user rather than raising an error since it could be possible that the negatives are normal
- compute each row so we can check whether or not they add up to the total. include an absolute and relative tolerance to make sure the information can have small wiggle room. we use the component_cols defined earlier, get the sum, then compare it to the total

# unknown
- break down the tolerance checking. if it was me i would just do exact check, i don't know alot of these new functions. ~np.isclose(), .abs()

# answers
- np.isclose(a, b, atol, rtol)
    - For each row, it returns True if:
        - |a - b| <= atol + rtol * |b|
    - This combo tolerates both:
        - tiny absolute differences when totals are small
        - slightly larger differences when totals are large
    - Why not exact? real world data often has rounding, late adjustments, or minor floating-point errors. exact == would flag lots of harmless rows
