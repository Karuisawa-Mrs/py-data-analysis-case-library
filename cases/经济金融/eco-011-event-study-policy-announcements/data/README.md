# Data README

## Data Mode
Hybrid: simulated stock returns and event dates for policy announcement event study.

## Schema
- `date`: datetime
- `firm_id`: str
- `return`: float, daily stock return
- `market_return`: float, market index return
- `event_date`: bool, True if policy announcement date

## Acquisition
Data is generated internally by `analysis.py` to mimic event-study structure. No live market data is downloaded.
