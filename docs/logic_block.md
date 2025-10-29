# Logic Block

**Goal**  
- [What the block/system should achieve (success condition).]
- Extract Fed SOMA holdings data from their official endpoint, clean up the data, and use it to draw conclusions about market movement
- Have clear and separated functions to allow ease of use as well as modularity
- Allow the data to update without reproducing the entire dataset since data range is decades long
- Have multiple charts in a dashboard with modifiable date ranges to get a clear view of the Fed holdings

**Inputs**  
- [What comes in: type(s), assumptions.]
- Fed SOMA data in CSV form(use the summary data, not detailed)
- 

**Outputs**  
- [Explicit form of result: type, format, conditions.]  
- Cleaned up CSV data in both wide and long formats. Also include .parquet versions for efficiency
- Dashboard using plotly and matlib to create visuals using the data
- Include week over week changes with rolling trend, cumulative change, category composition makeup levels, composition shares, as well as total holdings, for 5 sets of charts

**Constraints / Invariants**  
- [Rules that must always hold, e.g., type safety, performance, code constraints.]  
- The program should work as long as the endpoint for the Fed SOMA data doesn't change
- Automatically updates without having to regenerate the entire dataset, as the dataset is large
- When extracting dataset, must account for holidays as well as days where tahe mrket isn't open
- Use proper datetime formats at each stage of data type to ensure data integrity

**Intermediates**
- raw weekly CSV(s) from NY Fed
- csv, longform, and parquet forms
- pandas dataframes(in memory when executing)
- final html dashboard: `data/soma_dashboard.html`

**Rules (IF/THEN)**  
- [Decision logic in plain IF/THEN statements.]  
- IF no new weeks, THEN `soma_update_and_parquet_annotated.py` prints “No new weeks” and exits.
- IF schema mismatch on read, THEN fail fast (don’t write corrupted outputs).
- IF ZOOM_YEARS or ANCHOR_DATE change, THEN charts recompute but raw stays untouched.

**Flow**  
1. Get the CSV into a pandas dataframe, then normalize the columns and ensure the date is properly formatted. Drop duplicates and save the data into a .csv file in a separate data folder
2. Update: get the current .csv file's latest date, then clean and normalize to the same format, append onto the csv
3. Run sanity_check.py to check both the wide and long formats are sane
4. Build figures from the wide format: week over week changes with rolling trend, cumulative change, category composition makeup levels, composition shares, as well as total holdings
5. Assemble HTML with CDN plotly, stitch together the charts, write output to OUT_HTML

**Edge Cases**  
- Empty dataset after filtering by last_n_years: skip annotations, figures will render empty
- Non-numeric in numeric columns: coercion > NaN > fail and return the explicit column counts
- Duplicate dates: upstream cleaning should drop dupes
- ANCHOR_DATE outside of visible range: annotation helper should clip/hide via x_min/x_max
- Timezone: timestamp in header uses local machine time

**Tests / Checks**  
- Schema: {"as_of_date","total"} (wide), {"as_of_date","category","amount"} (long)
- Monotonic dates: df["as_of_date"].is_monotonic_increasing
- Numeric coercion: .apply(pd.to_numeric, errors="coerce") (wide) / to_numeric(amount) (long); assert no NaNs
- Totals non-negative: assert (total >= 0).all()
- Immutability check: hash or equals() before/after chart calls to ensure figures don’t mutate wide.
- Component tolerance (wide):
   - comps_sum = df[component_cols].sum(axis=1)
   - Tolerance: |comps_sum - total| <= atol + rtol*|total| with atol=1_000, rtol=0.005(up to $1000 and 0.5% tolerance)
   - Warn with off_count and worst |diff|.
