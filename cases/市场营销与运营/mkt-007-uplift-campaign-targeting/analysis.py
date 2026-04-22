from __future__ import annotations

# pyright: reportMissingTypeStubs=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportExplicitAny=false, reportMissingTypeArgument=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportAny=false, reportUnusedCallResult=false, reportOperatorIssue=false, reportAttributeAccessIssue=false

import argparse
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
import yaml
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


CASE_ID = "mkt-007-uplift-campaign-targeting"
CASE_TITLE = "精准营销中的增量响应建模：客户 uplift 分析"
CLAIM_BOUNDARY = "演示增量响应预测逻辑，区分预测响应与预测增量响应"
GITHUB_REFERENCE_NOTE = (
    "The two-model uplift decomposition follows patterns visible in "
    "maks-sh/scikit-uplift and criteo-research/large-scale-ITE-UM-benchmark: "
    "fit separate treatment/control response models and score uplift as mu1 - mu0."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulated uplift modeling case for campaign targeting.")
    _ = parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run the same pipeline with a smaller sample while generating all required artifacts.",
    )
    return parser.parse_args()


def resolve_paths() -> dict[str, Path]:
    case_dir = Path(__file__).resolve().parent
    paths = {
        "case_dir": case_dir,
        "data_dir": case_dir / "data",
        "output_dir": case_dir / "outputs",
        "params_file": case_dir / "params.yaml",
    }
    paths["data_dir"].mkdir(parents=True, exist_ok=True)
    paths["output_dir"].mkdir(parents=True, exist_ok=True)
    return paths


def load_params(params_file: Path) -> dict[str, Any]:
    params = yaml.safe_load(params_file.read_text(encoding="utf-8")) or {}
    if not isinstance(params, dict):
        raise ValueError("params.yaml must parse to a mapping")
    return params


def build_run_config(params: dict[str, Any], smoke_test: bool) -> dict[str, Any]:
    config = dict(cast(dict[str, Any], params.get("simulation", {})))
    if smoke_test:
        overrides = cast(dict[str, Any], params.get("smoke_test", {}))
        config.update(overrides)
    return config


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def generate_customer_data(seed: int, config: dict[str, Any]) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n_customers = int(config["n_customers"])
    treatment_rate = float(config["treatment_rate"])

    age = rng.integers(20, 68, size=n_customers)
    income_k = np.clip(rng.normal(85, 28, size=n_customers), 20, 220)
    prior_orders = rng.poisson(2.8, size=n_customers)
    engagement_score = rng.beta(2.2, 1.8, size=n_customers)
    loyalty_index = np.clip(0.18 * prior_orders + 0.75 * engagement_score + rng.normal(0, 0.25, size=n_customers), 0, 5)
    price_sensitivity = np.clip(rng.beta(2.0, 2.6, size=n_customers) + rng.normal(0, 0.08, size=n_customers), 0, 1)
    new_customer = (prior_orders == 0).astype(int)
    weeks_since_purchase = np.clip(rng.normal(9, 5, size=n_customers), 0, 30)
    region_score = rng.normal(0, 1, size=n_customers)

    income_scaled = (income_k - income_k.mean()) / income_k.std()
    age_scaled = (age - age.mean()) / age.std()
    weeks_scaled = (weeks_since_purchase - weeks_since_purchase.mean()) / weeks_since_purchase.std()
    prior_orders_log = np.log1p(prior_orders)

    baseline_logit = (
        -2.45
        + 1.65 * engagement_score
        + 0.55 * prior_orders_log
        + 0.48 * loyalty_index
        + 0.10 * income_scaled
        - 0.30 * price_sensitivity
        - 0.35 * weeks_scaled
        + 0.08 * age_scaled
        + 0.12 * region_score
    )

    uplift_shift = (
        -0.18
        + 0.95 * price_sensitivity
        + 0.70 * new_customer
        - 0.55 * loyalty_index
        - 0.45 * engagement_score
        - 0.20 * income_scaled
        + 0.18 * weeks_scaled
        + 0.12 * region_score
    )

    p_control = np.clip(sigmoid(baseline_logit), 0.01, 0.95)
    p_treat = np.clip(sigmoid(baseline_logit + uplift_shift), 0.01, 0.95)
    true_uplift = p_treat - p_control

    treatment = rng.binomial(1, treatment_rate, size=n_customers)
    realized_probability = np.where(treatment == 1, p_treat, p_control)
    response = rng.binomial(1, realized_probability, size=n_customers)

    data = pd.DataFrame(
        {
            "customer_id": [f"C{i:05d}" for i in range(n_customers)],
            "age": age,
            "income_k": income_k,
            "prior_orders": prior_orders,
            "engagement_score": engagement_score,
            "loyalty_index": loyalty_index,
            "price_sensitivity": price_sensitivity,
            "new_customer": new_customer,
            "weeks_since_purchase": weeks_since_purchase,
            "region_score": region_score,
            "treatment": treatment,
            "response": response,
            "p_control": p_control,
            "p_treat": p_treat,
            "true_uplift": true_uplift,
        }
    )
    return data


