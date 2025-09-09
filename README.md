# Fed SOMA Pipeline

This is a personal project to collect the Federal Reserve's **SOMA weekly summary** data and make it easier to analyze.

## Usage

- Run `soma_update_and_parquet_annotated.py` to update the dataset (keeps a CSV and Parquet, and also saves a tidy long version).
- Run `sanity_check.py` to check the data for problems.
- Run `soma_dashboard.py` to make charts (weekly changes, cumulative change, composition).

Outputs are saved in the `data/` folder:
- `soma_summary_weekly.csv` (wide format)
- `soma_summary_long.csv` (tidy format)
- Charts as PNGs

## Why I built this
Mostly to practice Python, data handling, and Git, while also learning something about Fed balance sheet movements.
