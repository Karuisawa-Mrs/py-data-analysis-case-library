# Data README

## Data Mode
Hybrid: simulated policy documents with pre-defined topic mixtures.

## Schema
- `doc_id`: str
- `text`: str, simulated document text
- `true_topic`: str, ground-truth topic label

## Acquisition
Documents are generated internally by `analysis.py` using templates and random word sampling.
