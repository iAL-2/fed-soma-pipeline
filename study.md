```python
def weekly_dates(start: date, end: date, weekday: int = 2):
    """
    Generate 1 date per week between start and end on 'weekday'.
    weekday: Mon=0 ... Sun=6; Fed SOMA as-of is usually Wednesday (2).
    """
    d = start
    while d.weekday() != weekday:
        d += timedelta(days=1)
    while d <= end:
        yield d
        d += timedelta(days=7)
```
## known
- So this function first accepts 3 parameters: start, end, weekday. start and end date formats, and they expect to be filled in by settings later on, to be able to customize how much data and from when the user wants to collect from
- Starts from Wednesdays because that's when the fed releases the weekly reports

## unknowns
- next is d = start. not sure why we can't just stay with 'start'. is it because .weekday requires a variable?
- what is the main function doing? while d.weekday() != weekday
- what is yield? never seen this before
- what is timedelta doing?
- whats the main purpose of this function? += is string concatenation, but its using a date format. usually with +=, the string becomes all connected like "ThisIsAString". What happens in the date format? Makes more sense to me to use a list format yet here it seems like its concatenation

## answers
- d = start is used because we will be modifying the original argument, the start date. startdate is used only in this function so technically turning it into a local variable is not necessary, but it's a good step for hygiene and future habit. could also improve readability. If 'start' is used in a future function it wouldn't cause issues
- d is the start date. weekday() finds out which day of the week it is. so the main purpose `while d.weekday() != weekday` is to find the first wednesday after the date you inputted. Because the user can enter a date that is not a wednesday. 

start = 2024-06-01  # a Saturday
weekday = 2         # Wednesday

Loop:
d = 2024-06-01 (Saturday, 5) != 2  → add 1 day
d = 2024-06-02 (Sunday, 6) != 2    → add 1 day
d = 2024-06-03 (Monday, 0) != 2    → add 1 day
d = 2024-06-04 (Tuesday, 1) != 2   → add 1 day
d = 2024-06-05 (Wednesday, 2) == 2 → stop

- now d is a wednesday for sure

- timedelta is a date math object from the datetime library. It represents a time difference, either days, seconds, etc. Adding or subtracting timedelta from a date moves it forward or backwards by that amount of time. Since we declared days=1 and days=7 in this function with +=, it means move the date forward 1 day or 1 week
- yield is another part of the lazy generator series. It gives whatever the generator produces at that time without storing it into memory. If we don't need the full list of dates this saves calculation power
- okay so yield is actually similar to 'return'. it will return a value to the caller of this function, then pauses until the caller asks for the next value. Essentially, this whole `weekly_dates` function replaces an explicit list... by generating the list on demand. since there are so many dates in this pipeline, doing this saves having to have hundreds of dates in memory. 
- essentially this function is a generator that will seek out the first wednesday after the start date you put in, then yield every wednesday in sequence to anything that calls this function, until the specified end date

### Summary
Purpose: generate one weekly as-of date (default Wednesday) between start and end.
Type: generator (lazy evaluation).
Key idea: avoid building full list; stream dates to caller.

### -----------------------------------

```python
def fetch_csv_df(url: str, timeout=60, retries=3, backoff=1.5) -> pd.DataFrame:
    """
    GET a CSV into a DataFrame with basic retry.
    Raises on HTTP errors or empty content.
    """
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            if not r.content:
                raise ValueError("Empty response body")
            # Some endpoints may send text/csv; read robustly from bytes.
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
```
# known
- accepts argument `url`, which im assuming is from function `url_builder()`. has 3 default settings, assumedly set up in a way common for fetch requests
- raises error when empty content, which means the request was invalid/incorrect. also raises on http errors which could indicate server issues
- retries several times, which also is assumedly common for requests such as these

