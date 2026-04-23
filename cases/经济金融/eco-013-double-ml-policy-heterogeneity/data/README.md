# Data README

## Data Mode
Simulated: synthetic panel with treatment, covariates, and outcomes.

## Schema
- `unit_id`: int
- `period`: int
- `treatment`: int, 0/1
- `y`: float, outcome
- `x1`, `x2`: float, confounders

## Acquisition
Generated internally by `analysis.py` using `np.random.default_rng(seed)`.
