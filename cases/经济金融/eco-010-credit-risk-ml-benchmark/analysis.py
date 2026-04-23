from __future__ import annotations

import argparse
from pathlib import Path
from typing import cast

import matplotlib
import numpy as np
import pandas as pd
import yaml
from numpy.typing import NDArray
from sklearn.calibration import calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    brier_score_loss,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

matplotlib.use("Agg")

import matplotlib.pyplot as plt


CASE_ID = "eco-010-credit-risk-ml-benchmark"
CASE_TITLE = "信用违约风险基准：逻辑回归与梯度提升树对比"
CLAIM_BOUNDARY = "该案例演示分类模型对比与校准评估方法，不替代真实银行信贷审批决策。"

EXPECTED_ARTIFACTS = {
    "summary": "summary.txt",
    "smoke": "smoke_test.txt",
    "metrics": "model_metrics.csv",
    "calibration": "calibration_curve.png",
    "distribution": "score_distribution.png",
    "feature_importance": "feature_importance.csv",
}

ScoreArray = NDArray[np.float64]
Params = dict[str, object]


def require_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str, float)):
        raise ValueError(f"{field_name} must be convertible to int")
    return int(value)


def parse_args() -> bool:
    parser = argparse.ArgumentParser(description="Simulated credit risk benchmark analysis.")
    _ = parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run the full pipeline on a reduced sample while generating all required artifacts.",
    )
    args = parser.parse_args()
    smoke_test_value = getattr(args, "smoke_test", False)
    return smoke_test_value if isinstance(smoke_test_value, bool) else False


def resolve_paths() -> dict[str, Path]:
    case_dir = Path(__file__).resolve().parent
    paths = {
        "case_dir": case_dir,
        "data_dir": case_dir / "data",
        "params_file": case_dir / "params.yaml",
    }
    paths["data_dir"].mkdir(parents=True, exist_ok=True)
    return paths


def load_params(params_file: Path) -> Params:
    params = cast(object, yaml.safe_load(params_file.read_text(encoding="utf-8")) or {})
    if not isinstance(params, dict):
        raise ValueError("params.yaml must parse to a mapping")
    if "seed" not in params:
        raise ValueError("params.yaml must define seed")
    return cast(Params, params)


def build_run_config(params: Params, smoke_test: bool) -> dict[str, str | int | float]:
    output_dir_name = str(params.get("output_dir", "outputs"))
    config = {
        "seed": require_int(params["seed"], "seed"),
        "n_samples": 200 if smoke_test else 2000,
        "test_size": 0.3,
        "output_dir_name": output_dir_name,
        "data_file_name": "simulated_credit_risk_data.csv",
    }
    return config


