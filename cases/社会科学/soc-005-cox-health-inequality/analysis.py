# pyright: reportMissingImports=false, reportMissingTypeStubs=false, reportReturnType=false

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from lifelines import CoxPHFitter, KaplanMeierFitter
from lifelines.statistics import proportional_hazard_test


SES_ORDER = ["high", "mid", "low"]
CASE_ID = "soc-005-cox-health-inequality"
SES_LABELS = {
    "high": "High SES",
    "mid": "Middle SES",
    "low": "Low SES",
}
SES_HAZARD_SHIFT = {
    "high": -0.30,
    "mid": 0.0,
    "low": 0.38,
}
SEX_HAZARD_SHIFT = {
    0: 0.0,
    1: -0.08,
}
DATA_MODE = "simulated"
REPLICATION_TYPE = "illustration"
CLAIM_BOUNDARY = "该案例演示生存分析逻辑，不替代真实队列研究结论。"


@dataclass(frozen=True)
class CaseConfig:
    seed: int
    output_dir: str
    cohort_size: int
    smoke_test_cohort_size: int
    max_followup_years: float
    baseline_hazard: float
    administrative_censor_low: float
    administrative_censor_high: float
    loss_to_followup_share: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Simulate a censored cohort and estimate SES differences in healthy-life survival. "
            "analysis.py is the single source of truth."
        )
    )
    _ = parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run a smaller end-to-end pipeline while still generating all required artifacts.",
    )
    return parser.parse_args()


def resolve_paths() -> dict[str, Path]:
    case_dir = Path(__file__).resolve().parent
    output_dir = case_dir / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    return {
        "case_dir": case_dir,
        "output_dir": output_dir,
        "params_file": case_dir / "params.yaml",
        "index_file": case_dir / "index.md",
    }


def load_config(params_file: Path) -> CaseConfig:
    payload = yaml.safe_load(params_file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("params.yaml must parse to a mapping")

    return CaseConfig(
        seed=int(payload["seed"]),
        output_dir=str(payload["output_dir"]),
        cohort_size=int(payload["cohort_size"]),
        smoke_test_cohort_size=int(payload["smoke_test_cohort_size"]),
        max_followup_years=float(payload["max_followup_years"]),
        baseline_hazard=float(payload["baseline_hazard"]),
        administrative_censor_low=float(payload["administrative_censor_low"]),
        administrative_censor_high=float(payload["administrative_censor_high"]),
        loss_to_followup_share=float(payload["loss_to_followup_share"]),
    )


def simulate_cohort(config: CaseConfig, smoke_test: bool) -> pd.DataFrame:
    cohort_size = config.smoke_test_cohort_size if smoke_test else config.cohort_size
    rng = np.random.default_rng(config.seed + (17 if smoke_test else 0))

    age = np.clip(rng.normal(loc=56.0, scale=9.5, size=cohort_size), 35, 80)
    female = rng.binomial(1, 0.52, size=cohort_size)
    chronic_burden = np.clip(rng.poisson(lam=1.4, size=cohort_size), 0, 5)
    ses_group = rng.choice(SES_ORDER, size=cohort_size, p=[0.30, 0.42, 0.28])

    linear_predictor = (
        ((age - 55.0) / 10.0) * 0.24
        + np.array([SEX_HAZARD_SHIFT[int(value)] for value in female])
        + chronic_burden * 0.28
        + np.array([SES_HAZARD_SHIFT[group] for group in ses_group])
    )
    individual_hazard = config.baseline_hazard * np.exp(linear_predictor)
    event_time = rng.exponential(scale=1.0 / individual_hazard)

    administrative_censor = rng.uniform(
        low=config.administrative_censor_low,
        high=config.administrative_censor_high,
        size=cohort_size,
    )
    has_loss_to_followup = rng.binomial(1, config.loss_to_followup_share, size=cohort_size).astype(bool)
    random_loss_time = rng.uniform(low=1.2, high=config.max_followup_years, size=cohort_size)
    loss_to_followup = np.where(has_loss_to_followup, random_loss_time, np.inf)

    censor_time = np.minimum(administrative_censor, loss_to_followup)
    observed_time = np.minimum.reduce(
        [event_time, censor_time, np.full(cohort_size, config.max_followup_years)]
    )
    event_observed = (event_time <= censor_time) & (event_time <= config.max_followup_years)

    cohort = pd.DataFrame(
        {
            "person_id": np.arange(1, cohort_size + 1, dtype=int),
            "age": age,
            "female": female,
            "chronic_burden": chronic_burden,
            "ses_group": ses_group,
            "followup_years": observed_time,
            "event_observed": event_observed.astype(int),
        }
    )
    cohort["ses_group"] = pd.Categorical(cohort["ses_group"], categories=SES_ORDER, ordered=True)
    cohort["female_label"] = np.where(cohort["female"] == 1, "female", "male")
    return cohort


def build_model_frame(cohort: pd.DataFrame) -> pd.DataFrame:
    dummies = pd.get_dummies(cohort["ses_group"], prefix="ses", drop_first=True)
    model_frame = pd.concat(
        [
            cohort[["followup_years", "event_observed", "age", "female", "chronic_burden"]],
            dummies,
        ],
        axis=1,
    )
    for expected_column in ("ses_mid", "ses_low"):
        if expected_column not in model_frame.columns:
            model_frame[expected_column] = 0
    ordered_columns = [
        "followup_years",
        "event_observed",
        "age",
        "female",
        "chronic_burden",
        "ses_mid",
        "ses_low",
    ]
    return model_frame[ordered_columns].astype(float)


def save_km_curve(cohort: pd.DataFrame, figure_path: Path) -> None:
    kmf = KaplanMeierFitter()
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(8, 5.5))

    for group in SES_ORDER:
        group_frame = cohort.loc[cohort["ses_group"] == group]
        kmf.fit(
            durations=group_frame["followup_years"],
            event_observed=group_frame["event_observed"],
            label=SES_LABELS[group],
        )
        kmf.plot_survival_function(ax=ax, ci_show=True)

    _ = ax.set_title("Health-survival curves by socioeconomic status")
    _ = ax.set_xlabel("Follow-up time (years)")
    _ = ax.set_ylabel("Probability of remaining free of health decline")
    _ = ax.set_ylim(0.0, 1.02)
    _ = ax.legend(title="SES group")
    fig.tight_layout()
    fig.savefig(figure_path, dpi=180)
    plt.close(fig)


