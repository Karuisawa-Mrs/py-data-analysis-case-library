from __future__ import annotations

# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false, reportMissingTypeArgument=false

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import yaml
from statsmodels.tools.sm_exceptions import ValueWarning

try:
    from linearmodels.panel import PanelOLS
except ModuleNotFoundError:
    PanelOLS = None


CASE_ID = "soc-004-twfe-left-behind-education"
CASE_TITLE = "父母外出务工对留守儿童学业成绩的影响：双向固定效应模型"
DEFAULT_SEED = 20260422


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulate a student-year panel and estimate a two-way fixed-effects model."
    )
    _ = parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run a reduced-size deterministic pipeline for automated validation.",
    )
    return parser.parse_args()


def resolve_paths() -> dict[str, Path]:
    case_dir = Path(__file__).resolve().parent
    output_dir = case_dir / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    return {
        "case_dir": case_dir,
        "params_file": case_dir / "params.yaml",
        "output_dir": output_dir,
    }


def load_params(params_file: Path) -> dict[str, Any]:
    params = yaml.safe_load(params_file.read_text(encoding="utf-8")) or {}
    if not isinstance(params, dict):
        raise ValueError("params.yaml must parse to a mapping")
    return params


def sigmoid(value: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-value))


def simulate_panel(params: dict[str, Any], smoke_test: bool) -> pd.DataFrame:
    simulation = params.get("simulation", {})
    if not isinstance(simulation, dict):
        raise ValueError("simulation section in params.yaml must be a mapping")

    seed = int(params.get("seed", DEFAULT_SEED))
    rng = np.random.default_rng(seed)

    n_students = int(simulation["n_students_smoke"] if smoke_test else simulation["n_students_full"])
    n_years = int(simulation["n_years_smoke"] if smoke_test else simulation["n_years_full"])
    start_year = int(simulation["start_year"])
    years = np.arange(start_year, start_year + n_years)

    region_names = ["east", "central", "west"]
    region_shares_map = simulation.get("region_shares", {})
    if not isinstance(region_shares_map, dict):
        raise ValueError("region_shares must be a mapping")
    region_shares = np.array([float(region_shares_map.get(name, 0.0)) for name in region_names], dtype=float)
    region_shares = region_shares / region_shares.sum()

    baseline_age = rng.integers(
        int(simulation["min_baseline_age"]),
        int(simulation["max_baseline_age"]) + 1,
        size=n_students,
    )
    students = pd.DataFrame(
        {
            "student_id": np.arange(1, n_students + 1),
            "baseline_age": baseline_age,
            "female": rng.binomial(1, 0.48, size=n_students),
            "region": rng.choice(region_names, p=region_shares, size=n_students),
            "student_fe": rng.normal(0.0, 4.5, size=n_students),
            "economic_pressure": rng.normal(0.0, 1.0, size=n_students),
            "caregiver_baseline": rng.normal(0.0, 1.0, size=n_students),
            "school_match": rng.normal(0.0, 1.0, size=n_students),
        }
    )
    students["young_group"] = (students["baseline_age"] <= 10).astype(int)
    students["region_group"] = np.where(students["region"].eq("east"), "coastal", "inland")

    year_effects = np.linspace(-1.2, 1.4, n_years) + rng.normal(0.0, 0.25, size=n_years)
    region_push = {
        "east": np.linspace(0.10, -0.08, n_years),
        "central": np.linspace(0.18, 0.30, n_years),
        "west": np.linspace(0.25, 0.38, n_years),
    }

    rows: list[dict[str, Any]] = []
    true_effect = float(simulation["true_effect_left_behind"])
    younger_penalty = float(simulation["younger_penalty"])
    inland_penalty = float(simulation["inland_penalty"])
    threshold = float(simulation["left_behind_threshold"])

    for student in students.itertuples(index=False):
        previous_left_behind = 0
        for offset, year in enumerate(years):
            age = int(student.baseline_age + offset)
            year_fe = float(year_effects[offset])
            common_income_trend = 0.12 * offset
            household_income = (
                0.9
                - 0.45 * float(student.economic_pressure)
                + 0.25 * (student.region == "east")
                + common_income_trend
                + rng.normal(0.0, 0.35)
            )
            caregiver_support = (
                0.55 * float(student.caregiver_baseline)
                - 0.20 * previous_left_behind
                - 0.06 * offset
                + rng.normal(0.0, 0.35)
            )
            school_resources = (
                0.45 * float(student.school_match)
                + 0.30 * (student.region == "east")
                + 0.08 * offset
                + rng.normal(0.0, 0.25)
            )
            study_hours = (
                1.8
                + 0.12 * age
                + 0.22 * school_resources
                - 0.35 * previous_left_behind
                + rng.normal(0.0, 0.40)
            )

            migration_latent = (
                -0.30
                + 0.65 * float(student.economic_pressure)
                + region_push[str(student.region)][offset]
                + 0.22 * (age <= 12)
                + 0.55 * previous_left_behind
                - 0.28 * household_income
                + rng.normal(0.0, 0.55)
            )
            left_behind_probability = float(sigmoid(np.array([migration_latent]))[0])
            left_behind = int(left_behind_probability > threshold)

            treatment_effect = true_effect
            if int(student.young_group) == 1:
                treatment_effect += younger_penalty
            if str(student.region_group) == "inland":
                treatment_effect += inland_penalty

            exam_score = (
                74.0
                + float(student.student_fe)
                + year_fe
                + treatment_effect * left_behind
                + 1.35 * household_income
                + 1.05 * study_hours
                + 1.10 * caregiver_support
                + 1.20 * school_resources
                - 0.08 * (age - 12) ** 2
                + rng.normal(0.0, 2.4)
            )

            rows.append(
                {
                    "student_id": int(student.student_id),
                    "year": int(year),
                    "age": age,
                    "baseline_age": int(student.baseline_age),
                    "female": int(student.female),
                    "region": str(student.region),
                    "region_group": str(student.region_group),
                    "young_group": int(student.young_group),
                    "household_income": household_income,
                    "study_hours": study_hours,
                    "caregiver_support": caregiver_support,
                    "school_resources": school_resources,
                    "left_behind": left_behind,
                    "left_behind_probability": left_behind_probability,
                    "exam_score": exam_score,
                }
            )
            previous_left_behind = left_behind

    panel = pd.DataFrame(rows).sort_values(["student_id", "year"]).reset_index(drop=True)
    panel["left_behind_switch"] = panel.groupby("student_id")["left_behind"].diff().abs().fillna(0.0)
    return panel