def generate_credit_data(seed: int, n_samples: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    age = np.clip(rng.normal(loc=41.0, scale=11.0, size=n_samples), 21, 72)
    income = np.clip(rng.lognormal(mean=10.75, sigma=0.45, size=n_samples), 20_000, 250_000)
    credit_score = np.clip(rng.normal(loc=660.0, scale=55.0, size=n_samples), 470, 830)
    debt_to_income = np.clip(rng.beta(a=2.2, b=3.6, size=n_samples), 0.03, 0.92)
    employment_years = np.clip(age - 21 + rng.normal(0.0, 4.0, size=n_samples), 0, 40)
    loan_amount = np.clip(income * rng.uniform(0.12, 0.6, size=n_samples), 3_000, 90_000)
    loan_to_income = np.clip(loan_amount / income, 0.05, 1.2)
    utilization = np.clip(
        0.58 * debt_to_income + 0.25 * loan_to_income + rng.normal(0.10, 0.12, size=n_samples),
        0.01,
        0.99,
    )
    delinquencies_12m = rng.poisson(lam=np.clip(0.25 + 2.8 * utilization, 0.1, 3.8), size=n_samples)
    inquiries_6m = rng.poisson(lam=np.clip(1.2 + 2.0 * loan_to_income, 0.4, 5.5), size=n_samples)
    savings_buffer = np.clip(income * rng.uniform(0.03, 0.30, size=n_samples), 500, 60_000)
    housing_status = rng.choice(
        ["rent", "mortgage", "own"],
        size=n_samples,
        p=[0.43, 0.39, 0.18],
    )
    purpose = rng.choice(
        ["working_capital", "debt_consolidation", "home_improvement", "consumer"],
        size=n_samples,
        p=[0.26, 0.34, 0.14, 0.26],
    )

    housing_risk = np.select(
        [housing_status == "rent", housing_status == "mortgage", housing_status == "own"],
        [0.32, 0.10, -0.08],
        default=0.0,
    )
    purpose_risk = np.select(
        [
            purpose == "debt_consolidation",
            purpose == "consumer",
            purpose == "working_capital",
            purpose == "home_improvement",
        ],
        [0.30, 0.18, 0.10, -0.05],
        default=0.0,
    )

    score = (
        -3.55
        + 3.2 * debt_to_income
        + 1.55 * utilization
        + 0.95 * loan_to_income
        + 0.30 * np.log1p(delinquencies_12m)
        + 0.16 * np.log1p(inquiries_6m)
        - 0.010 * (credit_score - 660.0)
        - 0.000010 * (income - 70_000.0)
        - 0.035 * employment_years
        - 0.000012 * savings_buffer
        + 0.008 * (38.0 - age)
        + housing_risk
        + purpose_risk
        + rng.normal(0.0, 0.42, size=n_samples)
    )
    default_probability = 1.0 / (1.0 + np.exp(-score))
    default_flag = rng.binomial(1, default_probability, size=n_samples)

    dataset = pd.DataFrame(
        {
            "age": age.round(0).astype(int),
            "annual_income": income.round(2),
            "credit_score": credit_score.round(0).astype(int),
            "debt_to_income": debt_to_income.round(4),
            "employment_years": employment_years.round(2),
            "loan_amount": loan_amount.round(2),
            "loan_to_income": loan_to_income.round(4),
            "credit_utilization": utilization.round(4),
            "delinquencies_12m": delinquencies_12m.astype(int),
            "inquiries_6m": inquiries_6m.astype(int),
            "savings_buffer": savings_buffer.round(2),
            "housing_status": housing_status,
            "loan_purpose": purpose,
            "default_probability": default_probability.round(6),
            "default_flag": default_flag.astype(int),
        }
    )
    return dataset


def prepare_feature_lists(dataset: pd.DataFrame) -> tuple[list[str], list[str]]:
    feature_columns = [str(column) for column in dataset.columns if column not in {"default_flag", "default_probability"}]
    categorical_features = [
        column for column in feature_columns if pd.api.types.is_object_dtype(dataset[column])
    ]
    numeric_features = [column for column in feature_columns if column not in categorical_features]
    return numeric_features, categorical_features


def build_preprocessor(numeric_features: list[str], categorical_features: list[str]) -> ColumnTransformer:
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, numeric_features),
            ("categorical", categorical_pipeline, categorical_features),
        ]
    )


def fit_models(
    train_features: pd.DataFrame,
    train_target: pd.Series,
    numeric_features: list[str],
    categorical_features: list[str],
    seed: int,
) -> dict[str, Pipeline]:
    logistic_pipeline = Pipeline(
        steps=[
            ("preprocessor", build_preprocessor(numeric_features, categorical_features)),
            (
                "model",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    solver="lbfgs",
                ),
            ),
        ]
    )
    gradient_boosting_pipeline = Pipeline(
        steps=[
            ("preprocessor", build_preprocessor(numeric_features, categorical_features)),
            (
                "model",
                GradientBoostingClassifier(
                    learning_rate=0.05,
                    max_depth=3,
                    min_samples_leaf=10,
                    n_estimators=160,
                    subsample=0.9,
                    random_state=seed,
                ),
            ),
        ]
    )

    models = {
        "logistic_regression": logistic_pipeline,
        "gradient_boosting": gradient_boosting_pipeline,
    }
    for pipeline in models.values():
        _ = pipeline.fit(train_features, train_target)
    return models


def binary_classification_metrics(target: pd.Series, prediction: NDArray[np.int_]) -> tuple[float, float, float, float]:
    target_array = target.to_numpy(dtype=int)
    true_positive = int(np.sum((target_array == 1) & (prediction == 1)))
    true_negative = int(np.sum((target_array == 0) & (prediction == 0)))
    false_positive = int(np.sum((target_array == 0) & (prediction == 1)))
    false_negative = int(np.sum((target_array == 1) & (prediction == 0)))
    total = true_positive + true_negative + false_positive + false_negative

    accuracy = (true_positive + true_negative) / total if total else 0.0
    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) else 0.0
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return accuracy, precision, recall, f1