# unknown
- dont know about alot of these .commands(). assumedly they are from the pandas library but lets break it down.
- -> pd.DataFrame: this reads like a type hint, not sure if it is
- r = requests.get(url, timeout=timeout). whats this line doing? im assuming requests is a established collection from one of the imported libraries since its not defined in this function. the url argument means it will input the argument given to the function at calltime, and timeout is default to 60. but timeout=timeout is weird, not sure what it means
- r.raise_for_status() -> also not sure what raise_for_status() is from. in vscode is says raises httperror if there is one, but what library is this from? this function call, it returns http error to what? directly to the terminal? or does it return it back to r and modify r?
- if not r.content: this would only occur if the response had 0 content which is an error, so this one i understand. what i dont understand is where does .content come from. which library?
- df = pd.read_csv(io.BytesIO(r.content)) -> so if there is content, some sequence happens to it with panda, then it is assigned to df. break it down for me
- if df.empty: feels like just another way to check if it is falsy or not, not a method ive seen before. where does .empty come from? why not just use 'if not df'? anyways, if it is empty raise an error. otherwise, after passing all these guardrails, it is valid, then return it. it is now in dataframe format or something
- if there is an exception, assign it to e, then assign it to last_err. seems like this multiple variable assignment is to allow the function to capture multiple states of the errors
- the exception loops...by using .sleep()? not sure whats going on here, but the logic should be to loop 3 times by counting attempt up to retries. time im guessing is a library imported in that will allow python to count, sleep tells it how many seconds, and with back ** attempt every attempt will give it slightly more time in seconds to catch errors with service and such

# answers
- yes `-> pd.DataFrame` is a type hint. this format means type hint, just gotta see it more to get used to it
`r = requests.get(url, timeout=timeout)`
-  requests comes from the requests http library, and requests.get() returns a Response object, whatever that means
`timeout=timeout`
- is a keyword argument. requests.get() can handle the timeout keyword, and timeout is passed in through the initial function with a default of 60. it uses same name on both sides so it looks weird, but one is a keyword, the other is a local variable defined earlier
- timeout is if the server doesn't respond in n seconds(connect or read) it will raise a timeout error

`r.raise_for_status()`
-  is a method on the Response. my understanding is that after the response object has been generated and assigned to r, you can modify it with the methods from the requests library
- so raise_for_status() will raise `requests.exceptions.HTTPError` if status code is 4xx/5xx. If status is OK(2xx/3xx) then it does nothing, and r will not be modified.
- If an error is raised it will go to the except section and retry with limited attempts

`if not r.content`: 
- r.content is bytes of the response body (from Request). if the body is zero bytes, then raise ValueError

`df = pd.read_csv(io.BytesIO(r.content))`
- io.BytesIO() wraps raw bytes in a file-like buffer so pandas.read_csv can read it as if it were a file
- why use bytes instead of string? apparently there are some advantages like better encoding an delimiter reading by pandas. string is fine but need to use correct encoding
- result: df is a DataFrame parsed from CSV payload

`if df.empty: raise ValueError`
- df.empty is a pandas property. True if dataframe has 0 rows. Feels like a falsy checker. However, you can't use `if not df` because in pandas, dataframes have no truth value. So to check if it is empty or not have to use .empty or len(df) == 0

`except Exception as e: ... time.sleep(backoff ** attempt)`
- any exception that was caught will come here, then the most recent exception is stored so you can reraise it after the final attempt
- time.sleep(backoff ** attempt) implements exponential backoff in seconds. On the last attempt, it will not sleep but instead reraise the last error, which is stored as a variable.

## Summary
- Try to parse a URL to get a CSV DataFrame
- Catch errors and retry a limited amount of times

# ----------------
```python

def normalize_summary(df: pd.DataFrame, asof: date) -> pd.DataFrame:
    """
    Light normalization:
    - lower_snake_case columns
    - add as_of_date column
    """
    rename = {c: c.strip().lower().replace(" ", "_") for c in df.columns}
    df = df.rename(columns=rename)
    df["as_of_date"] = asof.isoformat()
    return df
```
# known
- this function accepts the dataframe from the url->csv->df function, as well as an asof date.
- asof argument probably is pulled from the first function `weekly_dates()`
- declares rename as a dictionary. intent here is to normalize the headers of the columns into lower snake case, as well as add the date as a column
- after normalizing, replace the original names of columns with the new normalized ones
- after cleaning up the data, return it back to the caller. so essentially, this function digests the uncleaned data, normalizes it, adds new important columns, then returns a cleaned up version

