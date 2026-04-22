from __future__ import annotations

# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false, reportMissingTypeArgument=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportOptionalMemberAccess=false, reportArgumentType=false, reportMissingTypeStubs=false, reportUnusedCallResult=false, reportAny=false, reportExplicitAny=false

import argparse
import logging
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

try:
    from semopy import Model, calc_stats
except ModuleNotFoundError as exc:  # pragma: no cover - dependency contract belongs to environment
    raise ModuleNotFoundError(
        "semopy is required for soc-006-sem-social-capital-wellbeing. Install project dependencies first."
    ) from exc


CASE_ID = "soc-006-sem-social-capital-wellbeing"
CASE_TITLE = "社会资本如何影响主观幸福感：结构方程模型的路径分析"
DATA_MODE = "simulated"
REPLICATION_TYPE = "illustration"
CLAIM_BOUNDARY = "演示SEM路径分析逻辑，不替代真实社会调查实证结论"

LOGGER = logging.getLogger(__name__)

CFA_MODEL = """
social_capital =~ sc1 + sc2 + sc3
social_trust =~ st1 + st2 + st3
swb =~ swb1 + swb2 + swb3 + swb4
social_capital ~~ social_trust
social_capital ~~ swb
social_trust ~~ swb
""".strip()

SEM_MODEL = """
social_capital =~ sc1 + sc2 + sc3
social_trust =~ st1 + st2 + st3
swb =~ swb1 + swb2 + swb3 + swb4
social_trust ~ social_capital
swb ~ social_capital + social_trust
""".strip()


@dataclass(frozen=True)
class CaseConfig:
    seed: int
    output_dir: str
    sample_size_full: int
    sample_size_smoke: int
    bootstrap_reps_full: int
    bootstrap_reps_smoke: int
    bootstrap_attempt_multiplier: int
    social_capital_to_trust: float
    social_capital_to_swb: float
    trust_to_swb: float
    social_capital_sd: float
    trust_noise_sd: float
    swb_noise_sd: float
    loadings: dict[str, list[float]]
    measurement_error_sd: dict[str, float]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulate latent-variable survey indicators and run CFA + SEM mediation analysis with semopy."
    )
    _ = parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run a reduced but complete deterministic SEM pipeline for automated validation.",
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