def split_data(data: pd.DataFrame, seed: int, test_size: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    stratify_label = data["treatment"].astype(str) + "_" + data["response"].astype(str)
    train_df, test_df = train_test_split(
        data,
        test_size=test_size,
        random_state=seed,
        stratify=stratify_label,
    )
    return train_df.reset_index(drop=True), test_df.reset_index(drop=True)


def feature_columns() -> list[str]:
    return [
        "age",
        "income_k",
        "prior_orders",
        "engagement_score",
        "loyalty_index",
        "price_sensitivity",
        "new_customer",
        "weeks_since_purchase",
        "region_score",
    ]


def make_classifier(max_iter: int) -> Pipeline:
    return Pipeline(
        [
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(max_iter=max_iter, solver="lbfgs")),
        ]
    )


def score_uplift(train_df: pd.DataFrame, test_df: pd.DataFrame, max_iter: int) -> pd.DataFrame:
    columns = feature_columns()
    treated_model = make_classifier(max_iter=max_iter)
    control_model = make_classifier(max_iter=max_iter)

    treated_train = train_df.loc[train_df["treatment"] == 1]
    control_train = train_df.loc[train_df["treatment"] == 0]

    treated_model.fit(treated_train[columns], treated_train["response"])
    control_model.fit(control_train[columns], control_train["response"])

    scored = test_df.copy()
    scored["mu1_hat"] = treated_model.predict_proba(test_df[columns])[:, 1]
    scored["mu0_hat"] = control_model.predict_proba(test_df[columns])[:, 1]
    scored["uplift_hat"] = scored["mu1_hat"] - scored["mu0_hat"]
    scored["response_hat"] = scored["mu1_hat"]
    return scored.sort_values("uplift_hat", ascending=False).reset_index(drop=True)


def build_uplift_ranking(scored: pd.DataFrame, n_bins: int = 10) -> pd.DataFrame:
    ranked = scored.sort_values("uplift_hat", ascending=False).reset_index(drop=True).copy()
    ranked["rank_decile"] = pd.qcut(ranked.index + 1, q=n_bins, labels=False) + 1

    rows: list[dict[str, Any]] = []
    for decile in sorted(ranked["rank_decile"].unique()):
        subset = ranked.loc[ranked["rank_decile"] == decile].copy()
        treated_subset = subset.loc[subset["treatment"] == 1, "response"]
        control_subset = subset.loc[subset["treatment"] == 0, "response"]
        observed_incremental = float(treated_subset.mean() - control_subset.mean()) if len(treated_subset) and len(control_subset) else np.nan

        rows.append(
            {
                "rank_decile": int(decile),
                "customers": int(len(subset)),
                "avg_predicted_uplift": float(subset["uplift_hat"].mean()),
                "avg_true_uplift": float(subset["true_uplift"].mean()),
                "avg_predicted_response": float(subset["response_hat"].mean()),
                "avg_control_response_probability": float(subset["p_control"].mean()),
                "avg_treated_response_probability": float(subset["p_treat"].mean()),
                "treated_share": float(subset["treatment"].mean()),
                "observed_treated_response": float(treated_subset.mean()) if len(treated_subset) else np.nan,
                "observed_control_response": float(control_subset.mean()) if len(control_subset) else np.nan,
                "observed_incremental_response": observed_incremental,
            }
        )

    return pd.DataFrame(rows)


