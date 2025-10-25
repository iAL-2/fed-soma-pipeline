# Fed SOMA Pipeline

End-to-end pipeline for working with the Federal Reserve’s **System Open Market Account (SOMA)** data.  
This project downloads weekly SOMA summaries, validates them, stores them as CSV/Parquet, and builds an interactive Plotly dashboard.

This is an AI powered project that I am using to learn from.

---

## Features

### Data Management
- **Initial backfill:** `soma_initial_backfill.py`
- **Weekly update:** `soma_update_and_parquet_annotated.py`
- **Sanity checks:** `sanity_check.py`

### Visualization
- **Interactive dashboard:** `soma_dashboard_interactive.py`
- Charts include:
  - Net weekly change + rolling average  
  - Cumulative change since anchor date  
  - Composition by category (levels & shares)  
  - Total holdings  
- **Output:** `data/soma_dashboard.html` (open in your browser)

---

## Requirements

- Python 3.10+
- Packages: `pandas`, `plotly`

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Usage

1. **Backfill history** (one-time):
   ```bash
   python soma_initial_backfill.py
   ```

2. **Update with latest weekly data**:
   ```bash
   python soma_update_and_parquet_annotated.py
   ```

3. **Run checks** (optional):
   ```bash
   python sanity_check.py
   ```

4. **Build dashboard**:
   ```bash
   python soma_dashboard_interactive.py
   ```

   Open the generated file:
   ```
   data/soma_dashboard.html
   ```

---

## Config

Adjust these values inside `soma_dashboard_interactive.py`:

- `ANCHOR_DATE` → baseline for cumulative change  
- `ROLL_W` → rolling window for trend line  
- `ZOOM_YEARS` → number of years shown on “recent” charts  

---

## License

_No license chosen yet. All rights reserved by default._
