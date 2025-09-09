# sanity_check.py (wide + long, tolerant to negative component lines)
import pandas as pd
import numpy as np

P_WIDE = "data/soma_summary_weekly.csv"
P_LONG = "data/soma_summary_long.csv"

def check_wide(path):
    df = pd.read_csv(path, parse_dates=["as_of_date"]).sort_values("as_of_date")

    assert "as_of_date" in df.columns, "Missing as_of_date"
    assert "total" in df.columns, f"Expected 'total' column. Got: {df.columns.tolist()}"
    assert df["as_of_date"].is_monotonic_increasing, "Dates not sorted ascending (wide)"

    # Ensure numeric dtypes (coerce if necessary but do NOT silently drop NaNs)
    num_cols = [c for c in df.columns if c != "as_of_date"]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce")
    if df[num_cols].isna().any().any():
        bad = {
            c: int(df[c].isna().sum())
            for c in num_cols if df[c].isna().any()
        }
        raise AssertionError(f"Non-numeric values after coercion: {bad}")

    # 1) TOTAL must be non-negative
    if (df["total"] < 0).any():
        rows = df.loc[df["total"] < 0, ["as_of_date","total"]]
        raise AssertionError(f"'total' has negatives at:\n{rows.to_string(index=False)}")

    # 2) Component buckets can be negative—warn, don’t fail
    component_cols = [c for c in num_cols if c.lower() != "total"]
    neg_report = []
    for c in component_cols:
        nneg = int((df[c] < 0).sum())
        if nneg > 0:
            neg_min = df.loc[df[c] < 0, c].min()
            neg_report.append((c, nneg, neg_min))
    if neg_report:
        print("[warn] Negative component amounts detected (this can be normal):")
        for c, nneg, neg_min in neg_report:
            print(f"  - {c}: {nneg} rows (min={neg_min})")

    # 3) Optional reconciliation: sum(components) ≈ total (within tolerance)
    #    Some feeds include/exclude certain adjustments; allow slack.
    comps_sum = df[component_cols].sum(axis=1)
    # absolute and relative tolerances
    atols = 1e3  # adjust if your units are very large/small
    rtols = 5e-3 # 0.5% relative tolerance
    diff = comps_sum - df["total"]
    off = ~np.isclose(comps_sum, df["total"], atol=atols, rtol=rtols)
    off_count = int(off.sum())
    if off_count > 0:
        worst = diff[off].abs().max()
        print(f"[warn] Component sum != total within tolerances "
              f"(atol={atols}, rtol={rtols}). Off rows: {off_count}, worst |diff|={worst}")

    print(f"[OK] Wide: rows={len(df)} cols={df.columns.tolist()}")

def check_long(path):
    df = pd.read_csv(path, parse_dates=["as_of_date"]).sort_values(["as_of_date","category"])
    required = {"as_of_date","category","amount"}
    assert required.issubset(df.columns), f"Missing columns in LONG. Need {required}"
    assert df["as_of_date"].is_monotonic_increasing, "Dates not sorted ascending (long)"

    # Ensure numeric
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    if df["amount"].isna().any():
        raise AssertionError("Non-numeric 'amount' values after coercion in LONG.")

    # Allow negative amounts for some categories (e.g., tips_inflation_compensation)
    # But ensure TOTAL is non-negative:
    is_total = df["category"].str.lower().eq("total")
    if (df.loc[is_total, "amount"] < 0).any():
        rows = df.loc[is_total & (df["amount"] < 0), ["as_of_date","amount"]]
        raise AssertionError(f"LONG 'total' has negatives at:\n{rows.to_string(index=False)}")

    # Optional: warn on negative components
    neg = df.loc[~is_total & (df["amount"] < 0)]
    if not neg.empty:
        by_cat = neg.groupby("category")["amount"].agg(["count","min"])
        print("[warn] LONG negatives by category (can be normal):")
        print(by_cat.sort_values("count", ascending=False).to_string())

    print(f"[OK] Long: rows={len(df)} categories={df['category'].nunique()}")

if __name__ == "__main__":
    check_wide(P_WIDE)
    check_long(P_LONG)
