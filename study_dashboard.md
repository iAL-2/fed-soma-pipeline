```python
# --------- CONFIG (easy things you may change) ---------
DATA_DIR = Path("data")                               # where CSV lives and HTML will be written
WIDE_CSV = DATA_DIR / "soma_summary_weekly.csv"       # input CSV (wide format)
OUT_HTML = DATA_DIR / "soma_dashboard.html"           # output HTML dashboard

ANCHOR_DATE = pd.Timestamp("2017-06-01")  # baseline date for "cumulative" and vertical line
ROLL_W = 4                                # rolling window (in weeks) to smooth weekly change
ZOOM_YEARS = 5                            # only show the most recent N years in some charts
# ------------------------------------------------------
```

# known
- starting from the config section, we have the location of the files, which is the csv wide format as well as the dashboard file location
- settings for the different charts we will be making, these are adjustable levers

# unknown
- none


```python
def load_wide() -> pd.DataFrame:
    """
    Read the weekly CSV, ensure dates are real dates, sort by date,
    and convert all non-date columns to numbers (fill blanks with 0).
    We also enforce that a 'total' column must exist.
    """
    df = pd.read_csv(WIDE_CSV, parse_dates=["as_of_date"]).sort_values("as_of_date")
    value_cols = [c for c in df.columns if c != "as_of_date"]
    # Convert every value column to numeric; if something is not numeric, make it 0 instead of NaN
    df[value_cols] = df[value_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    if "total" not in df.columns:
        raise RuntimeError(f"'total' column not found. Columns: {df.columns.tolist()}")
    return df
```
# known
- this reads the wide csv with .read_csv() and assigns it a dataframe, after sorting by the as_of_date
- get the column names with df.columns that are not "as_of_date", assigning them value_cols
- raise a runtimeerror if a specific column name "total" is not found, returning to user a list of the found columns instead

# unknown 
- df[value_cols] = df[value_cols].apply(pd.to_numeric, errors="coerce").fillna(0). not sure what this line is doing in specific. df[value_cols] is a collection lookup. since value_cols was our extracted column names excluding "as_of"date", what returns should be...what exactly? the value of 'key' column name is... a list of the values of that column? not too sure what the format of the data is
- not sure what .apply(), .to_numeric, errors="coerce", and .fillna(0) is. 

# answers
- df[value_cols] selects and results in a smaller dataframe containing only those numeric columns(similar to a table. not a list of dict)
- .apply(func) tries to apply the funciton column by column
- pd.to_numeric is a panda method to try and convert values to integer or float
- errors = "coerce" will generate a NaN if the value cannot be converted. this combination will ensure that the numeric conversion will catch everything even if the csv had stray text.
- .fillna(0) will replace all NaN values made in the coercion step with 0. so any bad or blank cell becomes a 0 instead of a missing value
- after conversion and cleaning, the sanitized dataframe is written back into the same slice of the original dataframe with assignment
- in conclusion, read the CSV, parse the dates into datetime64, sort the dates, then exclude dates and convert and clean the rest of the data into numbers so we can ensure proper processing for making charts and graphs. since the nature of the data is numbers aside from the dates, this process, numeric coercion, fits perfectly once we write logic to exclude the date

```python
def dollars_axis_layout(fig: go.Figure, trillions=False):
    """
    Make the y-axis show dollars with commas. If 'trillions' is True, show T units.
    Example: $1,234 or $1.2T
    """
    fig.update_yaxes(tickformat="$,.1fT" if trillions else "$,.0f")
```

# known
- first plotly function. how do i know it's plotly? because earlier we had 'import plotly.graph_objects as go'. now we have go.Figure. it accepts go.Figure arguments, and defaults trillions=False

# unknown
- what is fig.update_yaxes()? why is it yaxes and not yaxis()? judging from the wording it changes the structure of the y-axis, in this case with the keyword tickformat=. do an example of before and after here to show what this function is doing

# answers
- axes is the plural of axis so it will update all y-axes in the figure at once. it modifies the interal axis layout dictionary, in this case the tick label formatting
- tickformat is a formatting string that tells Plotly how to display numeric tick labels.
- "$,.0f" means
    $ prefix
    , = use thousands separator
    .0f = fixed-point, zero decimal places
    - > eg 1234567 -> $1,234,567
