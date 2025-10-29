import pandas as pd
import numpy as np


P_WIDE = "data/soma_summary_weekly.csv"  # table with many columns per date
P_LONG = "data/soma_summary_long.csv"    # table with 3 key columns: date, category, amount

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
    df = pd.read_csv(path, parse_dates=["as_of_date"]).sort_values("as_of_date")

    assert "as_of_date" in df.columns, "Missing as_of_date"
    assert "total" in df.columns, f"Expected 'total' column. Got: {df.columns.tolist()}"

    assert df["as_of_date"].is_monotonic_increasing, "Dates not sorted ascending (wide)"

    num_cols = [c for c in df.columns if c != "as_of_date"]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce")

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


def check_long(path):
    """
    Validate the 'long' CSV:
      - must contain columns: as_of_date, category, amount
      - dates sorted ascending
      - 'amount' is numeric
      - TOTAL category must not be negative
      - component categories may be negative → warn by category counts
    """
    df = pd.read_csv(path, parse_dates=["as_of_date"]).sort_values(["as_of_date","category"])

    required = {"as_of_date","category","amount"}
    assert required.issubset(df.columns), f"Missing columns in LONG. Need {required}"

    assert df["as_of_date"].is_monotonic_increasing, "Dates not sorted ascending (long)"

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    if df["amount"].isna().any():
        raise AssertionError("Non-numeric 'amount' values after coercion in LONG.")

    is_total = df["category"].str.lower().eq("total")
    if (df.loc[is_total, "amount"] < 0).any():
        rows = df.loc[is_total & (df["amount"] < 0), ["as_of_date","amount"]]
        raise AssertionError(f"LONG 'total' has negatives at:\n{rows.to_string(index=False)}")

    neg = df.loc[~is_total & (df["amount"] < 0)]
    if not neg.empty:
        by_cat = neg.groupby("category")["amount"].agg(["count","min"])
        print("[warn] LONG negatives by category (can be normal):")
        print(by_cat.sort_values("count", ascending=False).to_string())

    print(f"[OK] Long: rows={len(df)} categories={df['category'].nunique()}")


if __name__ == "__main__":
    # Run both checks when this file is executed directly.
    check_wide(P_WIDE)
    check_long(P_LONG)
