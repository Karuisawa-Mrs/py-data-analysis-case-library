# Data README

## Data Mode
Hybrid: small simulated credit risk dataset generated deterministically by `analysis.py`.

## Schema
- `loan_amount`: float, requested loan amount
- `income`: float, annual income
- `credit_score`: float, standardized credit score
- `debt_to_income`: float, debt-to-income ratio
- `employment_years`: float, years at current job
- `default`: int, 1 if defaulted, 0 otherwise

## Acquisition
Data is generated internally via `np.random.default_rng(seed)` to ensure full reproducibility without external downloads.
