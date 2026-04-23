# Best-Practice Roadmap: eco-012-volatility-forecast-garch-tft

## Current Implementation (Fallback)
Due to Windows compilation issues with `arch` and `pytorch-forecasting`, the current `analysis.py` uses:
- **statsmodels** for ARCH effect testing (Ljung-Box on squared returns, simple volatility proxy)
- **sklearn GradientBoostingRegressor** as the ML-based volatility forecaster
- Rolling-window variance as target

## Target Best-Practice Implementation
Once dependencies are installable, migrate to:

### 1. GARCH Family (classical baseline)
**Library**: `bashtage/arch` (https://github.com/bashtage/arch)
**Installation**: `pip install arch`
**Code pattern**:
```python
from arch import arch_model

# GARCH(1,1)
am = arch_model(returns, vol='Garch', p=1, q=1)
res = am.fit(disp='off')
forecasts = res.forecast(horizon=5)

# EGARCH(1,1)
am_egarch = arch_model(returns, vol='EGARCH', p=1, q=1)
res_egarch = am_egarch.fit(disp='off')
```
**Artifacts to add**:
- `outputs/garch_summary.txt` — GARCH parameter estimates and diagnostics
- `outputs/egarch_summary.txt` — EGARCH parameter estimates
- `outputs/conditional_volatility.csv` — Fitted conditional volatility series

### 2. Temporal Fusion Transformer (deep learning)
**Library**: `pytorch-forecasting` or `Nixtla/neuralforecast`
**Installation**: `pip install pytorch-forecasting` or `pip install neuralforecast`
**Code pattern (pytorch-forecasting)**:
```python
from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet
from pytorch_forecasting.data import GroupNormalizer

# Prepare time-series dataset with known/realized volatility
# Target: realized_vol (e.g., squared returns or Parkinson estimator)
# Covariates: lagged returns, day-of-week, rolling stats

training = TimeSeriesDataSet(
    data_df,
    time_idx="time_idx",
    target="realized_vol",
    group_ids=["series_id"],
    max_encoder_length=60,
    max_prediction_length=5,
    time_varying_known_reals=["time_idx", "dayofweek"],
    time_varying_unknown_reals=["returns_lag1", "returns_lag5"],
    target_normalizer=GroupNormalizer(groups=["series_id"]),
)

# Train TFT
tft = TemporalFusionTransformer.from_dataset(
    training,
    learning_rate=0.03,
    hidden_size=16,
    attention_head_size=2,
    dropout=0.1,
    hidden_continuous_size=8,
    output_size=1,
    loss=QuantileLoss(),
)
```
**Artifacts to add**:
- `outputs/tft_predictions.csv` — Out-of-sample volatility forecasts
- `outputs/tft_attention_weights.csv` — Interpretable attention over time steps

### 3. Migration Steps
1. Install `arch` and `pytorch-forecasting` (or `neuralforecast`)
2. In `analysis.py`, detect library availability and branch:
   ```python
   try:
       from arch import arch_model
       HAS_ARCH = True
   except ImportError:
       HAS_ARCH = False
   ```
3. Replace the fallback sklearn-only branch with the GARCH + TFT pipeline
4. Keep the fallback branch as a degraded mode when libraries are absent
5. Update `expected_artifacts` in `index.md` to include GARCH/TFT-specific outputs
6. Update `references.bib` to add Lim et al. (2021) TFT paper

### 4. Known Windows Issues
- `arch` requires C compiler; if MSVC not available, use conda: `conda install -c conda-forge arch-py`
- `pytorch-forecasting` depends on `torch` and `pytorch-lightning`; ensure torch CUDA/CPU wheel matches

### 5. Validation After Migration
```bash
python analysis.py --smoke-test
# Should produce ALL expected artifacts including GARCH summaries and TFT predictions
```
