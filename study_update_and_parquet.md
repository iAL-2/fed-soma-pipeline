```python
def url_builder(asof: date) -> str:
    return (
        "https://markets.newyorkfed.org/read"
        f"?productCode=30&query=summary"
        f"&startDt={asof.isoformat()}&endDt={asof.isoformat()}&format=csv"
    )
```

# known
- same format as the url_builder from the initial backfill. argument asof is passed the date when it is called.
- isoformat() is friendly for reading csv and json, turns the date into string("YYYY-MM-DD", which is the exact format the Fed's API expects)
- f strings with indents to make the url code look nice, as well as allow functions like isoformat

# unknown
- none



```python 
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
```

# known
- exact same format as backfill. only the dates will be changed since this is an update file
- if anything forgotten just refer to study_initial...

# unknown
- none


```python
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
```
# known
- this should be where it first diverges from the initial backfill.
- first checks the path with path.exists(). if it doesn't exist, return none, otherwise proceed
- reads the path, imports it to dataframe with pandas. if dataframe is empty with .empty, then return none
- somehow it will return the most recent date from the existing csv
- next_wednesday() will iterate until it finds the next wednesday. it will first add one day to make it thursday so it can loop properly. with date format and timedelta, days will loop to 6 then repeat starting at 0
- weekly_wednesday is same logic as before

# unknown
- what is usecols keywords in read_csv do?
- df["as_of_date"] = pd.to_datetime(df["as_of_date"]).dt.date
    return df["as_of_date"].max(), what is this line doing step by step?
- why bother with next_wednesday? shouldn't the end date in the csv file be a wednesday? why not just use weekly_wednesday?

# answers
- usecols tells pandas to read only that column. its a speed/memory optimization
df["as_of_date"] = pd.to_datetime(df["as_of_date"]).dt.date
return df["as_of_date"].max()
- pd.to_datetime() parses column values into pandas timestamp objects
- .dt.date then converts those timestamps to python date objects
- .max() returns the latest date in that column. conversion is necessary since if they are not in date time format it can be compared improperly. this is because when its read from the csv, it is initially in string form.
- (chatgpt extra note) The combination .dt.date (Python date objects) instead of keeping pandas Timestamps ensures the function can safely return a pure date type rather than a pandas object, which keeps type consistency with other helpers like next_wednesday.

```python
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
```

# known
- CSV_WIDE is a path defined earlier, so .exists() checks if it is there or not. if it doesn't exist, raise an error
- get the last date using last_asof_or_none defined earlier. it should return the last parsed date. since the function uses a specific column name, it can fail if the csv is missing the column, so guard against that with a raise runtimeerror check
- find the next target date, the next wednesday after the last date in the csv. assign that to the variable start, that's where the new data will start. the end date will be date.today() to get a completely up to date version
- since the start date is meant to be the wednesday after the last date, if it is up to date it will be in the future. we can use a comparison check to know it is up to date then. if it is, print a message for the user
- if not up to date, start compiling the url using the url_builder() function with the new start and end dates. this is exactly the same as before, start iterating through all the target dates, parse them into a panda dataframe, clean up the columns and add guards to make sure the data is in order
- finally, run the dedupe function again to clean it up

# unknown

# chatgpt extra notes
- `weekly_wednesdays(start, today)` yields all Wednesdays ≤ today, ensuring up-to-date coverage. If today is Thu–Sun and data not yet released, fetch fails safely via try/except.
- `next_wednesday(last)` ensures no duplicate pulls by jumping strictly after the last date, even if the CSV’s final entry wasn’t a Wednesday.
- `"as_of_date"` injection adds a string version of the date (`isoformat()`); normalization back to `date` happens later when reading.
- `df.rename(columns={c: c.strip() for c in df.columns})` trims whitespace in headers to prevent mismatched or broken column names.
- try/except block logs and skips missing weeks (e.g., holidays), keeping the loop robust.
- `dedupe_sort_wide_inplace()` removes duplicates and reorders chronologically, ensuring a clean, reliable master CSV after appending.



```python
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
```

# known
- okay so this is getting into territory im not familiar with, external engines/libraries
- the logic is simple though. first, identify the 2 engines you want to check for. then do a for loop to iterate through them. the first one in the iteration will be the 'default', and if it passes it will select the first one. otherwise check the second one. if theres an importerror, could be wrong versions or other problems, seems to be just a guardrail for checking engines. if none passes, return none for the next function
- now we get into refresh_wide_parquet(). the logic here is also simple, take the engine returned in the last function. if none was returned, add a guardrail to catch it. otherwise, read the csv into dataframe, taking only the dates. then use a pandas method to_parquet() to convert it, with the output being parq_wide, engine argument taking the selected engine. print a message for the user to the terminal
- refresh_long_parquet(). this will read from csv_long(which i dont think exists yet), import it to panda dataframe, then use to_parquet panda method to change the format

# unknown
- what is parse_dates? does this mean read_csv is only reading the date column?
- not sure if i've gone over .resolve() yet, but im sure its just a guard/check, but clarify it for me

# answers
- pd.read_csv(..., parse_dates=["as_of_date"]) does not read only the date column; it reads the whole CSV and parses that one column as datetime.
- parse_dates=["as_of_date"]: tells pandas to parse the as_of_date column into datetime64[ns] (Timestamp) dtype during load. It doesn’t limit columns. This ensures stable dtypes going into Parquet.
- .resolve() on a Path: returns the absolute, normalized path (resolves ./.. and symlinks). It’s just for a clear, user-friendly “where the file is” message.


```python
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
```

# known 
- as suspected, the long form of the csv is generated here
- this one reads the csv_wide, parse_dates keyword will turn the strings from the asofdate column into datetime64 format.
- iterate through the columns with [c for c in wide.colums if c != "as_of_date"]. 
- long = wide.melt() is obviously the conversion method. not sure where melt() comes from, probably python
- accepts the keyword arguments id_vars, value_vars, var_name, and value_name
- then write it back to csv with .to_csv, remove index, and check the location with .resolve()

# unknown
- is .columns only returning column name or all the data in that column as well?
- explain the wide.melt() in detail, and include an example table transformation. im having trouble understanding it
- why is it returning csv_long if the transformation to the file already happened?

# answers
- DataFrame.columns returns an Index of column labels (names), not the column data. Your list comprehension builds a list of names excluding "as_of_date"
- Conceptually, melt turns “wide” columns into rows, creating two new columns: one for the former column name (var_name) and one for the value from the cell (value_name). You keep key columns fixed via id_vars.

as_of_date | total | mbs | tips
-----------+-------+-----+------
2025-10-01 | 100   | 70  | 30
2025-10-08 | 110   | 75  | 35

long = wide.melt(
    id_vars=["as_of_date"],
    value_vars=["total","mbs","tips"],
    var_name="category",
    value_name="amount"
)

as_of_date | category | amount
-----------+----------+-------
2025-10-01 | total    | 100
2025-10-01 | mbs      | 70
2025-10-01 | tips     | 30
2025-10-08 | total    | 110
2025-10-08 | mbs      | 75
2025-10-08 | tips     | 35

- Why return CSV_LONG if the file is already written?

Returning the path is a convenience so callers can chain operations without re-deriving the location (e.g., path = make_long_from_wide(); do_something(path)). It also makes the function testable and composable in pipelines.