def evaluate_models(
    models: dict[str, Pipeline],
    test_features: pd.DataFrame,
    test_target: pd.Series,
) -> tuple[pd.DataFrame, dict[str, ScoreArray]]:
    metrics_rows: list[dict[str, float | str]] = []
    predicted_scores: dict[str, ScoreArray] = {}

    for model_name, pipeline in models.items():
        score = cast(ScoreArray, pipeline.predict_proba(test_features)[:, 1])
        prediction = cast(NDArray[np.int_], (score >= 0.5).astype(int))
        accuracy, precision, recall, f1 = binary_classification_metrics(test_target, prediction)
        predicted_scores[model_name] = score
        metrics_rows.append(
            {
                "model": model_name,
                "accuracy": float(accuracy),
                "precision": float(precision),
                "recall": float(recall),
                "f1": float(f1),
                "roc_auc": float(roc_auc_score(test_target, score)),
                "brier_score": float(brier_score_loss(test_target, score)),
            }
        )

    metrics_frame = pd.DataFrame(metrics_rows).sort_values("roc_auc", ascending=False).reset_index(drop=True)
    return metrics_frame, predicted_scores


def get_transformed_feature_names(
    preprocessor: ColumnTransformer,
    numeric_features: list[str],
    categorical_features: list[str],
) -> list[str]:
    feature_names: list[str] = list(numeric_features)
    if categorical_features:
        categorical_transformer = cast(Pipeline, preprocessor.named_transformers_["categorical"])
        onehot = cast(OneHotEncoder, categorical_transformer.named_steps["onehot"])
        categorical_names = list(onehot.get_feature_names_out(categorical_features))
        feature_names.extend(categorical_names)
    return feature_names


def build_feature_importance_table(
    models: dict[str, Pipeline],
    numeric_features: list[str],
    categorical_features: list[str],
) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []

    for model_name, pipeline in models.items():
        preprocessor = cast(ColumnTransformer, pipeline.named_steps["preprocessor"])
        feature_names = get_transformed_feature_names(preprocessor, numeric_features, categorical_features)

        if model_name == "logistic_regression":
            model = cast(LogisticRegression, pipeline.named_steps["model"])
            coefficients = cast(ScoreArray, model.coef_[0])
            importance = cast(ScoreArray, np.abs(coefficients))
            signed_values = coefficients
        else:
            model = cast(GradientBoostingClassifier, pipeline.named_steps["model"])
            importance = cast(ScoreArray, model.feature_importances_)
            signed_values = cast(ScoreArray, model.feature_importances_)

        ranking = np.argsort(importance)[::-1]
        for rank, position in enumerate(ranking, start=1):
            idx = int(position)
            rows.append(
                {
                    "model": model_name,
                    "rank": rank,
                    "feature": feature_names[idx],
                    "importance": float(importance[idx]),
                    "signed_effect": float(signed_values[idx]),
                }
            )

    importance_table = pd.DataFrame(rows)
    return importance_table.sort_values(["model", "rank"]).reset_index(drop=True)


def save_calibration_plot(
    target: pd.Series,
    predicted_scores: dict[str, ScoreArray],
    figure_path: Path,
) -> None:
    fig, axis = plt.subplots(figsize=(7, 5), constrained_layout=True)
    colors = {
        "logistic_regression": "#1f77b4",
        "gradient_boosting": "#d62728",
    }

    for model_name, score in predicted_scores.items():
        frac_positive, mean_predicted = calibration_curve(target, score, n_bins=10, strategy="quantile")
        _ = axis.plot(
            mean_predicted,
            frac_positive,
            marker="o",
            linewidth=2,
            label=model_name,
            color=colors[model_name],
        )

    _ = axis.plot([0, 1], [0, 1], linestyle="--", color="black", linewidth=1.2, label="perfect_calibration")
    _ = axis.set_title("Calibration curve")
    _ = axis.set_xlabel("Mean predicted probability")
    _ = axis.set_ylabel("Observed default rate")
    _ = axis.legend(frameon=False)
    axis.grid(alpha=0.2)
    fig.savefig(figure_path, dpi=150)
    plt.close(fig)


def save_score_distribution_plot(predicted_scores: dict[str, ScoreArray], figure_path: Path) -> None:
    fig, axis = plt.subplots(figsize=(7, 5), constrained_layout=True)
    bins = np.linspace(0.0, 1.0, 20).tolist()
    colors = {
        "logistic_regression": "#1f77b4",
        "gradient_boosting": "#d62728",
    }

    for model_name, score in predicted_scores.items():
        _ = axis.hist(
            score,
            bins=bins,
            alpha=0.45,
            density=True,
            label=model_name,
            color=colors[model_name],
            edgecolor="white",
        )

    _ = axis.set_title("Predicted default score distribution")
    _ = axis.set_xlabel("Predicted probability of default")
    _ = axis.set_ylabel("Density")
    _ = axis.legend(frameon=False)
    axis.grid(alpha=0.2)
    fig.savefig(figure_path, dpi=150)
    plt.close(fig)


