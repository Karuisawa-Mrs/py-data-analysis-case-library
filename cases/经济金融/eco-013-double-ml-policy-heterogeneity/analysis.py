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
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.model_selection import KFold


CASE_ID = "eco-013-double-ml-policy-heterogeneity"
CASE_TITLE = "政策效果的异质性分析：双重机器学习与因果森林"
CLAIM_BOUNDARY = "该案例演示因果机器学习方法，不替代真实政策评估的严谨识别设计。"

FloatArray = NDArray[np.float64]


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
    feature_columns = ["X1", "X2", "X3", "W1", "W2", "W3", "W4", "post_period", "period"]
    features = panel.loc[:, feature_columns].copy()
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
) -> None:
    ate_row = estimates.loc[estimates["estimand"] == "ATE"].iloc[0]
    att_row = estimates.loc[estimates["estimand"] == "ATT"].iloc[0]
    top_segment = segment_table.sort_values("segment_ate", ascending=False).iloc[0]

    lines = [
        f"case_id: {CASE_ID}",
        f"title: {CASE_TITLE}",
        f"mode: {'SMOKE TEST' if smoke_test else 'FULL RUN'}",
        f"fallback_note: sklearn-only manual Double ML fallback; see best-practice-roadmap.md for the EconML migration plan.",
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


def write_smoke_manifest(smoke_path: Path, smoke_test: bool, artifacts: dict[str, Path]) -> None:
    lines = [
        f"mode: {'SMOKE TEST' if smoke_test else 'FULL RUN'}",
        f"case_id: {CASE_ID}",
        f"summary_file: {artifacts['summary'].name}",
        f"ate_att_estimates: {artifacts['ate_att_estimates'].name}",
        f"cate_by_segment: {artifacts['cate_by_segment'].name}",
        f"orthogonal_score_diagnostics: {artifacts['orthogonal_score_diagnostics'].name}",
        f"cate_distribution_plot: {artifacts['cate_distribution'].name}",
        "fallback_note: sklearn-only manual Double ML implementation.",
        f"claim_boundary: {CLAIM_BOUNDARY}",
    ]
    smoke_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_case(smoke_test: bool = False) -> dict[str, str]:
    paths = resolve_paths()
    params = load_params(paths["params_file"])
    config = build_run_config(params, smoke_test)

    output_dir = paths["output_dir"]
    ate_att_estimates_path = output_dir / "ate_att_estimates.csv"
    cate_by_segment_path = output_dir / "cate_by_segment.csv"
    orthogonal_score_diagnostics_path = output_dir / "orthogonal_score_diagnostics.csv"
    cate_distribution_path = output_dir / "cate_distribution.png"
    summary_path = output_dir / "summary.txt"
    smoke_path = output_dir / "smoke_test.txt"

    panel = simulate_policy_panel(
        seed=config["seed"],
        n_units=config["n_units"],
        n_periods=config["n_periods"],
    )
    estimates, diagnostics, score_frame = manual_double_ml_estimate(
        panel=panel,
        n_folds=config["n_folds"],
        n_bootstrap=config["n_bootstrap"],
        seed=config["seed"],
    )
    segment_table = build_segment_table(
        score_frame=score_frame,
        n_bootstrap=max(100, config["n_bootstrap"] // 2),
        seed=config["seed"] + 303,
    )

    estimates.to_csv(ate_att_estimates_path, index=False)
    segment_table.to_csv(cate_by_segment_path, index=False)
    diagnostics.to_csv(orthogonal_score_diagnostics_path, index=False)
    save_cate_histogram(score_frame, cate_distribution_path)
    write_summary(summary_path, config, panel, estimates, segment_table, diagnostics, smoke_test)

    artifacts = {
        "summary": summary_path,
        "ate_att_estimates": ate_att_estimates_path,
        "cate_by_segment": cate_by_segment_path,
        "orthogonal_score_diagnostics": orthogonal_score_diagnostics_path,
        "cate_distribution": cate_distribution_path,
    }
    write_smoke_manifest(smoke_path, smoke_test, artifacts)
    return {key: str(value) for key, value in {**artifacts, "smoke": smoke_path}.items()}


def read_summary_text() -> str:
    return (resolve_paths()["output_dir"] / "summary.txt").read_text(encoding="utf-8")


def print_notebook_summary() -> None:
    print(read_summary_text())


if __name__ == "__main__":
    smoke_test = parse_args()
    outputs = run_case(smoke_test=smoke_test)
    print(f"Generated: {outputs['summary']}")