- so this function is just a neat helper to apply human-friendly dollar formatting across all charts with one line

example

-> dollars_axis_layout()
Y-axis tick labels:
1000000000, 2000000000, 3000000000

-> dollars_axis_layout(fig)
Y-axis tick labels:
$1,000,000,000
$2,000,000,000
$3,000,000,000

-> dollars_axis_layout(fig, trillions=True)
Y-axis tick labels:
$1.0T
$2.0T
$3.0T


```python
def add_ranges(fig: go.Figure):
    """
    Add quick date buttons and a draggable date range slider to the x-axis.
    Buttons: last 6 months, 1 year, 2 years, or All.
    """
    fig.update_xaxes(
        rangeselector=dict(
            buttons=list([
                dict(count=6,  label="6M", step="month", stepmode="backward"),
                dict(count=1,  label="1Y", step="year",  stepmode="backward"),
                dict(count=2,  label="2Y", step="year",  stepmode="backward"),
                dict(step="all", label="All"),
            ])
        ),
        rangeslider=dict(visible=True),
        type="date"
    )
```
# known
- another function to edit a plotly figure. it accepts a figure as an argument
- we use dictionaries and lists to make a tree of data. its rather confusing but its just key:value over and over again. since dictionaries can fit lists, each key can have multiple values. in buttons= case, there are 4 'buttons' with different values. but since those values also have values, its... a list of dictionaries inside of a dictionary. 

# unknown
- breakdown the keyword arguments. its using plotly's update_xaxes(). rangeselctor, buttons, rangeslider, and type

# answers
- correct on the structure, its using nested dicts/lists for defining configuation for plotly's x-axis controls
- rangeselector adds a set of zoom buttons above the plot, each button defines one quick range button, which are defined with a dictionary
- rangeslider adds a small draggable slider bar, allowing user to manually zoom and pan through the time range
- type="date" tells plotly to treat the x-axis as date/time data

```python
def last_n_years(df: pd.DataFrame, years: int) -> pd.DataFrame:
    """
    Keep only the rows where as_of_date is within the last 'years' years.
    Useful to avoid drawing extremely long histories in some charts.
    """
    if df.empty:
        return df
    cutoff = df["as_of_date"].max() - pd.DateOffset(years=years)
    return df[df["as_of_date"] >= cutoff]
```
# known
- writes a logic to have a sane date range. accepts a dataframe and a years argument. extrapolates the maximum date in the dataframe with .max(), then subtracts it with pd.DateOffset()
- the dataframe should already have the date in datetime64 at this point since it was parsed earlier(if not must make sure because it is not parsed in this function)
- dateoffset() should be similar to timedelta() but for dates

# unknown
- not sure what it is trying to return here. its a math expression with >= inside of a dict? is it a range or is it a single date slice

# answers
- return df[df["as_of_date"] >= cutoff] is a dataframe filter, not a dictionary or math expression
    - Inside the brackets, df["as_of_date"] >= cutoff creates a Boolean Series — a list of True/False values for every row, depending on whether that row’s date is newer than or equal to the cutoff.
    Example:
    as_of_date       >= cutoff?  
    2020-01-01       False  
    2021-05-01       True  
    2023-09-01       True  
    - df[...] then selects only the rows where the condition is True. That’s how pandas does conditional filtering.
- so this function returns a new, filtered dataframe, containing only the rows within the specified years of data


```python
def _to_py_dt(x):
    """
    Convert different timestamp types (pandas/NumPy/string) into a plain Python datetime.
    This makes Plotly's annotation API happier.
    """
    from datetime import datetime as _dt
    if hasattr(x, "to_pydatetime"):
        return x.to_pydatetime()
    if isinstance(x, pd.Timestamp):
        return x.to_pydatetime()
    if isinstance(x, _dt):
        return x
    return pd.to_datetime(x).to_pydatetime()
```

# known
- judging by the annotation, this small function just converts the different time types into pure python datetime.
- it does this with several if statements. if it catches that the thing it is trying to process, (x), is in the incorrect format, then it will return a function with the correct logic to convert it. 

# unknown
- the logic all makes sense, just unfamiliar with the different types. string is from csv, datetime64 is from pandas, while pydatetime is python datetime. not sure where numpy comes in though. break down which type of data each line is trying to catch