# unknown 
- {c: c.strip().lower().replace(" ", "_") for c in df.columns}, why is this in dictionary format? im guessing it's because pd.dataframe is similar to a dictionary? i understand the contents, iterate through df.columns and replace the column names with the normalized versions, then assign to rename. does this generator expression not modify the contents of df.columns directly? im guessing it doesnt because of the way this was done but i'd like clarification
- df = df.rename(columes=rename), again this seems to be a panda function. why is it though you decide to make the keyword the same as the variable? isnt it confusing to readers? it's 2 different things, with the same name. yes you declare them equal to another further down but it's confusing at this point. i guess what id like to know is whether or not this is good practice or industry standard. if it is, nothing to be done, i will have to adapt
- df["as_of_date"] = asof.isoformat(), this line suggests to me that df, our dataframe, is structured like a collection of some kind, not sure which. but this is a collection lookup. since it's a string not a value, it must be a dictionary. if "as_of_date" doesnt exist, create a new key:value pair. now asof.isoformat()... it turns asof, which should be in a date format, into isoform. i still dont know much about isoformat, and i suspect you will tell me that isoformat is just what panda uses, even though i dont know what that means in detail yet.

# answers
`{c: c.strip().lower().replace(" ", "_") for c in df.columns}`
- this is a dictionary because the intent is to create a mapping in dictionary form. the key point is c: new expression. this was the part i missed initially. this creates a key:value pair that the next step can use pair the old and new together, and modify it with .rename(). it's assigned to variable rename because it doesn't modify df.columns yet

` df = df.rename(columns=rename)`
- df.columns must be modified with .rename(), so here we use the mapping from earlier
- columns is indeed a keyword argument, i got this right
- columns=rename is equal to oldname = newname, for columns
- .rename() returns a new dataframe. what this means is the old one isn't modified unless you also pass inplace=true. in this case we directly overwrote the old one with df = df.rename(...), since we don't need the old data anymore in memory
- this same name is common and accepted, but if i dont like it i can change it to something else readable

`df["as_of_date"] = asof.isoformat()`
- df[...] with a string key accesses/creates a column (DataFrame is dict-like for columns)
- since it's dict-like, dict reading methods work. if as_of_date doesn't exist, pandas creates it. if it exists, its overwritten
- so .isoformat() converts the datetime.date into a string... an iso string. apparently there are many string formats. iso plays nicely with csv/json

# summary
- This function normalizes the dataframe created earlier into one using lower snake case, adds an asofdate column, then returns the cleaned up dataframe to caller


```python
def append_csv(df: pd.DataFrame, path: Path):
    """Append to CSV (write header if file doesn’t exist)."""
    header = not path.exists()
    df.to_csv(path, mode="a", index=False, header=header, quoting=csv.QUOTE_MINIMAL)
```

# known
- path type hint probably indicates the \data and DATA_DIR type of paths
- the note says append to csv, write a header if file doesn't exist
- formatting for the to_csv() looks similar to open()

# unknown
- first time seeing .exists(). looks to be some kind of falsy check, but not sure what kind of variable declaration this is. header = not path.exists(), means header is not -> a boolean check?
- what is to_csv() doing exactly? 
- what is mode = "a"? is it similar to "r" and "w" for read and write?
- actually just break down the entire df.to_csv(...) statement

# answers
- the path type refers to a Path object from pathlib. referring to these type things as objects

`header = not path.exists()`
- .exists() checks whether the file exists or not on the filesystem, and it returns true/false. so my earlier understanding is correct, it's a boolean check
- since we want to create headers the first time we create the file, we add `not` in front for a double negative to return header=True. Afterwards, if the header exists, it will return false. So this statement is telling us whether or not we want to write the header based on the current state of whether or not the path exists

`df.to_csv(path, mode="a", index=False, header=header, quoting=csv.QUOTE_MINIMAL)`
- to_csv() is a pandas method that writesa DataFrame to a .csv file
- path is where to save it
- mode="a" reads for append. its the same as the I/'O modes in python, 'w' is write, 'r' is read, 'a' is append
- index=False. By default, dataframes have a numeric index column. That's not necessary for this data transformation so we put false to prevent writing that colum to the CSV
- header=. If it's false it doesn't add new headers. Since the logic is defined earlier it is used here
- quoting=csv.QUOTE_MINIMAL, comes from python's csv module. it controls how values with commas or quotes are escaped(whatever that means).  QUOTE_MINIMAL only quotes fields that need it(those containing commas or quotes.) other options are QUOTE_ALL, and QUOTE_NONE

“Escaping” just means making special characters safe in plain text. Example: if a field contains a comma, CSV needs to quote it, or else it would split into two columns


# summary
- Check if the CSV File exists. If not, mark it down in boolean logic so we know whether or not to write the first line of headers
- Append the dataframe's rows to the CSV.
    - Dont include the index
    - include headers only if it's a new file
    - use safe CSV quoting