def write_summary(
    summary_path: Path,
    metrics_frame: pd.DataFrame,
    dataset: pd.DataFrame,
    smoke_test: bool,
    seed: int,
    data_path: Path,
) -> None:
    best_row = metrics_frame.iloc[0]
    summary = f"""case_id: {CASE_ID}
title: {CASE_TITLE}
mode: {'SMOKE TEST' if smoke_test else 'FULL RUN'}
seed_from_params: {seed}
observations: {len(dataset)}
default_rate: {dataset['default_flag'].mean():.4f}
data_file: {data_path.name}

best_model_by_roc_auc: {best_row['model']}
best_model_roc_auc: {best_row['roc_auc']:.4f}
best_model_f1: {best_row['f1']:.4f}
best_model_brier_score: {best_row['brier_score']:.4f}

model_comparison:
{metrics_frame.to_string(index=False)}

interpretation: This benchmark compares a linear baseline and a nonlinear tree ensemble on simulated credit default data with class imbalance.
claim_boundary: {CLAIM_BOUNDARY}
"""
    _ = summary_path.write_text(summary, encoding="utf-8")


def write_smoke_manifest(smoke_path: Path, artifacts: dict[str, Path], smoke_test: bool) -> None:
    lines = [
        f"mode: {'SMOKE TEST' if smoke_test else 'FULL RUN'}",
        f"case_id: {CASE_ID}",
        f"summary: {artifacts['summary'].name}",
        f"metrics: {artifacts['metrics'].name}",
        f"calibration_curve: {artifacts['calibration'].name}",
        f"score_distribution: {artifacts['distribution'].name}",
        f"feature_importance: {artifacts['feature_importance'].name}",
        f"simulated_data: {artifacts['data'].relative_to(artifacts['data'].parent.parent)}",
        f"claim_boundary: {CLAIM_BOUNDARY}",
    ]
    _ = smoke_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_case(smoke_test: bool = False) -> dict[str, str]:
    paths = resolve_paths()
    params = load_params(paths["params_file"])
    config = build_run_config(params, smoke_test)

    output_dir = paths["case_dir"] / str(config["output_dir_name"])
    output_dir.mkdir(parents=True, exist_ok=True)
    seed = int(config["seed"])

    data_path = paths["data_dir"] / str(config["data_file_name"])
    summary_path = output_dir / EXPECTED_ARTIFACTS["summary"]
    smoke_path = output_dir / EXPECTED_ARTIFACTS["smoke"]
    metrics_path = output_dir / EXPECTED_ARTIFACTS["metrics"]
    calibration_path = output_dir / EXPECTED_ARTIFACTS["calibration"]
    distribution_path = output_dir / EXPECTED_ARTIFACTS["distribution"]
    importance_path = output_dir / EXPECTED_ARTIFACTS["feature_importance"]

    dataset = generate_credit_data(seed=seed, n_samples=int(config["n_samples"]))
    dataset.to_csv(data_path, index=False)

    features = dataset.drop(columns=["default_flag", "default_probability"]).copy()
    target = cast(pd.Series, dataset["default_flag"].copy())
    numeric_features, categorical_features = prepare_feature_lists(dataset)

    split = train_test_split(
        features,
        target,
        test_size=float(config["test_size"]),
        random_state=seed,
        stratify=target,
    )
    train_features = cast(pd.DataFrame, split[0])
    test_features = cast(pd.DataFrame, split[1])
    train_target = cast(pd.Series, split[2])
    test_target = cast(pd.Series, split[3])

    models = fit_models(train_features, train_target, numeric_features, categorical_features, seed)
    metrics_frame, predicted_scores = evaluate_models(models, test_features, test_target)
    importance_table = build_feature_importance_table(models, numeric_features, categorical_features)

    metrics_frame.to_csv(metrics_path, index=False)
    importance_table.to_csv(importance_path, index=False)
    save_calibration_plot(test_target, predicted_scores, calibration_path)
    save_score_distribution_plot(predicted_scores, distribution_path)
    write_summary(summary_path, metrics_frame, dataset, smoke_test, seed, data_path)

    artifacts = {
        "summary": summary_path,
        "smoke": smoke_path,
        "metrics": metrics_path,
        "calibration": calibration_path,
        "distribution": distribution_path,
        "feature_importance": importance_path,
        "data": data_path,
    }
    write_smoke_manifest(smoke_path, artifacts, smoke_test)
    return {key: str(value) for key, value in artifacts.items()}


if __name__ == "__main__":
    smoke_test = parse_args()
    produced = run_case(smoke_test=smoke_test)
    print("Generated artifacts:")
    for label, path in produced.items():
        print(f"- {label}: {path}")
