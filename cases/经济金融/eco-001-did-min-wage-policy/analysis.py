from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, cast

import matplotlib
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import yaml

matplotlib.use("Agg")

import matplotlib.pyplot as plt


CASE_ID = "eco-001-did-min-wage-policy"
CASE_TITLE = "最低工资政策的就业效应：双重差分法实证分析"
CLAIM_BOUNDARY = "该案例演示 DID 识别逻辑，不替代真实最低工资政策实证结论。"
GITHUB_REFERENCE_NOTE = (
    "Regression structure adapted from the fixed-effects DID/event-study pattern "
    "shown in amazon-science/azcausal, where treatment indicators are estimated "
    "alongside unit and time fixed effects."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulated DID case for minimum wage policy.")
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


def build_simulation_config(params: dict[str, Any], smoke_test: bool) -> dict[str, Any]:
    config = dict(params.get("simulation", {}))
    if smoke_test:
        config["n_treated_firms"] = min(int(config["n_treated_firms"]), 24)
        config["n_control_firms"] = min(int(config["n_control_firms"]), 24)
    return config


def generate_panel(seed: int, config: dict[str, Any]) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    periods = list(range(int(config["n_periods"])))
    policy_start = int(config["policy_start"])
    rows: list[dict[str, Any]] = []

    for group_name, treated, firm_count in (
        ("control", 0, int(config["n_control_firms"])),
        ("treated", 1, int(config["n_treated_firms"])),
    ):
        prefix = "C" if treated == 0 else "T"
        for firm_index in range(firm_count):
            firm_id = f"{prefix}{firm_index:03d}"
            firm_fe = rng.normal(0.0, float(config["firm_fe_sd"]))
            base_wage = float(config["base_wage"]) + rng.normal(0.0, float(config["base_wage_sd"]))
            base_productivity = float(config["base_productivity"]) + rng.normal(
                0.0, float(config["productivity_sd"])
            )

            for period in periods:
                post = int(period >= policy_start)
                time_effect = float(config["time_linear"]) * period + float(config["time_quadratic"]) * (period**2)
                productivity = base_productivity + float(config["productivity_trend"]) * period + rng.normal(
                    0.0, float(config["productivity_noise_sd"])
                )
                avg_wage = base_wage + float(config["wage_trend"]) * period + rng.normal(
                    0.0, float(config["wage_noise_sd"])
                )
                if treated and post:
                    avg_wage += float(config["wage_policy_bump"])
                demand_index = float(config["demand_level"]) + rng.normal(0.0, float(config["demand_noise_sd"]))
                did = treated * post
                employment = (
                    float(config["employment_intercept"])
                    + firm_fe
                    + time_effect
                    + float(config["productivity_coef"]) * productivity
                    - float(config["wage_coef"]) * avg_wage
                    + float(config["demand_coef"]) * demand_index
                    + float(config["policy_effect"]) * did
                    + rng.normal(0.0, float(config["employment_noise_sd"]))
                )
                rows.append(
                    {
                        "firm_id": firm_id,
                        "period": period,
                        "group": group_name,
                        "treated": treated,
                        "post": post,
                        "employment": max(employment, 5.0),
                        "avg_wage": avg_wage,
                        "productivity": productivity,
                        "demand_index": demand_index,
                        "did": did,
                        "relative_period": period - policy_start,
                    }
                )

    panel = pd.DataFrame(rows).sort_values(["firm_id", "period"]).reset_index(drop=True)
    return panel


def build_group_means(panel: pd.DataFrame) -> pd.DataFrame:
    group_means = panel.groupby(["period", "group"], as_index=False).agg(mean_employment=("employment", "mean"))
    return cast(pd.DataFrame, group_means)


def save_parallel_trends_plot(group_means: pd.DataFrame, figure_path: Path, policy_start: int) -> None:
    pivot = group_means.pivot(index="period", columns="group", values="mean_employment").sort_index()
    normalized = pivot.subtract(pivot.loc[: policy_start - 1].mean())

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True)
    colors = {"control": "#1f77b4", "treated": "#d62728"}

    for group in ["control", "treated"]:
        axes[0].plot(pivot.index, pivot[group], marker="o", linewidth=2, color=colors[group], label=group)
        axes[1].plot(
            normalized.index,
            normalized[group],
            marker="o",
            linewidth=2,
            color=colors[group],
            label=group,
        )

    for axis in axes:
        axis.axvline(policy_start - 0.5, linestyle="--", color="black", alpha=0.7)
        axis.set_xlabel("Period")
        axis.legend(frameon=False)

    axes[0].set_title("Average employment by group")
    axes[0].set_ylabel("Mean employment")
    axes[1].set_title("Normalized to pre-policy mean")
    axes[1].set_ylabel("Change relative to pre-policy mean")

    fig.suptitle("Minimum wage DID: parallel trends", fontsize=13)
    fig.savefig(figure_path, dpi=150)
    plt.close(fig)


def fit_did_model(panel: pd.DataFrame) -> Any:
    model = smf.ols(
        "employment ~ did + avg_wage + productivity + demand_index + C(firm_id) + C(period)",
        data=panel,
    )
    return model.fit(cov_type="cluster", cov_kwds={"groups": panel["firm_id"]})


def fit_placebo_model(panel: pd.DataFrame, placebo_start: int, policy_start: int) -> Any:
    placebo_panel = panel.loc[panel["period"] < policy_start].copy()
    placebo_panel["placebo_post"] = (placebo_panel["period"] >= placebo_start).astype(int)
    placebo_panel["placebo_did"] = placebo_panel["treated"] * placebo_panel["placebo_post"]
    model = smf.ols(
        "employment ~ placebo_did + avg_wage + productivity + demand_index + C(firm_id) + C(period)",
        data=placebo_panel,
    )
    return model.fit(cov_type="cluster", cov_kwds={"groups": placebo_panel["firm_id"]})


def coefficient_frame(result: Any, variable: str, label: str) -> pd.DataFrame:
    ci_low, ci_high = result.conf_int().loc[variable]
    return pd.DataFrame(
        [
            {
                "term": variable,
                "label": label,
                "estimate": float(result.params[variable]),
                "std_error": float(result.bse[variable]),
                "t_value": float(result.tvalues[variable]),
                "p_value": float(result.pvalues[variable]),
                "ci_low": float(ci_low),
                "ci_high": float(ci_high),
            }
        ]
    )


def write_summary(
    summary_path: Path,
    panel: pd.DataFrame,
    config: dict[str, Any],
    did_result: pd.DataFrame,
    placebo_result: pd.DataFrame,
    smoke_test: bool,
) -> None:
    did_row = did_result.iloc[0]
    placebo_row = placebo_result.iloc[0]
    line_break = "\n"
    summary = f"""case_id: {CASE_ID}
title: {CASE_TITLE}
mode: {'SMOKE TEST' if smoke_test else 'FULL RUN'}
observations: {len(panel)}
firms: {panel['firm_id'].nunique()}
periods: {panel['period'].nunique()}
policy_start: {int(config['policy_start'])}

main_did_estimate: {did_row['estimate']:.4f}
main_did_ci95: [{did_row['ci_low']:.4f}, {did_row['ci_high']:.4f}]
main_did_p_value: {did_row['p_value']:.4f}
interpretation: 在控制企业固定效应、时期固定效应以及观测控制变量后，处理组企业在政策后平均就业相对对照组减少约 {abs(did_row['estimate']):.2f} 人。

placebo_estimate: {placebo_row['estimate']:.4f}
placebo_p_value: {placebo_row['p_value']:.4f}
placebo_interpretation: 若安慰剂系数接近 0 且不显著，可视为与“政策前不存在虚假处理效应”的设定一致。

parallel_trend_note: 图中政策前两组就业趋势被设计为共享共同趋势，政策后差异主要来自处理效应。
github_reference_note: {GITHUB_REFERENCE_NOTE}
claim_boundary: {CLAIM_BOUNDARY}
"""
    _ = summary_path.write_text(summary.replace("\n", line_break), encoding="utf-8")


