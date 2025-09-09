Fed SOMA Pipeline

End-to-end pipeline for working with the Federal Reserve’s System Open Market Account (SOMA) data.
This project downloads weekly SOMA summaries, validates them, stores them as CSV/Parquet, and builds an interactive Plotly dashboard.

Features

Data management

Initial backfill (soma_initial_backfill.py)

Weekly update (soma_update_and_parquet_annotated.py)

Sanity checks (sanity_check.py)

Visualization

Interactive dashboard (soma_dashboard_interactive.py)

Charts:

Net weekly change + rolling average

Cumulative change since anchor date

Composition by category (levels & shares)

Total holdings

Output: data/soma_dashboard.html (open in your browser)

Requirements

Python 3.10+

Packages: pandas, plotly

Install dependencies:
