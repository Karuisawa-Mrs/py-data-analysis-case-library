from __future__ import annotations

# pyright: reportMissingImports=false, reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportUnknownLambdaType=false, reportGeneralTypeIssues=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportExplicitAny=false, reportAny=false, reportUnusedCallResult=false

import argparse
import warnings
from dataclasses import dataclass
from pathlib import Path
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from statsmodels.formula.api import mixedlm
from statsmodels.regression.mixed_linear_model import MixedLMResultsWrapper
from statsmodels.tools.sm_exceptions import ConvergenceWarning


CASE_ID = "soc-016-multilevel-school-achievement"
CASE_TITLE = "学校情境与学生成绩：多层次线性模型分析"
DATA_MODE = "simulated"
REPLICATION_TYPE = "illustration"
CLAIM_BOUNDARY = "该案例演示多层次模型方法，不替代真实教育评估研究。"


@dataclass(frozen=True)
class CaseConfig:
    seed: int
    output_dir: str
    n_schools_full: int
    students_per_school_full: int
    n_schools_smoke: int
    students_per_school_smoke: int
    school_resource_mean: float
    school_resource_sd: float
    school_intercept_sd: float
    ses_slope_mean: float
    ses_slope_sd: float
    reading_noise_sd: float
    math_noise_sd: float


@dataclass(frozen=True)
class FitSummary:
    model_name: str
    result: MixedLMResultsWrapper | None
    converged: bool
    warnings_seen: tuple[str, ...]
    error_message: str | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Simulate students nested within schools and estimate null, random-intercept, "
            "and random-slope multilevel models using statsmodels MixedLM."
        )
    )
    _ = parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run a smaller but complete pipeline and emit all expected artifacts.",
    )
    return parser.parse_args()


