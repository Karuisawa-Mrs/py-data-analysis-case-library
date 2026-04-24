from __future__ import annotations

# Fallback implementation: this case uses a manual sklearn-based Double ML workflow
# because econml is not currently installable in the target Windows environment.
# See best-practice-roadmap.md for the intended EconML migration path.

import argparse
from pathlib import Path
from typing import TypedDict

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from numpy.typing import NDArray
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor, RandomForestRegressor
from sklearn.model_selection import KFold

try:
    from econml.dml import CausalForestDML, LinearDML

    HAS_ECONML = True
except ImportError:  # pragma: no cover - depends on optional Python 3.10-3.12 environment
    CausalForestDML = None
    LinearDML = None
    HAS_ECONML = False


CASE_ID = "eco-013-double-ml-policy-heterogeneity"
CASE_TITLE = "政策效果的异质性分析：双重机器学习与因果森林"
CLAIM_BOUNDARY = "该案例演示因果机器学习方法，不替代真实政策评估的严谨识别设计。"

FloatArray = NDArray[np.float64]
FEATURE_COLUMNS = ["X1", "X2", "X3", "W1", "W2", "W3", "W4", "post_period", "period"]
HETEROGENEITY_COLUMNS = ["X1", "X2", "X3", "post_period"]
CONTROL_COLUMNS = ["W1", "W2", "W3", "W4", "period"]


class Paths(TypedDict):
    case_dir: Path
    data_dir: Path
    output_dir: Path
    params_file: Path
    roadmap_file: Path


class RunConfig(TypedDict):
    seed: int
    n_units: int
    n_periods: int
    n_bootstrap: int
    n_folds: int
    output_dir_name: str


def parse_args() -> bool:
    parser = argparse.ArgumentParser(description="Fallback manual Double ML analysis for policy heterogeneity.")
    _ = parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run the full pipeline on a reduced sample while producing all required artifacts.",
    )
    args = parser.parse_args()
    smoke_test_value = getattr(args, "smoke_test", False)
    return smoke_test_value if isinstance(smoke_test_value, bool) else False


def resolve_paths() -> Paths:
    case_dir = Path(__file__).resolve().parent
    data_dir = case_dir / "data"
    params_file = case_dir / "params.yaml"

    params_text = params_file.read_text(encoding="utf-8")
    raw_params = yaml.safe_load(params_text) or {}
    output_dir_name = str(raw_params.get("output_dir", "outputs")) if isinstance(raw_params, dict) else "outputs"
    output_dir = case_dir / output_dir_name

    data_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    return {
        "case_dir": case_dir,
        "data_dir": data_dir,
        "output_dir": output_dir,
        "params_file": params_file,
        "roadmap_file": case_dir / "best-practice-roadmap.md",
    }


def load_params(params_file: Path) -> dict[str, object]:
    params = yaml.safe_load(params_file.read_text(encoding="utf-8")) or {}
    if not isinstance(params, dict):
        raise ValueError("params.yaml must parse to a mapping")
    if "seed" not in params:
        raise ValueError("params.yaml must define seed")
    return params


def require_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(f"{field_name} must be convertible to int")
    return int(value)


def build_run_config(params: dict[str, object], smoke_test: bool) -> RunConfig:
    return {
        "seed": require_int(params["seed"], "seed"),
        "n_units": 50 if smoke_test else 250,
        "n_periods": 10 if smoke_test else 20,
        "n_bootstrap": 200 if smoke_test else 500,
        "n_folds": 5,
        "output_dir_name": str(params.get("output_dir", "outputs")),
    }