def evaluate_policy(
    scored: pd.DataFrame,
    policy: str,
    score_column: str,
    share_grid: list[float],
    contact_cost: float,
    conversion_value: float,
    seed: int,
) -> pd.DataFrame:
    if policy == "random":
        ordered = scored.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    else:
        ordered = scored.sort_values(score_column, ascending=False).reset_index(drop=True)

    rows: list[dict[str, Any]] = []
    total = len(ordered)
    for share in share_grid:
        target_n = max(1, int(round(total * share)))
        selected = ordered.head(target_n).copy()
        expected_incremental_conversions = float(selected["true_uplift"].sum())
        expected_profit = expected_incremental_conversions * conversion_value - target_n * contact_cost
        treated_subset = selected.loc[selected["treatment"] == 1, "response"]
        control_subset = selected.loc[selected["treatment"] == 0, "response"]
        observed_incremental = float(treated_subset.mean() - control_subset.mean()) if len(treated_subset) and len(control_subset) else np.nan

        rows.append(
            {
                "policy": policy,
                "target_share": float(share),
                "targeted_customers": int(target_n),
                "avg_selected_true_uplift": float(selected["true_uplift"].mean()),
                "avg_selected_predicted_uplift": float(selected["uplift_hat"].mean()),
                "avg_selected_predicted_response": float(selected["response_hat"].mean()),
                "expected_incremental_conversions": expected_incremental_conversions,
                "expected_incremental_revenue": expected_incremental_conversions * conversion_value,
                "expected_profit": expected_profit,
                "expected_roi_per_customer": expected_profit / target_n,
                "observed_incremental_response": observed_incremental,
            }
        )
    return pd.DataFrame(rows)


def build_roi_comparison(scored: pd.DataFrame, config: dict[str, Any], seed: int) -> pd.DataFrame:
    share_grid = [float(x) for x in cast(list[Any], config["target_share_grid"])]
    contact_cost = float(config["contact_cost"])
    conversion_value = float(config["conversion_value"])

    frames = [
        evaluate_policy(scored, "uplift", "uplift_hat", share_grid, contact_cost, conversion_value, seed),
        evaluate_policy(scored, "response", "response_hat", share_grid, contact_cost, conversion_value, seed),
        evaluate_policy(scored, "random", "uplift_hat", share_grid, contact_cost, conversion_value, seed),
    ]
    return pd.concat(frames, ignore_index=True)


def build_top_customers(scored: pd.DataFrame, top_n: int) -> pd.DataFrame:
    columns = [
        "customer_id",
        "uplift_hat",
        "response_hat",
        "mu0_hat",
        "mu1_hat",
        "true_uplift",
        "p_control",
        "p_treat",
        "engagement_score",
        "loyalty_index",
        "price_sensitivity",
        "new_customer",
        "prior_orders",
    ]
    return scored.sort_values("uplift_hat", ascending=False).head(top_n).loc[:, columns].reset_index(drop=True)