def load_config(params_file: Path) -> CaseConfig:
    payload = yaml.safe_load(params_file.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("params.yaml must parse to a mapping")

    loadings = payload.get("loadings")
    measurement_error_sd = payload.get("measurement_error_sd")
    if not isinstance(loadings, dict) or not isinstance(measurement_error_sd, dict):
        raise ValueError("loadings and measurement_error_sd must both be mappings")

    return CaseConfig(
        seed=int(payload["seed"]),
        output_dir=str(payload["output_dir"]),
        sample_size_full=int(payload["sample_size_full"]),
        sample_size_smoke=int(payload["sample_size_smoke"]),
        bootstrap_reps_full=int(payload["bootstrap_reps_full"]),
        bootstrap_reps_smoke=int(payload["bootstrap_reps_smoke"]),
        bootstrap_attempt_multiplier=int(payload["bootstrap_attempt_multiplier"]),
        social_capital_to_trust=float(payload["social_capital_to_trust"]),
        social_capital_to_swb=float(payload["social_capital_to_swb"]),
        trust_to_swb=float(payload["trust_to_swb"]),
        social_capital_sd=float(payload["social_capital_sd"]),
        trust_noise_sd=float(payload["trust_noise_sd"]),
        swb_noise_sd=float(payload["swb_noise_sd"]),
        loadings={key: [float(v) for v in value] for key, value in loadings.items()},
        measurement_error_sd={key: float(value) for key, value in measurement_error_sd.items()},
    )


def standardize(values: np.ndarray) -> np.ndarray:
    centered = values - float(values.mean())
    scale = float(values.std(ddof=0))
    if np.isclose(scale, 0.0):
        return centered
    return centered / scale


def simulate_indicators(latent: np.ndarray, prefix: str, loadings: list[float], error_sd: float, rng: np.random.Generator) -> dict[str, np.ndarray]:
    indicators: dict[str, np.ndarray] = {}
    for index, loading in enumerate(loadings, start=1):
        signal = loading * latent + rng.normal(0.0, error_sd, size=len(latent))
        indicators[f"{prefix}{index}"] = standardize(signal)
    return indicators


def simulate_dataset(config: CaseConfig, smoke_test: bool) -> pd.DataFrame:
    sample_size = config.sample_size_smoke if smoke_test else config.sample_size_full
    rng = np.random.default_rng(config.seed + (101 if smoke_test else 0))

    social_capital = rng.normal(0.0, config.social_capital_sd, size=sample_size)
    social_trust = (
        config.social_capital_to_trust * social_capital
        + rng.normal(0.0, config.trust_noise_sd, size=sample_size)
    )
    swb = (
        config.social_capital_to_swb * social_capital
        + config.trust_to_swb * social_trust
        + rng.normal(0.0, config.swb_noise_sd, size=sample_size)
    )

    data = {
        **simulate_indicators(
            social_capital,
            prefix="sc",
            loadings=config.loadings["social_capital"],
            error_sd=config.measurement_error_sd["social_capital"],
            rng=rng,
        ),
        **simulate_indicators(
            social_trust,
            prefix="st",
            loadings=config.loadings["social_trust"],
            error_sd=config.measurement_error_sd["social_trust"],
            rng=rng,
        ),
        **simulate_indicators(
            swb,
            prefix="swb",
            loadings=config.loadings["swb"],
            error_sd=config.measurement_error_sd["swb"],
            rng=rng,
        ),
    }

    frame = pd.DataFrame(data)
    frame.insert(0, "respondent_id", np.arange(1, sample_size + 1, dtype=int))
    return frame


def fit_semopy_model(model_desc: str, data: pd.DataFrame) -> tuple[Model, pd.DataFrame, pd.DataFrame]:
    model = Model(model_desc)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        _ = model.fit(data)
    estimates = model.inspect(std_est=True).copy()
    stats = calc_stats(model).copy()
    if "Value" in stats.index:
        stats_frame = stats.loc[["Value"]].T.reset_index()
        stats_frame.columns = ["metric", "value"]
    else:
        stats_frame = stats.T.reset_index()
        stats_frame.columns = ["metric", "value"]
    return model, estimates, stats_frame


def path_row(estimates: pd.DataFrame, *, lval: str, rval: str) -> pd.Series:
    matches = estimates.loc[
        (estimates["op"] == "~")
        & (estimates["lval"] == lval)
        & (estimates["rval"] == rval)
    ]
    if matches.empty:
        raise KeyError(f"Missing SEM path {lval} ~ {rval}")
    return matches.iloc[0]


def extract_effects(estimates: pd.DataFrame) -> dict[str, float]:
    path_a = path_row(estimates, lval="social_trust", rval="social_capital")
    path_b = path_row(estimates, lval="swb", rval="social_trust")
    path_c = path_row(estimates, lval="swb", rval="social_capital")

    a = float(path_a["Estimate"])
    b = float(path_b["Estimate"])
    c_prime = float(path_c["Estimate"])
    a_std = float(path_a["Est. Std"])
    b_std = float(path_b["Est. Std"])
    c_prime_std = float(path_c["Est. Std"])
    indirect = a * b
    indirect_std = a_std * b_std
    total = c_prime + indirect
    total_std = c_prime_std + indirect_std

    return {
        "a_path": a,
        "b_path": b,
        "direct_effect": c_prime,
        "indirect_effect": indirect,
        "total_effect": total,
        "a_path_std": a_std,
        "b_path_std": b_std,
        "direct_effect_std": c_prime_std,
        "indirect_effect_std": indirect_std,
        "total_effect_std": total_std,
        "a_path_p_value": safe_float(path_a["p-value"]),
        "b_path_p_value": safe_float(path_b["p-value"]),
        "direct_effect_p_value": safe_float(path_c["p-value"]),
    }


def safe_float(value: Any) -> float:
    if value in {"-", None}:
        return float("nan")
    return float(value)


def bootstrap_mediation(data: pd.DataFrame, config: CaseConfig, smoke_test: bool) -> tuple[pd.DataFrame, int]:
    target = config.bootstrap_reps_smoke if smoke_test else config.bootstrap_reps_full
    max_attempts = max(target * config.bootstrap_attempt_multiplier, target)
    rng = np.random.default_rng(config.seed + (909 if smoke_test else 707))
    collected: list[dict[str, float]] = []
    attempts = 0

    indicator_data = data.drop(columns=["respondent_id"])
    while len(collected) < target and attempts < max_attempts:
        attempts += 1
        sample_index = rng.integers(0, len(indicator_data), len(indicator_data))
        sample = indicator_data.iloc[sample_index].reset_index(drop=True)
        try:
            _, boot_estimates, _ = fit_semopy_model(SEM_MODEL, sample)
            collected.append(extract_effects(boot_estimates))
        except (KeyError, TypeError, ValueError, np.linalg.LinAlgError) as exc:
            LOGGER.warning("Skipping failed bootstrap replication after SEM fit error: %s", exc)
            continue

    if not collected:
        raise RuntimeError("All SEM bootstrap fits failed; no mediation estimates were collected.")

    return pd.DataFrame(collected), attempts


def summarize_indirect_bootstrap(bootstrap_effects: pd.DataFrame) -> dict[str, float]:
    indirect = bootstrap_effects["indirect_effect"].to_numpy(dtype=float)
    direct = bootstrap_effects["direct_effect"].to_numpy(dtype=float)
    total = bootstrap_effects["total_effect"].to_numpy(dtype=float)
    return {
        "bootstrap_successes": float(len(bootstrap_effects)),
        "indirect_ci_low": float(np.quantile(indirect, 0.025)),
        "indirect_ci_high": float(np.quantile(indirect, 0.975)),
        "direct_ci_low": float(np.quantile(direct, 0.025)),
        "direct_ci_high": float(np.quantile(direct, 0.975)),
        "total_ci_low": float(np.quantile(total, 0.025)),
        "total_ci_high": float(np.quantile(total, 0.975)),
    }


def build_mediation_table(effects: dict[str, float], bootstrap_summary: dict[str, float], bootstrap_attempts: int) -> pd.DataFrame:
    rows = [
        {
            "effect": "direct",
            "estimate": effects["direct_effect"],
            "estimate_std": effects["direct_effect_std"],
            "p_value": effects["direct_effect_p_value"],
            "ci_low": bootstrap_summary["direct_ci_low"],
            "ci_high": bootstrap_summary["direct_ci_high"],
            "bootstrap_successes": int(bootstrap_summary["bootstrap_successes"]),
            "bootstrap_attempts": bootstrap_attempts,
        },
        {
            "effect": "indirect",
            "estimate": effects["indirect_effect"],
            "estimate_std": effects["indirect_effect_std"],
            "p_value": float("nan"),
            "ci_low": bootstrap_summary["indirect_ci_low"],
            "ci_high": bootstrap_summary["indirect_ci_high"],
            "bootstrap_successes": int(bootstrap_summary["bootstrap_successes"]),
            "bootstrap_attempts": bootstrap_attempts,
        },
        {
            "effect": "total",
            "estimate": effects["total_effect"],
            "estimate_std": effects["total_effect_std"],
            "p_value": float("nan"),
            "ci_low": bootstrap_summary["total_ci_low"],
            "ci_high": bootstrap_summary["total_ci_high"],
            "bootstrap_successes": int(bootstrap_summary["bootstrap_successes"]),
            "bootstrap_attempts": bootstrap_attempts,
        },
    ]
    return pd.DataFrame(rows)


def render_stats_line(stats_frame: pd.DataFrame, metric: str) -> str:
    match = stats_frame.loc[stats_frame["metric"] == metric, "value"]
    if match.empty:
        return f"{metric}=NA"
    return f"{metric}={float(match.iloc[0]):.3f}"


def write_outputs(
    *,
    paths: dict[str, Path],
    config: CaseConfig,
    data: pd.DataFrame,
    cfa_stats: pd.DataFrame,
    sem_stats: pd.DataFrame,
    parameter_estimates: pd.DataFrame,
    mediation_table: pd.DataFrame,
    effects: dict[str, float],
    smoke_test: bool,
) -> dict[str, Path]:
    output_dir = paths["output_dir"]
    cfa_stats_path = output_dir / "cfa_fit_stats.csv"
    sem_stats_path = output_dir / "sem_fit_stats.csv"
    parameters_path = output_dir / "parameter_estimates.csv"
    mediation_path = output_dir / "mediation_effects.csv"
    sample_path = output_dir / "simulated_indicator_sample.csv"
    summary_path = output_dir / "summary.txt"
    smoke_path = output_dir / "smoke_test.txt"

    cfa_stats.to_csv(cfa_stats_path, index=False, encoding="utf-8-sig")
    sem_stats.to_csv(sem_stats_path, index=False, encoding="utf-8-sig")
    parameter_estimates.to_csv(parameters_path, index=False, encoding="utf-8-sig")
    mediation_table.to_csv(mediation_path, index=False, encoding="utf-8-sig")
    data.head(20).to_csv(sample_path, index=False, encoding="utf-8-sig")

    fit_summary = ", ".join(
        [
            render_stats_line(cfa_stats, "CFI"),
            render_stats_line(cfa_stats, "TLI"),
            render_stats_line(cfa_stats, "RMSEA"),
        ]
    )
    sem_fit_summary = ", ".join(
        [
            render_stats_line(sem_stats, "CFI"),
            render_stats_line(sem_stats, "TLI"),
            render_stats_line(sem_stats, "RMSEA"),
        ]
    )
    mediation_rows = mediation_table.set_index("effect")
    summary_lines = [
        f"case_id: {CASE_ID}",
        f"title: {CASE_TITLE}",
        f"mode: {'SMOKE TEST' if smoke_test else 'FULL RUN'}",
        f"seed: {config.seed}",
        f"sample_size: {len(data)}",
        f"data_mode: {DATA_MODE}",
        f"replication_type: {REPLICATION_TYPE}",
        "github_pattern_adaptation: 使用真实 GitHub semopy 示例中的 Model(desc) -> fit(data) -> inspect() -> calc_stats() 工作流，并结合 semopy 教程的 inspect/std_est 输出格式组织结果。",
        f"cfa_fit: {fit_summary}",
        f"sem_fit: {sem_fit_summary}",
        (
            "path_estimates: "
            f"social_capital->social_trust={effects['a_path']:.3f}, "
            f"social_trust->swb={effects['b_path']:.3f}, "
            f"social_capital->swb_direct={effects['direct_effect']:.3f}"
        ),
        (
            "mediation_effects: "
            f"indirect={effects['indirect_effect']:.3f} "
            f"(95% bootstrap CI {mediation_rows.loc['indirect', 'ci_low']:.3f}, {mediation_rows.loc['indirect', 'ci_high']:.3f}); "
            f"direct={effects['direct_effect']:.3f}; total={effects['total_effect']:.3f}"
        ),
        f"claim_boundary: {CLAIM_BOUNDARY}",
    ]
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    smoke_lines = [
        f"case_id: {CASE_ID}",
        f"mode: {'SMOKE TEST' if smoke_test else 'FULL RUN'}",
        f"sample_size: {len(data)}",
        f"cfa_fit_stats: {cfa_stats_path.name}",
        f"sem_fit_stats: {sem_stats_path.name}",
        f"mediation_effects: {mediation_path.name}",
        f"summary: {summary_path.name}",
    ]
    smoke_path.write_text("\n".join(smoke_lines) + "\n", encoding="utf-8")

    return {
        "cfa_fit_stats": cfa_stats_path,
        "sem_fit_stats": sem_stats_path,
        "parameter_estimates": parameters_path,
        "mediation_effects": mediation_path,
        "sample": sample_path,
        "summary": summary_path,
        "smoke_test": smoke_path,
    }


def run(smoke_test: bool = False) -> dict[str, Path]:
    paths = resolve_paths()
    config = load_config(paths["params_file"])
    data = simulate_dataset(config, smoke_test=smoke_test)
    indicator_data = data.drop(columns=["respondent_id"])

    _, cfa_estimates, cfa_stats = fit_semopy_model(CFA_MODEL, indicator_data)
    _, sem_estimates, sem_stats = fit_semopy_model(SEM_MODEL, indicator_data)
    effects = extract_effects(sem_estimates)
    bootstrap_effects, bootstrap_attempts = bootstrap_mediation(data, config, smoke_test=smoke_test)
    bootstrap_summary = summarize_indirect_bootstrap(bootstrap_effects)
    mediation_table = build_mediation_table(effects, bootstrap_summary, bootstrap_attempts)

    parameter_estimates = pd.concat(
        [
            cfa_estimates.assign(model="CFA"),
            sem_estimates.assign(model="SEM"),
        ],
        ignore_index=True,
    )
    parameter_estimates = parameter_estimates[
        ["model", "lval", "op", "rval", "Estimate", "Est. Std", "Std. Err", "z-value", "p-value"]
    ]

    artifacts = write_outputs(
        paths=paths,
        config=config,
        data=data,
        cfa_stats=cfa_stats,
        sem_stats=sem_stats,
        parameter_estimates=parameter_estimates,
        mediation_table=mediation_table,
        effects=effects,
        smoke_test=smoke_test,
    )
    return artifacts


def main() -> int:
    args = parse_args()
    artifacts = run(smoke_test=bool(args.smoke_test))
    print(f"Generated {len(artifacts)} artifacts for {CASE_ID}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