# answers
- if hasattr(x, "to_pydatetime"):
    This covers NumPy datetime64 and pandas Timestamp objects, both of which implement .to_pydatetime() to return a datetime.datetime.
        It’s the most general check — if the attribute exists, just call it.

- if isinstance(x, pd.Timestamp):
    Explicitly handles pandas Timestamp objects (redundant after the first check, but added for safety or clarity).
        These are what you get when you parse dates with pandas (parse_dates).

- if isinstance(x, _dt):
    _dt is datetime.datetime.
        So if the object is already a pure Python datetime, return it unchanged.

- return pd.to_datetime(x).to_pydatetime()
    Catch-all fallback: handles strings ("2024-10-28") or other time-like inputs.
        pd.to_datetime() converts the string (or other type) into a Timestamp, then .to_pydatetime() converts that to a Python datetime.

- Where NumPy fits in:
    NumPy’s datetime64 objects (common inside arrays or Series) support .to_pydatetime() as well, which is why the first check works for them.

```python
def qt_annotation(fig: go.Figure, anchor, text="QT start", x_min=None, x_max=None):
    """
    Draw a thin vertical dotted line at 'anchor' (e.g., QT start),
    but only if that date is within the current data range [x_min, x_max].
    Also add a small label at the top of the plot.
    """
    try:
        x = _to_py_dt(anchor)
    except Exception:
        return  # if we can't parse the date, silently skip

    if x_min is not None and x < _to_py_dt(x_min):
        return
    if x_max is not None and x > _to_py_dt(x_max):
        return

    fig.add_vline(x=x, line_width=1, line_dash="dot", line_color="gray")
    fig.add_annotation(
        x=x, y=1.0, xref="x", yref="paper",      # yref="paper" pins it to top of the plotting area
        text=text, showarrow=False,
        xanchor="left", yanchor="bottom",
        bgcolor="rgba(255,255,255,0.6)", bordercolor="gray", borderwidth=1
    )
```

# known
- starting to get into the graph creation so this is mostly new, but let's break down the syntax
    - accepts arguments fig and anchor. fig is in plotly figure object form, anchor is a date
    - text, x_min, and x_max have defaults set in, but are modifiable
- try to parse the date with the previously written conversion function. if it doesn't work it will skip

# unknown
- not sure what the x_min and x_max if statements are trying to catch. i think it's impossible to know at this point since the rest of the logic hasn't been seen yet. but if somehow the if statement catch, then function returns, which probably means failure
- no idea about any of the plotly functions

# answer
- x_min and x_max are guards
    - these prevent adding the line if the anchor dates lie outside of the visible/relevant range of data
- fig.add_vline()
    - adds a vertical line at specific x coordinate
    - key arguments
        - line_wdith=1 > thin line
        - line_dash="dot" > dotted pattern
        - line_color="gray" > color
- fig.add_annotation()
    - adds text or labels on the plot
    - x=x, y=1.0 > places the label at the same x-position as the line, near the top
    - xref="x" means x is in data coordinates(time axis)
    - yref="paper" means y is relative to the full figure’s height (so y=1.0 sticks to the top edge regardless of scale).
    - showarrow=False > removes pointer arrows
    - xanchor, yanchor control text alignment relative to that point.
    - The bgcolor, bordercolor, and borderwidth style the label box.
- in summary
    - checks whether the anchor date is inside the chart's range
    - if so, draws a thin gray dotted vertical line at that date
    - adds a small labed box at the top(eg "QT start")

```python
def fig_to_section(fig: go.Figure, title: str) -> str:
    """
    Convert a Plotly figure into a chunk of HTML we can stitch into our single page.
    We include a <h2> title above each figure for clarity.
    """
    return f"""
<section style="margin: 20px 0;">
  <h2 style="font-family: system-ui, -apple-system, Segoe UI, Roboto; margin: 8px 0 0 6px;">
    {title}
  </h2>
  {pio.to_html(fig, full_html=False, include_plotlyjs=False)}
</section>
"""
```

# known
- looks like just html/frontend code
- accepts a plotly figure as well as a title argument, probably to label the figure
- main function is the plot io .to_html
    - accepts arguments fig, while having defaults for full_html and include_plotlyjs

