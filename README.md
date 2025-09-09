# Fed SOMA Pipeline

End-to-end pipeline for working with the Federal Reserve’s **System Open Market Account (SOMA)** data.  
This project downloads weekly SOMA summaries, validates them, stores them as CSV/Parquet, and builds an interactive Plotly dashboard.

---

## Features
- **Data management**
  - Initial backfill (`soma_initial_backfill.py`)
  - Weekly update (`soma_update_and_parquet_annotated.py`)
  - Sanity checks (`sanity_check.py`)

- **Visualization**
  - Interactive dashboard (`soma_dashboard_interactive.py`)
  - Charts:
    - Net weekly change + rolling average
    - Cumulative change since anchor date
    - Composition by category (levels & shares)
    - Total holdings
  - Output: `data/soma_dashboard.html` (open in your browser)

---

## Requirements
- Python 3.10+
- Packages: `pandas`, `plotly`

Install dependencies:
```bash
pip install -r requirements.txt

Usage

    Backfill history (one-time):

python soma_initial_backfill.py

Update with latest weekly data:

python soma_update_and_parquet_annotated.py

Run checks (optional):

python sanity_check.py

Build dashboard:

python soma_dashboard_interactive.py

Open the generated file:

    data/soma_dashboard.html

Config

Adjust these values inside soma_dashboard_interactive.py:

    ANCHOR_DATE → baseline for cumulative change

    ROLL_W → rolling window for trend line

    ZOOM_YEARS → number of years shown on “recent” charts

License

No license chosen yet. All rights reserved by default.


Would you like me to also add a **requirements.txt** draft for your repo so it’s easy to install?

