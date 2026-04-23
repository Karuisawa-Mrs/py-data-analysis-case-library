# Data README

## Data Mode
Simulated: multi-level education data (students nested in schools).

## Schema
- `student_id`: int
- `school_id`: int
- `math_score`: float
- `reading_score`: float
- `ses`: float, socioeconomic status
- `school_resources`: float

## Acquisition
Generated internally by `analysis.py` using `np.random.default_rng(seed)`.
