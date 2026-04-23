# Data README

## Data Mode
Hybrid: simulated public feedback texts with sentiment labels.

## Schema
- `text_id`: str
- `text`: str, feedback text
- `sentiment`: int, 0=negative, 1=positive

## Acquisition
Texts are generated internally using templates and keyword substitution to ensure reproducibility.