def write_smoke_manifest(smoke_path: Path, artifacts: dict[str, Path], smoke_test: bool) -> None:
    lines = [
        f"mode: {'SMOKE TEST' if smoke_test else 'FULL RUN'}",
        f"case_id: {CASE_ID}",
        f"summary: {artifacts['summary'].name}",
        f"panel_data: {artifacts['data'].relative_to(artifacts['data'].parent.parent)}",
        f"parallel_trends: {artifacts['parallel_trends'].name}",
        f"did_table: {artifacts['did_table'].name}",
        f"placebo_table: {artifacts['placebo_table'].name}",
        f"group_means: {artifacts['group_means'].name}",
        f"claim_boundary: {CLAIM_BOUNDARY}",
    ]
    _ = smoke_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_summary_text() -> str:
    paths = resolve_paths()
    params = load_params(paths["params_file"])
    summary_path = paths["case_dir"] / str(params["outputs"]["summary_file"])
    return summary_path.read_text(encoding="utf-8")


def print_notebook_summary() -> None:
    print(read_summary_text())


def load_result_tables() -> dict[str, pd.DataFrame]:
    paths = resolve_paths()
    params = load_params(paths["params_file"])
    outputs = params["outputs"]
    return {
        "did": pd.read_csv(paths["case_dir"] / str(outputs["did_table"])),
        "placebo": pd.read_csv(paths["case_dir"] / str(outputs["placebo_table"])),
        "group_means": pd.read_csv(paths["case_dir"] / str(outputs["group_means_table"])),
    }


def run_case(smoke_test: bool = False) -> dict[str, str]:
    paths = resolve_paths()
    params = load_params(paths["params_file"])
    outputs = params["outputs"]
    seed = int(params["seed"])
    config = build_simulation_config(params, smoke_test)

    data_path = paths["case_dir"] / str(outputs["data_file"])
    summary_path = paths["case_dir"] / str(outputs["summary_file"])
    smoke_path = paths["case_dir"] / str(outputs["smoke_file"])
    parallel_trends_path = paths["case_dir"] / str(outputs["trends_figure"])
    did_table_path = paths["case_dir"] / str(outputs["did_table"])
    placebo_table_path = paths["case_dir"] / str(outputs["placebo_table"])
    group_means_path = paths["case_dir"] / str(outputs["group_means_table"])

    panel = generate_panel(seed=seed, config=config)
    group_means = build_group_means(panel)
    did_model = fit_did_model(panel)
    did_result = coefficient_frame(did_model, "did", "treated × post")
    placebo_model = fit_placebo_model(
        panel,
        placebo_start=int(config["placebo_start"]),
        policy_start=int(config["policy_start"]),
    )
    placebo_result = coefficient_frame(placebo_model, "placebo_did", "treated × placebo_post")

    panel.to_csv(data_path, index=False)
    group_means.to_csv(group_means_path, index=False)
    did_result.to_csv(did_table_path, index=False)
    placebo_result.to_csv(placebo_table_path, index=False)
    save_parallel_trends_plot(group_means, parallel_trends_path, policy_start=int(config["policy_start"]))

    write_summary(summary_path, panel, config, did_result, placebo_result, smoke_test)
    artifacts = {
        "summary": summary_path,
        "data": data_path,
        "parallel_trends": parallel_trends_path,
        "did_table": did_table_path,
        "placebo_table": placebo_table_path,
        "group_means": group_means_path,
    }
    write_smoke_manifest(smoke_path, artifacts, smoke_test)

    return {key: str(value) for key, value in {**artifacts, "smoke": smoke_path}.items()}


if __name__ == "__main__":
    args = parse_args()
    produced = run_case(smoke_test=bool(args.smoke_test))
    print(f"Generated summary: {produced['summary']}")