def write_summary(
    summary_path: Path,
    data: pd.DataFrame,
    scored: pd.DataFrame,
    ranking: pd.DataFrame,
    roi: pd.DataFrame,
    smoke_test: bool,
) -> None:
    top_uplift = ranking.loc[ranking["rank_decile"] == 1].iloc[0]
    uplift_20 = roi.loc[(roi["policy"] == "uplift") & (roi["target_share"] == 0.2)].iloc[0]
    response_20 = roi.loc[(roi["policy"] == "response") & (roi["target_share"] == 0.2)].iloc[0]
    random_20 = roi.loc[(roi["policy"] == "random") & (roi["target_share"] == 0.2)].iloc[0]
    natural_top_response = scored.sort_values("response_hat", ascending=False).head(max(1, len(scored) // 5))

    summary = f"""case_id: {CASE_ID}
title: {CASE_TITLE}
mode: {'SMOKE TEST' if smoke_test else 'FULL RUN'}
observations: {len(data)}
evaluation_sample: {len(scored)}
average_true_uplift: {data['true_uplift'].mean():.4f}
top_decile_avg_predicted_uplift: {top_uplift['avg_predicted_uplift']:.4f}
top_decile_avg_true_uplift: {top_uplift['avg_true_uplift']:.4f}
top_response_segment_avg_true_uplift: {natural_top_response['true_uplift'].mean():.4f}

roi_at_20pct_uplift: {uplift_20['expected_profit']:.2f}
roi_at_20pct_response: {response_20['expected_profit']:.2f}
roi_at_20pct_random: {random_20['expected_profit']:.2f}

interpretation: 按 uplift 排序的投放优先寻找“被触达后才更会转化”的客户；按响应排序更容易挑中本来就会购买的自然高响应客户，因此业务增量价值通常更低。
github_reference_note: {GITHUB_REFERENCE_NOTE}
claim_boundary: {CLAIM_BOUNDARY}
"""
    _ = summary_path.write_text(summary, encoding="utf-8")


def write_smoke_manifest(smoke_path: Path, artifacts: dict[str, Path], smoke_test: bool) -> None:
    lines = [
        f"mode: {'SMOKE TEST' if smoke_test else 'FULL RUN'}",
        f"case_id: {CASE_ID}",
        f"summary: {artifacts['summary'].name}",
        f"data: {artifacts['data'].relative_to(artifacts['data'].parent.parent)}",
        f"uplift_ranking: {artifacts['uplift_ranking'].name}",
        f"roi_comparison: {artifacts['roi_comparison'].name}",
        f"top_customers: {artifacts['top_customers'].name}",
        f"claim_boundary: {CLAIM_BOUNDARY}",
    ]
    _ = smoke_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_summary_text() -> str:
    paths = resolve_paths()
    params = load_params(paths["params_file"])
    summary_path = paths["case_dir"] / str(cast(dict[str, Any], params["outputs"])["summary_file"])
    return summary_path.read_text(encoding="utf-8")


def print_notebook_summary() -> None:
    print(read_summary_text())


def load_result_tables() -> dict[str, pd.DataFrame]:
    paths = resolve_paths()
    params = load_params(paths["params_file"])
    outputs = cast(dict[str, Any], params["outputs"])
    return {
        "uplift_ranking": pd.read_csv(paths["case_dir"] / str(outputs["uplift_ranking_file"])),
        "roi_comparison": pd.read_csv(paths["case_dir"] / str(outputs["roi_comparison_file"])),
        "top_customers": pd.read_csv(paths["case_dir"] / str(outputs["top_customers_file"])),
    }


def run_case(smoke_test: bool = False) -> dict[str, str]:
    paths = resolve_paths()
    params = load_params(paths["params_file"])
    outputs = cast(dict[str, Any], params["outputs"])
    seed = int(params["seed"])
    config = build_run_config(params, smoke_test)

    data_path = paths["case_dir"] / str(outputs["data_file"])
    summary_path = paths["case_dir"] / str(outputs["summary_file"])
    smoke_path = paths["case_dir"] / str(outputs["smoke_file"])
    ranking_path = paths["case_dir"] / str(outputs["uplift_ranking_file"])
    roi_path = paths["case_dir"] / str(outputs["roi_comparison_file"])
    top_customers_path = paths["case_dir"] / str(outputs["top_customers_file"])

    data = generate_customer_data(seed=seed, config=config)
    train_df, test_df = split_data(data, seed=seed, test_size=float(config["test_size"]))
    scored = score_uplift(train_df, test_df, max_iter=int(config["logistic_max_iter"]))
    ranking = build_uplift_ranking(scored)
    roi = build_roi_comparison(scored, config=config, seed=seed)
    top_customers = build_top_customers(scored, top_n=int(config["top_customer_count"]))

    data.to_csv(data_path, index=False)
    ranking.to_csv(ranking_path, index=False)
    roi.to_csv(roi_path, index=False)
    top_customers.to_csv(top_customers_path, index=False)
    write_summary(summary_path, data, scored, ranking, roi, smoke_test)

    artifacts = {
        "summary": summary_path,
        "data": data_path,
        "uplift_ranking": ranking_path,
        "roi_comparison": roi_path,
        "top_customers": top_customers_path,
    }
    write_smoke_manifest(smoke_path, artifacts, smoke_test)
    return {key: str(value) for key, value in {**artifacts, "smoke": smoke_path}.items()}


if __name__ == "__main__":
    args = parse_args()
    produced = run_case(smoke_test=bool(args.smoke_test))
    print(f"Generated summary: {produced['summary']}")