# unknown
- basically all of the html form, i never learned it. but i can glance and understand it's talking about styling and fonts

# answer
- pio.to_html(fig, full_html=False, include_plotlyjs=False) turns the Plotly figure into an embeddable HTML fragment without creating a full standalone page (the script that calls this will probably assemble several sections into one big dashboard).
- the rest is indeed frontend decoration

```python
def fig_weekly_change(df: pd.DataFrame) -> go.Figure:
    """
    Chart 1: Weekly change bars + rolling average line.
    - We take the 'total' series and compute the week-over-week difference (diff).
    - Then we compute a rolling mean of that diff to make a smoother trend line.
    """
    s = df.set_index("as_of_date")["total"].sort_index()
    wow = s.diff()                                # week-over-week change (this week - last week)
    wow_roll = wow.rolling(ROLL_W, min_periods=1).mean()  # smooth line over ROLL_W weeks

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=wow.index, y=wow.values, name="Weekly Δ (WoW)",
        hovertemplate="%{x|%Y-%m-%d}<br>Δ: $%{y:,.0f}<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=wow_roll.index, y=wow_roll.values, name=f"Rolling {ROLL_W}-week", mode="lines"
    ))
    fig.add_hline(y=0, line_width=1, line_color="gray")  # zero line for reference

    dollars_axis_layout(fig, trillions=False)
    add_ranges(fig)

    # Add the QT anchor if it lies within our dates:
    xs = wow.index
    if len(xs):
        qt_annotation(fig, ANCHOR_DATE, "QT start",
                      x_min=xs.min().to_pydatetime(), x_max=xs.max().to_pydatetime())

    fig.update_layout(
        title="Fed SOMA Net Weekly Change (bars) with Rolling Trend",
        legend_title=None, margin=dict(l=40, r=20, t=60, b=40), hovermode="x unified",
    )
    fig.update_xaxes(title="")
    fig.update_yaxes(title="Δ Holdings (USD)")
    return fig
```

# known
- type hints suggest it will parse a dataframe and convert it into a plotly figure
- annotation states the purpose. and needs 2 computations, so probably 2 different versions of the df. one is a week over week difference, then a rolling average of that to show a trend line
- sort the dataframe with set_index and .sort_index(), then assign it to variable
- week over week is computed with .diff()
- rolling average is computed with rolling().mean()
- create a blank plotly figure with fig = go.Figure()
- use established functions dollar_axis_layout() and add_ranges() to add buttons and clean up dollar layout
- add annotations if it passes a date range check
- finally edit the axis labels, titles, then return the cleaned up new graph

# unknown
- most of the plotly functions are lost on my again. is it safe to assume most of it is frontend? or do i have to learn backend like .add_trace() and .add_hline()?

# answer
- s = df.set_index("as_of_date")["total"].sort_index()
    -Your df at this point looks like this (wide form):
        | as_of_date | total | mbs | tips | bills | ... |
        |-------------|--------|------|-------|------|
        | 2025-10-01 | 9.8e12 | … | … | … |
        | 2025-10-08 | 9.81e12| … | … | … |
    - set_index() gives you a time series keyed by date, similar to a dictionary but for pandas
    - ["total"] will select only the total column, producing a series
    - s is now essentially 
        as_of_date
        2025-10-01    9.80e12
        2025-10-08    9.81e12
        ...
    - .sort_index() will sort the index in chronological order, which is important because diff() and rolling() assume data is sequential
- wow = s.diff()
    - Series.diff() subtracts each element from its previous element, aligned by index
        wow[i] = s[i] − s[i−1]
- wow_roll = wow.rolling(ROLL_W, min_periods=1).mean()
    - Series.rolling(window=N) creates a moving window view over the data.
        - ROLL_W = 4, so a 4-week rolling window. declared at the beginning
        - min_periods=1 allows it to compute even for the first few weeks (where fewer than 4 values exist).
    - .mean() computes the average change
    Visually, wow becomes the bars, while wow_roll becomes the smoothed trend line.

- set_index → convert to time-indexed series (dates → totals).
- sort_index → chronological order.
- diff() → week-over-week delta.
- rolling(...).mean() → smooth out short-term noise.