def build_panel_inputs(df: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    panel = df.set_index(["student_id", "year"]).sort_index()
    outcome = panel["exam_score"]
    exog = panel[["left_behind", "household_income", "study_hours", "caregiver_support", "school_resources"]]
    return outcome, exog


def fit_twfe(df: pd.DataFrame) -> dict[str, Any]:
    if PanelOLS is not None:
        outcome, exog = build_panel_inputs(df)
        model = PanelOLS(outcome, exog, entity_effects=True, time_effects=True)
        unadjusted = model.fit(cov_type="unadjusted")
        clustered = model.fit(cov_type="clustered", cluster_entity=True, cluster_time=True)
        covariance_label = "clustered_entity_time"
        estimator = "linearmodels.PanelOLS"
    else:
        model = None
        formula = (
            "exam_score ~ left_behind + household_income + study_hours + "
            "caregiver_support + school_resources + C(student_id) + C(year)"
        )
        unadjusted = smf.ols(formula=formula, data=df).fit()
        try:
            clustered = smf.ols(formula=formula, data=df).fit(
                cov_type="cluster",
                cov_kwds={
                    "groups": df[["student_id", "year"]],
                    "use_correction": True,
                },
            )
            covariance_label = "clustered_entity_time"
        except (ValueError, TypeError, np.linalg.LinAlgError, ValueWarning):
            clustered = smf.ols(formula=formula, data=df).fit(
                cov_type="cluster",
                cov_kwds={"groups": df["student_id"], "use_correction": True},
            )
            covariance_label = "clustered_entity"
        estimator = "statsmodels.OLS_with_dummies"

    return {
        "model": model,
        "unadjusted": unadjusted,
        "clustered": clustered,
        "clustered_label": covariance_label,
        "estimator": estimator,
        "nobs": int(clustered.nobs),
        "n_students": int(df["student_id"].nunique()),
        "n_years": int(df["year"].nunique()),
    }


def extract_row(name: str, result: Any, covariance_label: str, sample_label: str) -> dict[str, Any]:
    confidence_interval = result.conf_int()
    if isinstance(confidence_interval, pd.DataFrame):
        ci_low = float(confidence_interval.loc[name].iloc[0])
        ci_high = float(confidence_interval.loc[name].iloc[1])
    else:
        parameter_index = list(result.params.index).index(name)
        ci_low = float(confidence_interval[parameter_index][0])
        ci_high = float(confidence_interval[parameter_index][1])

    std_errors = result.std_errors if hasattr(result, "std_errors") else result.bse
    t_stats = result.tstats if hasattr(result, "tstats") else result.tvalues
    p_values = result.pvalues

    return {
        "sample": sample_label,
        "covariance": covariance_label,
        "term": name,
        "coef": float(result.params[name]),
        "std_error": float(std_errors[name]),
        "t_stat": float(t_stats[name]),
        "p_value": float(p_values[name]),
        "ci_low": ci_low,
        "ci_high": ci_high,
        "nobs": int(result.nobs),
    }


def build_main_results_table(fit_results: dict[str, Any]) -> pd.DataFrame:
    rows = [
        extract_row("left_behind", fit_results["unadjusted"], "unadjusted", "full_sample"),
        extract_row("left_behind", fit_results["clustered"], str(fit_results["clustered_label"]), "full_sample"),
    ]
    return pd.DataFrame(rows)


def run_subsample_estimates(df: pd.DataFrame, group_column: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for group_value, subset in df.groupby(group_column):
        subset = subset.copy()
        if subset["student_id"].nunique() < 25:
            continue
        no_within_variation = bool(
            subset.groupby("student_id")["left_behind"].nunique().le(1).to_numpy().all()
        )
        if no_within_variation:
            continue
        subset_fit = fit_twfe(subset)
        result = subset_fit["clustered"]
        row = extract_row("left_behind", result, str(subset_fit["clustered_label"]), str(group_value))
        row["n_students"] = int(subset["student_id"].nunique())
        row["n_years"] = int(subset["year"].nunique())
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_sample(df: pd.DataFrame) -> dict[str, Any]:
    switchers = (
        df.groupby("student_id")["left_behind"].nunique().gt(1).sum()
    )
    return {
        "rows": int(len(df)),
        "students": int(df["student_id"].nunique()),
        "years": int(df["year"].nunique()),
        "left_behind_share": float(df["left_behind"].mean()),
        "switcher_share": float(switchers / df["student_id"].nunique()),
        "avg_score": float(df["exam_score"].mean()),
    }


def render_dataframe(df: pd.DataFrame, digits: int = 3) -> str:
    if df.empty:
        return "(empty)"
    numeric_columns = df.select_dtypes(include=[np.number]).columns
    formatted = df.copy()
    for column in numeric_columns:
        formatted[column] = formatted[column].map(lambda value: round(float(value), digits))
    return formatted.to_string(index=False)


def write_outputs(
    paths: dict[str, Path],
    params: dict[str, Any],
    panel: pd.DataFrame,
    sample_summary: dict[str, Any],
    main_results: pd.DataFrame,
    age_results: pd.DataFrame,
    region_results: pd.DataFrame,
    estimator_name: str,
    smoke_test: bool,
) -> Path:
    output_dir = paths["output_dir"]
    artifact_path = output_dir / ("smoke_test.txt" if smoke_test else "summary.txt")
    mode_label = "SMOKE TEST" if smoke_test else "FULL RUN"
    claim_boundary = "该案例演示面板识别逻辑，不替代真实 CFPS/CHARLS 实证结论。"

    clustered_label = str(main_results.loc[main_results["covariance"].ne("unadjusted"), "covariance"].iloc[0])
    effect_row = main_results.loc[main_results["covariance"].eq(clustered_label)].iloc[0]
    left_behind_coef = float(effect_row["coef"])
    left_behind_se = float(effect_row["std_error"])
    left_behind_p = float(effect_row["p_value"])

    lines = [
        f"case_id: {CASE_ID}",
        f"title: {CASE_TITLE}",
        f"mode: {mode_label}",
        f"seed: {params.get('seed', DEFAULT_SEED)}",
        f"estimator: {estimator_name}",
        f"robust_covariance: {clustered_label}",
        "",
        "[design]",
        "- entity effects: absorb time-invariant student traits such as baseline ability and family cultural capital.",
        "- time effects: absorb common annual shocks such as policy, exam difficulty, and macro educational environment.",
        "- interpretation: the coefficient on left_behind is identified from within-student changes over time, conditional on observed time-varying covariates.",
        "",
        "[sample summary]",
        f"rows: {sample_summary['rows']}",
        f"students: {sample_summary['students']}",
        f"years: {sample_summary['years']}",
        f"left_behind_share: {sample_summary['left_behind_share']:.3f}",
        f"switcher_share: {sample_summary['switcher_share']:.3f}",
        f"avg_score: {sample_summary['avg_score']:.3f}",
        "",
        "[main regression: left_behind]",
        f"clustered coef: {left_behind_coef:.3f}",
        f"clustered std_error: {left_behind_se:.3f}",
        f"clustered p_value: {left_behind_p:.4f}",
        "",
        "[main regression table]",
        render_dataframe(main_results),
        "",
        "[heterogeneity: age groups]",
        render_dataframe(age_results),
        "",
        "[heterogeneity: region groups]",
        render_dataframe(region_results),
        "",
        "[claim boundary]",
        claim_boundary,
    ]

    summary_text = "\n".join(lines) + "\n"
    (output_dir / "summary.txt").write_text(summary_text, encoding="utf-8")
    (output_dir / "smoke_test.txt").write_text(summary_text, encoding="utf-8")

    main_results.to_csv(output_dir / "main_regression.csv", index=False, encoding="utf-8-sig")
    age_results.to_csv(output_dir / "heterogeneity_age.csv", index=False, encoding="utf-8-sig")
    region_results.to_csv(output_dir / "heterogeneity_region.csv", index=False, encoding="utf-8-sig")
    panel.head(80).to_csv(output_dir / "simulated_panel_sample.csv", index=False, encoding="utf-8-sig")
    return artifact_path


def run(smoke_test: bool = False) -> Path:
    paths = resolve_paths()
    params = load_params(paths["params_file"])
    panel = simulate_panel(params, smoke_test=smoke_test)
    fit_results = fit_twfe(panel)
    main_results = build_main_results_table(fit_results)

    labelled_panel = panel.copy()
    labelled_panel["age_group"] = np.where(labelled_panel["young_group"].eq(1), "younger_baseline", "older_baseline")
    age_results = run_subsample_estimates(labelled_panel, "age_group")
    region_results = run_subsample_estimates(labelled_panel, "region_group")
    sample_summary = summarize_sample(panel)

    return write_outputs(
        paths=paths,
        params=params,
        panel=panel,
        sample_summary=sample_summary,
        main_results=main_results,
        age_results=age_results,
        region_results=region_results,
        estimator_name=str(fit_results["estimator"]),
        smoke_test=smoke_test,
    )


if __name__ == "__main__":
    arguments = parse_args()
    output_path = run(smoke_test=bool(arguments.smoke_test))
    print(f"Generated: {output_path}")
