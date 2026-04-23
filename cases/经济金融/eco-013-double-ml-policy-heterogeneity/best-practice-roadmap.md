# Best-Practice Roadmap: eco-013-double-ml-policy-heterogeneity

## Current Implementation (Fallback)
Due to Windows compilation issues with `econml`, the current `analysis.py` uses:
- **Manual cross-fitting Double ML** implemented with pure `sklearn`
- `RandomForestRegressor` / `GradientBoostingRegressor` as nuisance estimators
- Neyman orthogonal score computed manually
- CATE estimated by sub-grouping on covariate bins (not causal forests)

## Target Best-Practice Implementation
Once `econml` is installable, migrate to:

### 1. Double Machine Learning (DML)
**Library**: `py-why/EconML` (https://github.com/py-why/EconML)
**Installation**: `pip install econml`
**Code pattern**:
```python
from econml.dml import LinearDML, CausalForestDML
from sklearn.ensemble import GradientBoostingRegressor, GradientBoostingClassifier

# Linear DML for ATE with linear CATE
est = LinearDML(
    model_y=GradientBoostingRegressor(n_estimators=100),
    model_t=GradientBoostingClassifier(n_estimators=100),
    cv=5,
)
est.fit(Y, T, X=X, W=W)
ate = est.ate_(X_test)
ate_interval = est.ate_interval_(X_test, alpha=0.05)

# Causal Forest DML for heterogeneous effects
cf_est = CausalForestDML(
    model_y=GradientBoostingRegressor(n_estimators=100),
    model_t=GradientBoostingClassifier(n_estimators=100),
    cv=5,
    criterion='mse',
    n_estimators=1000,
    min_samples_leaf=10,
    max_depth=5,
)
cf_est.fit(Y, T, X=X, W=W)
cate = cf_est.effect(X_test)
# Feature importance from causal forest splits
importances = cf_est.feature_importances_
```
**Artifacts to add**:
- `outputs/dml_summary.txt` — EconML model summary
- `outputs/causal_forest_importances.csv` — Feature importance from forest splits
- `outputs/ate_confidence_intervals.csv` — ATE point estimates + CI

### 2. Optional: DoWhy for Assumption Transparency
**Library**: `py-why/dowhy`
**Installation**: `pip install dowhy`
**Code pattern**:
```python
from dowhy import CausalModel

model = CausalModel(
    data=data,
    treatment='treatment',
    outcome='y',
    common_causes=['x1', 'x2', 'x3'],
)
identified_estimand = model.identify_effect()
estimate = model.estimate_effect(
    identified_estimand,
    method_name="backdoor.econml.dml.LinearDML",
    method_params={"init_params": {...}},
)
refutation = model.refute_estimate(
    identified_estimand, estimate,
    method_name="random_common_cause",
)
```

### 3. Migration Steps
1. Install `econml` (and optionally `dowhy`)
   - Windows note: if pip fails, try `conda install -c conda-forge econml`
2. In `analysis.py`, detect `econml` availability:
   ```python
   try:
       from econml.dml import LinearDML, CausalForestDML
       HAS_ECONML = True
   except ImportError:
       HAS_ECONML = False
   ```
3. Replace manual cross-fitting with `LinearDML` for ATE/ATT
4. Add `CausalForestDML` branch for CATE estimation
5. Keep manual sklearn fallback when `econml` absent
6. Update `expected_artifacts` in `index.md`
7. Update `references.bib` to add Chernozhukov et al. (2018) and Athey et al. (2019)

### 4. Validation After Migration
```bash
python analysis.py --smoke-test
# Should produce: ate_att_estimates.csv, cate_by_segment.csv,
# cate_distribution.png, AND causal_forest_importances.csv
```