def fit_cox_model(model_frame: pd.DataFrame) -> CoxPHFitter:
    cph = CoxPHFitter()
    cph.fit(model_frame, duration_col="followup_years", event_col="event_observed")
    return cph


def export_cox_summary(cph: CoxPHFitter, output_path: Path) -> pd.DataFrame:
    summary = cph.summary.copy()
    summary = summary.rename(
        columns={
            "coef": "coef",
            "exp(coef)": "hazard_ratio",
            "se(coef)": "std_error",
            "coef lower 95%": "coef_lower_95",
            "coef upper 95%": "coef_upper_95",
            "exp(coef) lower 95%": "hazard_ratio_lower_95",
            "exp(coef) upper 95%": "hazard_ratio_upper_95",
            "p": "p_value",
        }
    )
    summary.index.name = "covariate"
    summary.to_csv(output_path, encoding="utf-8-sig")
    return summary


def export_ph_test(cph: CoxPHFitter, model_frame: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    test_result = proportional_hazard_test(cph, model_frame, time_transform="rank")
    ph_table = test_result.summary.copy()
    ph_table.index.name = "covariate"
    ph_table.to_csv(output_path, encoding="utf-8-sig")
    return ph_table


def median_survival_by_group(cohort: pd.DataFrame) -> dict[str, float]:
    medians: dict[str, float] = {}
    kmf = KaplanMeierFitter()
    for group in SES_ORDER:
        group_frame = cohort.loc[cohort["ses_group"] == group]
        kmf.fit(group_frame["followup_years"], group_frame["event_observed"])
        medians[group] = float(kmf.median_survival_time_)
    return medians


def format_hr_interpretation(summary: pd.DataFrame) -> list[str]:
    lines: list[str] = []
    interpretation_map = {
        "ses_mid": "中 SES 相对高 SES",
        "ses_low": "低 SES 相对高 SES",
        "age": "年龄每增加 1 岁",
        "female": "女性相对男性",
        "chronic_burden": "慢病负担每增加 1 项",
    }
    for covariate, label in interpretation_map.items():
        if covariate not in summary.index:
            continue
        row = summary.loc[covariate]
        lines.append(
            (
                f"- {label} 的风险比 = {row['hazard_ratio']:.3f} "
                f"(95% CI: {row['hazard_ratio_lower_95']:.3f}, {row['hazard_ratio_upper_95']:.3f}; "
                f"p = {row['p_value']:.4f})。"
            )
        )
    return lines


def write_summary(
    *,
    cohort: pd.DataFrame,
    summary: pd.DataFrame,
    ph_table: pd.DataFrame,
    config: CaseConfig,
    paths: dict[str, Path],
    smoke_test: bool,
) -> Path:
    medians = median_survival_by_group(cohort)
    censoring_rate = 1.0 - float(cohort["event_observed"].mean())
    low_hr = float(summary.loc["ses_low", "hazard_ratio"])
    mid_hr = float(summary.loc["ses_mid", "hazard_ratio"])
    ph_flag_count = int((ph_table["p"] < 0.05).sum()) if "p" in ph_table.columns else -1

    lines = [
        f"mode: {'SMOKE TEST' if smoke_test else 'FULL RUN'}",
        f"case_id: {CASE_ID}",
        f"seed: {config.seed}",
        f"sample_size: {len(cohort)}",
        f"data_mode: {DATA_MODE}",
        f"replication_type: {REPLICATION_TYPE}",
        "event_definition: 首次进入健康受损状态",
        (
            "censoring_rule: 右删失来自行政结题与随机失访；"
            "默认视为非信息性删失。"
        ),
        f"censoring_rate: {censoring_rate:.3f}",
        (
            "median_survival_years: "
            f"high={medians['high']:.2f}, mid={medians['mid']:.2f}, low={medians['low']:.2f}"
        ),
        (
            "ses_hazard_gradient: "
            f"mid_vs_high_hr={mid_hr:.3f}, low_vs_high_hr={low_hr:.3f}"
        ),
        "hazard_ratio_interpretation:",
        *format_hr_interpretation(summary),
        (
            "ph_assumption_check: "
            f"Schoenfeld 残差 rank 变换检验中，p < 0.05 的协变量数量 = {ph_flag_count}。"
        ),
        f"claim_boundary: {CLAIM_BOUNDARY}",
    ]

    summary_path = paths["output_dir"] / "summary.txt"
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary_path


def write_smoke_artifact(paths: dict[str, Path], cohort: pd.DataFrame, smoke_test: bool) -> Path:
    artifact_path = paths["output_dir"] / "smoke_test.txt"
    status = "SMOKE TEST" if smoke_test else "FULL RUN"
    artifact_path.write_text(
        "\n".join(
            [
                f"mode: {status}",
                f"sample_size: {len(cohort)}",
                f"km_curve: {(paths['output_dir'] / 'km_curve_by_ses.png').name}",
                f"cox_summary: {(paths['output_dir'] / 'cox_summary.csv').name}",
                f"ph_test: {(paths['output_dir'] / 'ph_assumption_test.csv').name}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return artifact_path


def run(smoke_test: bool = False) -> dict[str, Path]:
    paths = resolve_paths()
    config = load_config(paths["params_file"])
    cohort = simulate_cohort(config=config, smoke_test=smoke_test)
    model_frame = build_model_frame(cohort)

    km_path = paths["output_dir"] / "km_curve_by_ses.png"
    cox_path = paths["output_dir"] / "cox_summary.csv"
    ph_path = paths["output_dir"] / "ph_assumption_test.csv"

    save_km_curve(cohort, km_path)
    cph = fit_cox_model(model_frame)
    summary = export_cox_summary(cph, cox_path)
    ph_table = export_ph_test(cph, model_frame, ph_path)
    summary_path = write_summary(
        cohort=cohort,
        summary=summary,
        ph_table=ph_table,
        config=config,
        paths=paths,
        smoke_test=smoke_test,
    )
    smoke_path = write_smoke_artifact(paths=paths, cohort=cohort, smoke_test=smoke_test)

    return {
        "summary": summary_path,
        "smoke_test": smoke_path,
        "km_curve": km_path,
        "cox_summary": cox_path,
        "ph_test": ph_path,
    }


if __name__ == "__main__":
    arguments = parse_args()
    outputs = run(smoke_test=bool(arguments.smoke_test))
    for label, path in outputs.items():
        print(f"{label}: {path}")