def resolve_paths() -> dict[str, Path]:
    case_dir = Path(__file__).resolve().parent
    params_file = case_dir / "params.yaml"
    payload = yaml.safe_load(params_file.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("params.yaml must parse to a mapping")

    configured_output_dir = payload.get("output_dir", "outputs")
    output_dir = case_dir / str(configured_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    return {
        "case_dir": case_dir,
        "params_file": params_file,
        "output_dir": output_dir,
    }


def load_config(params_file: Path) -> CaseConfig:
    payload = yaml.safe_load(params_file.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("params.yaml must parse to a mapping")

    return CaseConfig(
        seed=int(payload["seed"]),
        output_dir=str(payload.get("output_dir", "outputs")),
        n_schools_full=int(payload.get("n_schools_full", 30)),
        students_per_school_full=int(payload.get("students_per_school_full", 25)),
        n_schools_smoke=int(payload.get("n_schools_smoke", 10)),
        students_per_school_smoke=int(payload.get("students_per_school_smoke", 15)),
        school_resource_mean=float(payload.get("school_resource_mean", 0.0)),
        school_resource_sd=float(payload.get("school_resource_sd", 1.0)),
        school_intercept_sd=float(payload.get("school_intercept_sd", 6.5)),
        ses_slope_mean=float(payload.get("ses_slope_mean", 4.2)),
        ses_slope_sd=float(payload.get("ses_slope_sd", 1.0)),
        reading_noise_sd=float(payload.get("reading_noise_sd", 6.0)),
        math_noise_sd=float(payload.get("math_noise_sd", 7.5)),
    )


def simulate_multilevel_data(config: CaseConfig, smoke_test: bool) -> pd.DataFrame:
    rng = np.random.default_rng(config.seed + (29 if smoke_test else 0))
    n_schools = config.n_schools_smoke if smoke_test else config.n_schools_full
    students_per_school = (
        config.students_per_school_smoke if smoke_test else config.students_per_school_full
    )
    school_ids = np.arange(1, n_schools + 1, dtype=int)

    school_resources = rng.normal(
        loc=config.school_resource_mean,
        scale=config.school_resource_sd,
        size=n_schools,
    )
    school_intercepts = rng.normal(0.0, config.school_intercept_sd, size=n_schools)
    school_ses_slopes = rng.normal(
        loc=config.ses_slope_mean,
        scale=config.ses_slope_sd,
        size=n_schools,
    )

    school_frame = pd.DataFrame(
        {
            "school_id": school_ids,
            "school_resources": school_resources,
            "school_intercept": school_intercepts,
            "school_ses_slope": school_ses_slopes,
        }
    )

    student_frame = school_frame.loc[school_frame.index.repeat(students_per_school)].reset_index(drop=True)
    student_count = len(student_frame)
    student_frame.insert(0, "student_id", np.arange(1, student_count + 1, dtype=int))

    ses = rng.normal(0.0, 1.0, size=student_count)
    latent_ability = (
        49.0
        + 2.3 * ses
        + 3.2 * student_frame["school_resources"].to_numpy(dtype=float)
        + student_frame["school_intercept"].to_numpy(dtype=float)
        + rng.normal(0.0, 4.0, size=student_count)
    )
    reading_score = np.clip(
        latent_ability + 5.5 + rng.normal(0.0, config.reading_noise_sd, size=student_count),
        0.0,
        100.0,
    )
    math_score = np.clip(
        22.0
        + 0.36 * reading_score
        + student_frame["school_resources"].to_numpy(dtype=float) * 2.6
        + student_frame["school_intercept"].to_numpy(dtype=float)
        + student_frame["school_ses_slope"].to_numpy(dtype=float) * ses
        + rng.normal(0.0, config.math_noise_sd, size=student_count),
        0.0,
        100.0,
    )

    student_frame["ses"] = ses
    student_frame["reading_score"] = reading_score
    student_frame["math_score"] = math_score

    ordered_columns = [
        "student_id",
        "school_id",
        "math_score",
        "reading_score",
        "ses",
        "school_resources",
    ]
    return student_frame[ordered_columns].copy()


def fit_mixed_model(
    *,
    model_name: str,
    formula: str,
    data: pd.DataFrame,
    re_formula: str,
) -> FitSummary:
    methods = ("lbfgs", "powell", "cg")
    warning_messages: list[str] = []
    last_error: str | None = None
    fallback_result: MixedLMResultsWrapper | None = None
    fallback_method: str | None = None
    fallback_warnings: tuple[str, ...] = ()

    for method in methods:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", category=ConvergenceWarning)
            warnings.simplefilter("always", category=RuntimeWarning)
            try:
                model = mixedlm(formula=formula, data=data, groups=data["school_id"], re_formula=re_formula)
                result = model.fit(reml=True, method=method, maxiter=500, disp=False)
            except (ValueError, np.linalg.LinAlgError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                warning_messages.extend(str(item.message) for item in caught)
                continue

        warning_messages.extend(str(item.message) for item in caught)
        if bool(getattr(result, "converged", False)):
            cov_re = np.asarray(result.cov_re, dtype=float)
            between_var = float(cov_re[0, 0]) if cov_re.size else float("nan")
            deduped_warnings = tuple(dict.fromkeys(warning_messages))
            if np.isfinite(between_var) and between_var > 1e-6:
                return FitSummary(
                    model_name=model_name,
                    result=result,
                    converged=True,
                    warnings_seen=deduped_warnings,
                    error_message=None,
                )
            if fallback_result is None:
                fallback_result = result
                fallback_method = method
                fallback_warnings = deduped_warnings
            last_error = f"Converged with near-zero random intercept variance using optimizer={method}"
            continue

        last_error = f"Model did not converge with optimizer={method}"

    if fallback_result is not None:
        return FitSummary(
            model_name=model_name,
            result=fallback_result,
            converged=True,
            warnings_seen=fallback_warnings,
            error_message=(
                f"Used fallback optimizer={fallback_method} with near-zero random intercept variance"
            ),
        )

    return FitSummary(
        model_name=model_name,
        result=None,
        converged=False,
        warnings_seen=tuple(dict.fromkeys(warning_messages)),
        error_message=last_error,
    )


def extract_fixed_effects(fits: list[FitSummary]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for fit in fits:
        if fit.result is None:
            rows.append(
                {
                    "model_name": fit.model_name,
                    "term": "model_status",
                    "coefficient": np.nan,
                    "std_error": np.nan,
                    "z_value": np.nan,
                    "p_value": np.nan,
                    "ci_lower_95": np.nan,
                    "ci_upper_95": np.nan,
                    "converged": fit.converged,
                    "notes": fit.error_message or "fit failed",
                }
            )
            continue

        confidence_intervals = fit.result.conf_int()
        p_values = fit.result.pvalues
        standard_errors = fit.result.bse_fe
        z_values = fit.result.fe_params / standard_errors
        for term, coefficient in fit.result.fe_params.items():
            rows.append(
                {
                    "model_name": fit.model_name,
                    "term": str(term),
                    "coefficient": float(coefficient),
                    "std_error": float(standard_errors.loc[term]),
                    "z_value": float(z_values.loc[term]),
                    "p_value": float(p_values.loc[term]),
                    "ci_lower_95": float(confidence_intervals.loc[term, 0]),
                    "ci_upper_95": float(confidence_intervals.loc[term, 1]),
                    "converged": fit.converged,
                    "notes": "; ".join(fit.warnings_seen),
                }
            )

    return pd.DataFrame(rows)


def extract_random_effects(fit: FitSummary) -> pd.DataFrame:
    if fit.result is None:
        return pd.DataFrame(
            [
                {
                    "model_name": fit.model_name,
                    "school_id": np.nan,
                    "effect_name": "model_status",
                    "effect_value": np.nan,
                    "notes": fit.error_message or "fit failed",
                }
            ]
        )

    rows: list[dict[str, object]] = []
    for school_id, values in fit.result.random_effects.items():
        if isinstance(values, pd.Series):
            items = values.items()
        else:
            items = pd.Series(values).items()
        for effect_name, effect_value in items:
            rows.append(
                {
                    "model_name": fit.model_name,
                    "school_id": int(school_id),
                    "effect_name": str(effect_name),
                    "effect_value": float(effect_value),
                    "notes": "; ".join(fit.warnings_seen),
                }
            )

    return pd.DataFrame(rows)


def variance_row(fit: FitSummary) -> dict[str, object]:
    if fit.result is None:
        return {
            "model_name": fit.model_name,
            "between_school_variance": np.nan,
            "within_school_variance": np.nan,
            "icc": np.nan,
            "ses_slope_variance": np.nan,
            "intercept_ses_covariance": np.nan,
            "converged": fit.converged,
            "notes": fit.error_message or "fit failed",
        }

    cov_re = np.asarray(fit.result.cov_re, dtype=float)
    between_var = float(cov_re[0, 0]) if cov_re.size else float("nan")
    within_var = float(fit.result.scale)
    denominator = between_var + within_var
    icc = between_var / denominator if denominator > 0 else float("nan")
    slope_variance = float(cov_re[1, 1]) if cov_re.shape[0] > 1 else float("nan")
    intercept_ses_covariance = float(cov_re[0, 1]) if cov_re.shape[0] > 1 else float("nan")

    return {
        "model_name": fit.model_name,
        "between_school_variance": between_var,
        "within_school_variance": within_var,
        "icc": icc,
        "ses_slope_variance": slope_variance,
        "intercept_ses_covariance": intercept_ses_covariance,
        "converged": fit.converged,
        "notes": "; ".join(fit.warnings_seen),
    }


def save_predicted_vs_observed(data: pd.DataFrame, fit: FitSummary, figure_path: Path) -> None:
    if fit.result is None:
        raise RuntimeError("A fitted model is required to draw predicted_vs_observed.png")

    predicted = pd.Series(fit.result.fittedvalues, name="predicted_math_score")
    observed = data["math_score"].reset_index(drop=True)
    axis_min = float(min(observed.min(), predicted.min()))
    axis_max = float(max(observed.max(), predicted.max()))

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(7.5, 5.8))
    scatter = ax.scatter(
        predicted,
        observed,
        alpha=0.65,
        s=28,
        edgecolor="white",
        linewidth=0.4,
    )
    _ = scatter
    _ = ax.plot([axis_min, axis_max], [axis_min, axis_max], color="black", linestyle="--", linewidth=1.2)
    _ = ax.set_title("Predicted vs observed math score")
    _ = ax.set_xlabel("Predicted math score")
    _ = ax.set_ylabel("Observed math score")
    fig.tight_layout()
    fig.savefig(figure_path, dpi=180)
    plt.close(fig)


def write_summary(
    *,
    output_dir: Path,
    config: CaseConfig,
    data: pd.DataFrame,
    null_fit: FitSummary,
    random_intercept_fit: FitSummary,
    random_slope_fit: FitSummary,
    preferred_fit: FitSummary,
    variance_table: pd.DataFrame,
    smoke_test: bool,
) -> tuple[Path, Path]:
    preferred_variance = variance_table.loc[variance_table["model_name"] == preferred_fit.model_name].iloc[0]
    summary_lines = [
        f"case_id: {CASE_ID}",
        f"title: {CASE_TITLE}",
        f"mode: {'SMOKE TEST' if smoke_test else 'FULL RUN'}",
        f"seed: {config.seed}",
        f"sample_size: {len(data)}",
        f"school_count: {int(data['school_id'].nunique())}",
        f"students_per_school_mean: {data.groupby('school_id').size().mean():.1f}",
        f"data_mode: {DATA_MODE}",
        f"replication_type: {REPLICATION_TYPE}",
        "models_fit: null_model -> random_intercept_model -> random_slope_model_if_converged",
        f"null_model_converged: {null_fit.converged}",
        f"random_intercept_model_converged: {random_intercept_fit.converged}",
        f"random_slope_model_converged: {random_slope_fit.converged}",
        f"selected_prediction_model: {preferred_fit.model_name}",
        (
            "variance_decomposition_selected: "
            f"between_school={preferred_variance['between_school_variance']:.4f}, "
            f"within_school={preferred_variance['within_school_variance']:.4f}, "
            f"icc={preferred_variance['icc']:.4f}"
        ),
        (
            "score_ranges: "
            f"math_mean={data['math_score'].mean():.2f}, reading_mean={data['reading_score'].mean():.2f}, "
            f"ses_sd={data['ses'].std(ddof=0):.2f}"
        ),
        f"claim_boundary: {CLAIM_BOUNDARY}",
    ]
    summary_path = output_dir / "summary.txt"
    _ = summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    smoke_lines = [
        f"mode: {'SMOKE TEST' if smoke_test else 'FULL RUN'}",
        f"sample_size: {len(data)}",
        f"school_count: {int(data['school_id'].nunique())}",
        f"preferred_model: {preferred_fit.model_name}",
        "artifacts:",
        "- fixed_effects.csv",
        "- random_effects.csv",
        "- variance_decomposition.csv",
        "- predicted_vs_observed.png",
        "- summary.txt",
        "- smoke_test.txt",
    ]
    smoke_path = output_dir / "smoke_test.txt"
    _ = smoke_path.write_text("\n".join(smoke_lines) + "\n", encoding="utf-8")
    return summary_path, smoke_path


def run(smoke_test: bool = False) -> dict[str, Path]:
    paths = resolve_paths()
    config = load_config(paths["params_file"])
    data = simulate_multilevel_data(config=config, smoke_test=smoke_test)

    null_fit = fit_mixed_model(
        model_name="null_model",
        formula="math_score ~ 1",
        data=data,
        re_formula="1",
    )
    if null_fit.result is None:
        raise RuntimeError(f"Null model failed: {null_fit.error_message}")

    random_intercept_fit = fit_mixed_model(
        model_name="random_intercept_model",
        formula="math_score ~ ses + school_resources",
        data=data,
        re_formula="1",
    )
    if random_intercept_fit.result is None:
        raise RuntimeError(f"Random intercept model failed: {random_intercept_fit.error_message}")

    random_slope_fit = fit_mixed_model(
        model_name="random_slope_model",
        formula="math_score ~ ses + school_resources",
        data=data,
        re_formula="1 + ses",
    )
    preferred_fit = random_slope_fit if random_slope_fit.result is not None else random_intercept_fit

    fixed_effects = extract_fixed_effects([null_fit, random_intercept_fit, random_slope_fit])
    random_effects = extract_random_effects(preferred_fit)
    variance_table = pd.DataFrame(
        [
            variance_row(null_fit),
            variance_row(random_intercept_fit),
            variance_row(random_slope_fit),
        ]
    )

    fixed_effects_path = paths["output_dir"] / "fixed_effects.csv"
    random_effects_path = paths["output_dir"] / "random_effects.csv"
    variance_path = paths["output_dir"] / "variance_decomposition.csv"
    figure_path = paths["output_dir"] / "predicted_vs_observed.png"

    fixed_effects.to_csv(fixed_effects_path, index=False, encoding="utf-8-sig")
    random_effects.to_csv(random_effects_path, index=False, encoding="utf-8-sig")
    variance_table.to_csv(variance_path, index=False, encoding="utf-8-sig")
    save_predicted_vs_observed(data=data, fit=preferred_fit, figure_path=figure_path)
    summary_path, smoke_path = write_summary(
        output_dir=paths["output_dir"],
        config=config,
        data=data,
        null_fit=null_fit,
        random_intercept_fit=random_intercept_fit,
        random_slope_fit=random_slope_fit,
        preferred_fit=preferred_fit,
        variance_table=variance_table,
        smoke_test=smoke_test,
    )

    return {
        "summary": summary_path,
        "smoke_test": smoke_path,
        "fixed_effects": fixed_effects_path,
        "random_effects": random_effects_path,
        "variance_decomposition": variance_path,
        "predicted_vs_observed": figure_path,
    }


if __name__ == "__main__":
    arguments = parse_args()
    smoke_test_flag = getattr(arguments, "smoke_test", False)
    outputs = run(smoke_test=bool(smoke_test_flag))
    for label, path in outputs.items():
        print(f"{label}: {path}")