def simulate_policy_panel(seed: int, n_units: int, n_periods: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n_obs = n_units * n_periods

    unit_ids = np.repeat(np.arange(n_units), n_periods)
    periods = np.tile(np.arange(n_periods), n_units)
    post = (periods >= n_periods // 2).astype(float)

    unit_quality = rng.normal(0.0, 1.0, size=n_units)
    unit_exposure = rng.normal(0.0, 1.0, size=n_units)
    unit_trend = rng.normal(0.0, 0.35, size=n_units)

    x1_base = np.repeat(unit_quality, n_periods) + rng.normal(0.0, 0.45, size=n_obs)
    x2_base = np.repeat(unit_exposure, n_periods) + rng.normal(0.0, 0.55, size=n_obs)
    x3_base = np.repeat(unit_trend, n_periods) + 0.15 * periods + rng.normal(0.0, 0.40, size=n_obs)

    w1 = 0.4 * x1_base - 0.2 * x2_base + rng.normal(0.0, 0.65, size=n_obs)
    w2 = 0.2 * x2_base + 0.25 * post + rng.normal(0.0, 0.60, size=n_obs)
    w3 = rng.normal(0.0, 1.0, size=n_obs)
    w4 = np.sin(periods / max(n_periods - 1, 1) * np.pi) + rng.normal(0.0, 0.15, size=n_obs)

    linear_propensity = (
        -0.45
        + 0.60 * post
        + 0.55 * x1_base
        - 0.35 * x2_base
        + 0.22 * x3_base
        + 0.18 * w1
        - 0.12 * w2
        + 0.25 * x1_base * post
        - 0.08 * x2_base * post
    )
    propensity = 1.0 / (1.0 + np.exp(-linear_propensity))
    propensity = np.clip(propensity, 0.05, 0.95)
    treatment = rng.binomial(1, propensity, size=n_obs).astype(float)

    true_effect = 1.10 + 0.55 * x1_base - 0.20 * x2_base + 0.18 * post + 0.12 * x1_base * post
    baseline_outcome = (
        2.0
        + 0.80 * x1_base
        - 0.50 * x2_base
        + 0.35 * x3_base
        + 0.25 * w1
        + 0.15 * w2
        - 0.10 * w3
        + 0.30 * w4
        + np.repeat(unit_quality, n_periods)
        + 0.04 * periods
    )
    outcome = baseline_outcome + true_effect * treatment + rng.normal(0.0, 1.0, size=n_obs)

    panel = pd.DataFrame(
        {
            "unit_id": unit_ids.astype(int),
            "period": periods.astype(int),
            "post_period": post.astype(int),
            "X1": x1_base,
            "X2": x2_base,
            "X3": x3_base,
            "W1": w1,
            "W2": w2,
            "W3": w3,
            "W4": w4,
            "propensity": propensity,
            "T": treatment.astype(int),
            "true_tau": true_effect,
            "Y": outcome,
        }
    )
    return panel.sort_values(["unit_id", "period"]).reset_index(drop=True)


def fit_nuisance_models(train_features: pd.DataFrame, train_outcome: pd.Series, train_treatment: pd.Series, seed: int) -> tuple[RandomForestRegressor, GradientBoostingRegressor]:
    model_y = RandomForestRegressor(
        n_estimators=300,
        max_depth=6,
        min_samples_leaf=5,
        random_state=seed,
        n_jobs=-1,
    )
    model_t = GradientBoostingRegressor(
        n_estimators=220,
        learning_rate=0.05,
        max_depth=3,
        min_samples_leaf=10,
        subsample=0.9,
        random_state=seed,
    )
    _ = model_y.fit(train_features, train_outcome)
    _ = model_t.fit(train_features, train_treatment)
    return model_y, model_t


def bootstrap_mean_interval(values: FloatArray, n_bootstrap: int, seed: int, alpha: float = 0.05) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    n_obs = len(values)
    boot_means = np.empty(n_bootstrap, dtype=float)
    for idx in range(n_bootstrap):
        draw = rng.choice(values, size=n_obs, replace=True)
        boot_means[idx] = float(np.mean(draw))
    lower = float(np.quantile(boot_means, alpha / 2.0))
    upper = float(np.quantile(boot_means, 1.0 - alpha / 2.0))
    return lower, upper


def manual_double_ml_estimate(panel: pd.DataFrame, n_folds: int, n_bootstrap: int, seed: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    features = panel.loc[:, FEATURE_COLUMNS].copy()
    outcome = panel["Y"].astype(float)
    treatment = panel["T"].astype(float)

    mu_y = np.zeros(len(panel), dtype=float)
    mu_t = np.zeros(len(panel), dtype=float)
    fold_index = np.zeros(len(panel), dtype=int)

    splitter = KFold(n_splits=n_folds, shuffle=True, random_state=seed)

    # Manual Double ML procedure:
    # 1) Split the sample into K folds.
    # 2) For each fold, fit nuisance models for E[Y|X,W] and E[T|X,W] on the other K-1 folds.
    # 3) Predict the held-out fold to obtain cross-fitted mu_y and mu_t.
    # 4) Form residuals Y-mu_y and T-mu_t and compute the orthogonal pseudo-effect.
    # 5) Aggregate the pseudo-effect to obtain the ATE and bootstrap its sampling interval.
    for fold_id, (train_idx, test_idx) in enumerate(splitter.split(features), start=1):
        train_features = features.iloc[train_idx].copy()
        test_features = features.iloc[test_idx].copy()
        train_outcome = outcome.iloc[train_idx].copy()
        train_treatment = treatment.iloc[train_idx].copy()

        model_y, model_t = fit_nuisance_models(
            train_features=train_features,
            train_outcome=train_outcome,
            train_treatment=train_treatment,
            seed=seed + fold_id,
        )

        mu_y[test_idx] = model_y.predict(test_features)
        mu_t_fold = model_t.predict(test_features)
        mu_t[test_idx] = np.clip(mu_t_fold, 0.02, 0.98)
        fold_index[test_idx] = fold_id

    y_residual = outcome.to_numpy(dtype=float) - mu_y
    t_residual = treatment.to_numpy(dtype=float) - mu_t
    denominator = float(np.mean(np.square(t_residual)))
    if denominator <= 1e-8:
        raise ValueError("Orthogonal score denominator is too small; treatment residual variance collapsed.")

    pseudo_effect = (y_residual * t_residual) / denominator
    ate = float(np.mean(pseudo_effect))

    treated_mask = treatment.to_numpy(dtype=float) == 1.0
    treated_effects = pseudo_effect[treated_mask]
    att = float(np.mean(treated_effects)) if treated_effects.size else float("nan")

    ate_ci_low, ate_ci_high = bootstrap_mean_interval(
        values=pseudo_effect.astype(float),
        n_bootstrap=n_bootstrap,
        seed=seed + 101,
    )
    att_ci_low, att_ci_high = bootstrap_mean_interval(
        values=treated_effects.astype(float) if treated_effects.size else np.array([np.nan], dtype=float),
        n_bootstrap=n_bootstrap,
        seed=seed + 202,
    )

    score_frame = panel.copy()
    score_frame["fold"] = fold_index.astype(int)
    score_frame["mu_y"] = mu_y
    score_frame["mu_t"] = mu_t
    score_frame["y_residual"] = y_residual
    score_frame["t_residual"] = t_residual
    score_frame["orthogonal_score"] = pseudo_effect
    score_frame["score_numerator"] = y_residual * t_residual

    estimates = pd.DataFrame(
        [
            {
                "estimand": "ATE",
                "estimate": ate,
                "ci_lower": ate_ci_low,
                "ci_upper": ate_ci_high,
                "n_obs": int(len(panel)),
                "treated_share": float(treatment.mean()),
                "orthogonal_denominator": denominator,
                "bootstrap_draws": int(n_bootstrap),
            },
            {
                "estimand": "ATT",
                "estimate": att,
                "ci_lower": att_ci_low,
                "ci_upper": att_ci_high,
                "n_obs": int(treated_mask.sum()),
                "treated_share": float(treatment.mean()),
                "orthogonal_denominator": denominator,
                "bootstrap_draws": int(n_bootstrap),
            },
        ]
    )

    diagnostics = (
        score_frame.groupby("fold", as_index=False)
        .agg(
            n_obs=("fold", "size"),
            mean_mu_y=("mu_y", "mean"),
            mean_mu_t=("mu_t", "mean"),
            mean_y_residual=("y_residual", "mean"),
            std_y_residual=("y_residual", "std"),
            mean_t_residual=("t_residual", "mean"),
            std_t_residual=("t_residual", "std"),
            mean_score=("orthogonal_score", "mean"),
            treated_share=("T", "mean"),
        )
        .assign(orthogonal_denominator=denominator)
    )

    return estimates, diagnostics, score_frame


def build_segment_table(score_frame: pd.DataFrame, n_bootstrap: int, seed: int) -> pd.DataFrame:
    segmented = score_frame.copy()
    segmented["x1_segment"] = pd.qcut(segmented["X1"], q=4, labels=["Q1", "Q2", "Q3", "Q4"], duplicates="drop")

    rows: list[dict[str, float | int | str]] = []
    for segment_idx, (segment_name, group) in enumerate(segmented.groupby("x1_segment", dropna=False, observed=False), start=1):
        effects = group["orthogonal_score"].to_numpy(dtype=float)
        ci_low, ci_high = bootstrap_mean_interval(
            values=effects,
            n_bootstrap=n_bootstrap,
            seed=seed + segment_idx * 17 + len(group),
        )
        label = str(segment_name) if segment_name is not None else "missing"
        rows.append(
            {
                "segment_variable": "X1_quartile",
                "segment": label,
                "n_obs": int(len(group)),
                "treated_share": float(group["T"].mean()),
                "segment_ate": float(group["orthogonal_score"].mean()),
                "ci_lower": ci_low,
                "ci_upper": ci_high,
                "mean_X1": float(group["X1"].mean()),
                "mean_true_tau": float(group["true_tau"].mean()),
            }
        )

    segment_table = pd.DataFrame(rows).sort_values("segment").reset_index(drop=True)
    return segment_table


def build_fallback_importances(score_frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    effects = score_frame["orthogonal_score"].to_numpy(dtype=float)
    for column in HETEROGENEITY_COLUMNS:
        values = score_frame[column].to_numpy(dtype=float)
        if np.std(values) <= 1e-12 or np.std(effects) <= 1e-12:
            importance = 0.0
        else:
            importance = abs(float(np.corrcoef(values, effects)[0, 1]))
        rows.append(
            {
                "feature": column,
                "importance": importance,
                "source": "fallback_abs_correlation_with_orthogonal_score",
            }
        )
    return pd.DataFrame(rows).sort_values("importance", ascending=False).reset_index(drop=True)


def econml_double_ml_estimate(
    panel: pd.DataFrame,
    n_bootstrap: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    if not HAS_ECONML or LinearDML is None or CausalForestDML is None:
        raise ImportError("econml is not available in this Python environment")

    y = panel["Y"].to_numpy(dtype=float)
    t = panel["T"].to_numpy(dtype=float)
    x = panel.loc[:, HETEROGENEITY_COLUMNS].copy()
    w = panel.loc[:, CONTROL_COLUMNS].copy()

    linear_dml = LinearDML(
        model_y=GradientBoostingRegressor(n_estimators=100, max_depth=3, random_state=seed),
        model_t=GradientBoostingClassifier(n_estimators=100, max_depth=2, random_state=seed + 1),
        discrete_treatment=True,
        cv=3,
        random_state=seed,
    )
    linear_dml.fit(y, t, X=x, W=w)
    linear_effect = np.asarray(linear_dml.effect(x), dtype=float)
    ate = float(np.mean(linear_effect))
    ate_ci_low, ate_ci_high = bootstrap_mean_interval(linear_effect, n_bootstrap=n_bootstrap, seed=seed + 101)

    treated_effects = linear_effect[t == 1.0]
    att = float(np.mean(treated_effects)) if treated_effects.size else float("nan")
    att_ci_low, att_ci_high = bootstrap_mean_interval(
        treated_effects if treated_effects.size else np.array([np.nan], dtype=float),
        n_bootstrap=n_bootstrap,
        seed=seed + 202,
    )

    causal_forest = CausalForestDML(
        model_y=GradientBoostingRegressor(n_estimators=100, max_depth=3, random_state=seed + 2),
        model_t=GradientBoostingClassifier(n_estimators=100, max_depth=2, random_state=seed + 3),
        discrete_treatment=True,
        n_estimators=200,
        min_samples_leaf=8,
        max_depth=6,
        cv=3,
        random_state=seed + 4,
    )
    causal_forest.fit(y, t, X=x, W=w)
    forest_effect = np.asarray(causal_forest.effect(x), dtype=float)

    score_frame = panel.copy()
    score_frame["fold"] = 0
    score_frame["mu_y"] = np.nan
    score_frame["mu_t"] = np.nan
    score_frame["y_residual"] = np.nan
    score_frame["t_residual"] = np.nan
    score_frame["orthogonal_score"] = linear_effect
    score_frame["causal_forest_cate"] = forest_effect
    score_frame["score_numerator"] = np.nan

    estimates = pd.DataFrame(
        [
            {
                "estimand": "ATE",
                "estimate": ate,
                "ci_lower": ate_ci_low,
                "ci_upper": ate_ci_high,
                "n_obs": int(len(panel)),
                "treated_share": float(np.mean(t)),
                "orthogonal_denominator": np.nan,
                "bootstrap_draws": int(n_bootstrap),
            },
            {
                "estimand": "ATT",
                "estimate": att,
                "ci_lower": att_ci_low,
                "ci_upper": att_ci_high,
                "n_obs": int(np.sum(t == 1.0)),
                "treated_share": float(np.mean(t)),
                "orthogonal_denominator": np.nan,
                "bootstrap_draws": int(n_bootstrap),
            },
        ]
    )
    diagnostics = pd.DataFrame(
        [
            {
                "n_obs": int(len(panel)),
                "mean_mu_y": np.nan,
                "mean_mu_t": np.nan,
                "mean_y_residual": np.nan,
                "std_y_residual": np.nan,
                "mean_t_residual": np.nan,
                "std_t_residual": np.nan,
                "mean_score": ate,
                "treated_share": float(np.mean(t)),
                "orthogonal_denominator": np.nan,
                "implementation": "econml_LinearDML_and_CausalForestDML",
            }
        ]
    )
    importances = pd.DataFrame(
        {
            "feature": HETEROGENEITY_COLUMNS,
            "importance": np.asarray(causal_forest.feature_importances_, dtype=float),
            "source": "econml_causal_forest_split_importance",
        }
    ).sort_values("importance", ascending=False)
    return estimates, diagnostics, score_frame, importances, "econml LinearDML + CausalForestDML"


def save_cate_histogram(score_frame: pd.DataFrame, figure_path: Path) -> None:
    fig, axis = plt.subplots(figsize=(8, 5), constrained_layout=True)
    score_mean = float(score_frame["orthogonal_score"].mean())
    _ = axis.hist(
        score_frame["orthogonal_score"],
        bins=30,
        color="#1f77b4",
        edgecolor="white",
        alpha=0.85,
    )
    _ = axis.axvline(score_mean, color="#d62728", linestyle="--", linewidth=2.0)
    _ = axis.set_title("Cross-fitted pseudo-effect distribution")
    _ = axis.set_xlabel("Pseudo-effect")
    _ = axis.set_ylabel("Count")
    axis.grid(alpha=0.2)
    fig.savefig(figure_path, dpi=150)
    plt.close(fig)


def write_summary(
    summary_path: Path,
    config: RunConfig,
    panel: pd.DataFrame,
    estimates: pd.DataFrame,
    segment_table: pd.DataFrame,
    diagnostics: pd.DataFrame,
    smoke_test: bool,
    implementation_note: str,
) -> None:
    ate_row = estimates.loc[estimates["estimand"] == "ATE"].iloc[0]
    att_row = estimates.loc[estimates["estimand"] == "ATT"].iloc[0]
    top_segment = segment_table.sort_values("segment_ate", ascending=False).iloc[0]

    lines = [
        f"case_id: {CASE_ID}",
        f"title: {CASE_TITLE}",
        f"mode: {'SMOKE TEST' if smoke_test else 'FULL RUN'}",
        f"implementation_note: {implementation_note}",
        f"seed: {config['seed']}",
        f"n_units: {config['n_units']}",
        f"n_periods: {config['n_periods']}",
        f"n_observations: {len(panel)}",
        f"n_folds: {config['n_folds']}",
        f"bootstrap_draws: {config['n_bootstrap']}",
        f"ate_estimate: {ate_row['estimate']:.6f}",
        f"ate_ci: [{ate_row['ci_lower']:.6f}, {ate_row['ci_upper']:.6f}]",
        f"att_estimate: {att_row['estimate']:.6f}",
        f"att_ci: [{att_row['ci_lower']:.6f}, {att_row['ci_upper']:.6f}]",
        f"treated_share: {panel['T'].mean():.4f}",
        f"mean_true_tau: {panel['true_tau'].mean():.6f}",
        f"highest_segment: {top_segment['segment']} ({top_segment['segment_ate']:.6f})",
        f"diagnostic_mean_fold_score: {diagnostics['mean_score'].mean():.6f}",
        "procedure: cross-fit nuisance models for outcome and treatment, residualize Y and T, compute orthogonal pseudo-effects, aggregate to ATE/ATT, and summarize heterogeneity by X1 quartiles.",
        f"claim_boundary: {CLAIM_BOUNDARY}",
    ]
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_smoke_manifest(
    smoke_path: Path,
    smoke_test: bool,
    artifacts: dict[str, Path],
    implementation_note: str,
) -> None:
    lines = [
        f"mode: {'SMOKE TEST' if smoke_test else 'FULL RUN'}",
        f"case_id: {CASE_ID}",
        f"summary_file: {artifacts['summary'].name}",
        f"ate_att_estimates: {artifacts['ate_att_estimates'].name}",
        f"cate_by_segment: {artifacts['cate_by_segment'].name}",
        f"orthogonal_score_diagnostics: {artifacts['orthogonal_score_diagnostics'].name}",
        f"cate_distribution_plot: {artifacts['cate_distribution'].name}",
        f"implementation_note: {implementation_note}",
        f"claim_boundary: {CLAIM_BOUNDARY}",
    ]
    smoke_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_dml_summary(
    summary_path: Path,
    implementation_note: str,
    estimates: pd.DataFrame,
    importances: pd.DataFrame,
) -> None:
    ate_row = estimates.loc[estimates["estimand"] == "ATE"].iloc[0]
    top_feature = importances.iloc[0] if not importances.empty else None
    lines = [
        f"case_id: {CASE_ID}",
        f"implementation_note: {implementation_note}",
        f"ate_estimate: {ate_row['estimate']:.6f}",
        f"ate_ci: [{ate_row['ci_lower']:.6f}, {ate_row['ci_upper']:.6f}]",
        "top_heterogeneity_feature: "
        + (f"{top_feature['feature']} ({float(top_feature['importance']):.6f})" if top_feature is not None else "none"),
    ]
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_case(smoke_test: bool = False) -> dict[str, str]:
    paths = resolve_paths()
    params = load_params(paths["params_file"])
    config = build_run_config(params, smoke_test)

    output_dir = paths["output_dir"]
    ate_att_estimates_path = output_dir / "ate_att_estimates.csv"
    cate_by_segment_path = output_dir / "cate_by_segment.csv"
    orthogonal_score_diagnostics_path = output_dir / "orthogonal_score_diagnostics.csv"
    cate_distribution_path = output_dir / "cate_distribution.png"
    dml_summary_path = output_dir / "dml_summary.txt"
    causal_forest_importances_path = output_dir / "causal_forest_importances.csv"
    ate_confidence_intervals_path = output_dir / "ate_confidence_intervals.csv"
    summary_path = output_dir / "summary.txt"
    smoke_path = output_dir / "smoke_test.txt"

    panel = simulate_policy_panel(
        seed=config["seed"],
        n_units=config["n_units"],
        n_periods=config["n_periods"],
    )
    try:
        estimates, diagnostics, score_frame, importances, implementation_note = econml_double_ml_estimate(
            panel=panel,
            n_bootstrap=config["n_bootstrap"],
            seed=config["seed"],
        )
    except (ImportError, ValueError, TypeError, RuntimeError) as exc:
        estimates, diagnostics, score_frame = manual_double_ml_estimate(
            panel=panel,
            n_folds=config["n_folds"],
            n_bootstrap=config["n_bootstrap"],
            seed=config["seed"],
        )
        importances = build_fallback_importances(score_frame)
        implementation_note = f"sklearn manual Double ML fallback; EconML unavailable or failed: {type(exc).__name__}: {exc}"

    segment_table = build_segment_table(
        score_frame=score_frame,
        n_bootstrap=max(100, config["n_bootstrap"] // 2),
        seed=config["seed"] + 303,
    )

    estimates.to_csv(ate_att_estimates_path, index=False)
    estimates.to_csv(ate_confidence_intervals_path, index=False)
    segment_table.to_csv(cate_by_segment_path, index=False)
    diagnostics.to_csv(orthogonal_score_diagnostics_path, index=False)
    importances.to_csv(causal_forest_importances_path, index=False)
    save_cate_histogram(score_frame, cate_distribution_path)
    write_summary(
        summary_path,
        config,
        panel,
        estimates,
        segment_table,
        diagnostics,
        smoke_test,
        implementation_note,
    )
    write_dml_summary(dml_summary_path, implementation_note, estimates, importances)

    artifacts = {
        "summary": summary_path,
        "ate_att_estimates": ate_att_estimates_path,
        "ate_confidence_intervals": ate_confidence_intervals_path,
        "cate_by_segment": cate_by_segment_path,
        "orthogonal_score_diagnostics": orthogonal_score_diagnostics_path,
        "causal_forest_importances": causal_forest_importances_path,
        "dml_summary": dml_summary_path,
        "cate_distribution": cate_distribution_path,
    }
    write_smoke_manifest(smoke_path, smoke_test, artifacts, implementation_note)
    return {key: str(value) for key, value in {**artifacts, "smoke": smoke_path}.items()}


def read_summary_text() -> str:
    return (resolve_paths()["output_dir"] / "summary.txt").read_text(encoding="utf-8")


def print_notebook_summary() -> None:
    print(read_summary_text())


if __name__ == "__main__":
    smoke_test = parse_args()
    outputs = run_case(smoke_test=smoke_test)
    print(f"Generated: {outputs['summary']}")
