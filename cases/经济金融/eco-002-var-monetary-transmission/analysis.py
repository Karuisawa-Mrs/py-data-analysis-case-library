from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from statsmodels.tsa.api import VAR
from statsmodels.tsa.stattools import adfuller

matplotlib.use("Agg")

CASE_ID = "eco-002-var-monetary-transmission"
VARIABLES = ["M2", "GDP_deflator", "investment", "consumption", "exchange_rate"]
CLAIM_BOUNDARY = "该案例演示政策冲击传播逻辑，而非复刻真实央行冲击估计。"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Single-source analysis script for eco-002 VAR monetary transmission case."
    )
    _ = parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run a lightweight deterministic pipeline and emit all expected artifacts.",
    )
    return parser.parse_args()


def resolve_paths() -> dict[str, Path]:
    case_dir = Path(__file__).resolve().parent
    output_dir = case_dir / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    return {
        "case_dir": case_dir,
        "data_dir": case_dir / "data",
        "output_dir": output_dir,
        "params_file": case_dir / "params.yaml",
        "index_file": case_dir / "index.md",
    }


def load_params(params_file: Path) -> dict[str, Any]:
    payload = yaml.safe_load(params_file.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("params.yaml must parse to a mapping")
    return payload


def build_runtime_config(params: dict[str, Any], smoke_test: bool) -> dict[str, Any]:
    config = dict(params)
    if smoke_test:
        overrides = params.get("smoke_test_overrides", {})
        if isinstance(overrides, dict):
            config.update(overrides)
    config["smoke_test"] = smoke_test
    return config


def make_quarter_index(start: str, periods: int) -> pd.DatetimeIndex:
    return pd.period_range(start=start, periods=periods, freq="Q").to_timestamp(how="end")


def simulate_macro_levels(config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    seed = int(config["seed"])
    n_periods = int(config["n_periods"])
    burn_in = int(config["burn_in"])
    total_periods = n_periods + burn_in
    rng = np.random.default_rng(seed)

    policy_liquidity = np.zeros(total_periods)
    demand_cycle = np.zeros(total_periods)
    external_fx = np.zeros(total_periods)
    growth = np.zeros((total_periods, len(VARIABLES)))

    innovation_scale = np.array([0.28, 0.12, 0.22, 0.16, 0.18])

    for t in range(1, total_periods):
        policy_liquidity[t] = 0.55 * policy_liquidity[t - 1] + rng.normal(scale=0.55)
        demand_cycle[t] = 0.45 * demand_cycle[t - 1] + rng.normal(scale=0.40)
        external_fx[t] = 0.35 * external_fx[t - 1] + rng.normal(scale=0.45)
        eps_t = rng.normal(scale=innovation_scale)

        growth[t, 0] = (
            0.45 * growth[t - 1, 0]
            + 0.65 * policy_liquidity[t]
            + 0.15 * demand_cycle[t]
            + eps_t[0]
        )
        growth[t, 1] = (
            0.35 * growth[t - 1, 1]
            + 0.12 * policy_liquidity[t - 1]
            + 0.16 * demand_cycle[t]
            + 0.08 * growth[t - 1, 0]
            + eps_t[1]
        )
        growth[t, 2] = (
            0.42 * growth[t - 1, 2]
            + 0.48 * policy_liquidity[t]
            + 0.28 * demand_cycle[t]
            - 0.10 * growth[t - 1, 4]
            + eps_t[2]
        )
        growth[t, 3] = (
            0.48 * growth[t - 1, 3]
            + 0.20 * policy_liquidity[t]
            + 0.20 * demand_cycle[t]
            + 0.06 * growth[t - 1, 2]
            + eps_t[3]
        )
        growth[t, 4] = (
            0.38 * growth[t - 1, 4]
            - 0.26 * policy_liquidity[t]
            + 0.34 * external_fx[t]
            + eps_t[4]
        )

    retained_growth = growth[burn_in:]
    dates = make_quarter_index(str(config["date_start"]), periods=n_periods)
    base_levels = np.array([1100.0, 100.0, 650.0, 900.0, 100.0])
    log_levels = np.log(base_levels) + np.cumsum(retained_growth / 100.0, axis=0)
    levels = np.exp(log_levels)

    level_df = pd.DataFrame(levels, index=dates, columns=pd.Index(VARIABLES, dtype="object"))
    log_level_df = pd.DataFrame(
        np.log(level_df.to_numpy()),
        index=level_df.index,
        columns=level_df.columns,
    )
    transformed_df = log_level_df.diff().dropna() * 100.0
    transformed_df.index.name = "date"
    return level_df, transformed_df


def safe_adf_pvalue(series: pd.Series) -> float:
    cleaned = series.dropna()
    result = adfuller(cleaned, autolag="AIC")
    return float(result[1])


def build_stationarity_table(level_df: pd.DataFrame, transformed_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for name in VARIABLES:
        level_series = level_df.iloc[:, VARIABLES.index(name)]
        transformed_series = transformed_df.iloc[:, VARIABLES.index(name)]
        rows.append(
            {
                "variable": name,
                "level_adf_pvalue": safe_adf_pvalue(level_series),
                "log_diff_adf_pvalue": safe_adf_pvalue(transformed_series),
            }
        )
    table = pd.DataFrame(rows)
    table["level_stationary_at_5pct"] = table["level_adf_pvalue"] < 0.05
    table["log_diff_stationary_at_5pct"] = table["log_diff_adf_pvalue"] < 0.05
    return table


def choose_lag_order(model: VAR, maxlags: int, criterion: str) -> tuple[int, pd.DataFrame, dict[str, int | None]]:
    selection = model.select_order(maxlags=maxlags)
    lag_table = pd.DataFrame(selection.ics).rename_axis("lag")
    selected_orders: dict[str, int | None] = {}
    for key, value in selection.selected_orders.items():
        selected_orders[key] = None if value is None else int(value)

    chosen = selected_orders.get(criterion)
    if chosen is None or chosen < 1:
        chosen = 1
    return chosen, lag_table, selected_orders


def describe_irf(irf_object: Any, impulse_name: str) -> list[str]:
    impulse_index = VARIABLES.index(impulse_name)
    lines: list[str] = []
    for response_index, response_name in enumerate(VARIABLES):
        response_path = irf_object.orth_irfs[:, response_index, impulse_index]
        if len(response_path) <= 1:
            continue
        peak_horizon = int(np.argmax(np.abs(response_path[1:])) + 1)
        peak_value = float(response_path[peak_horizon])
        lines.append(
            f"- {response_name}: peak response {peak_value:.3f} at horizon {peak_horizon}"
        )
    return lines


def describe_fevd(fevd_object: Any, impulse_name: str) -> list[str]:
    impulse_index = VARIABLES.index(impulse_name)
    lines: list[str] = []
    last_horizon_index = fevd_object.decomp.shape[1] - 1
    for response_index, response_name in enumerate(VARIABLES):
        contribution = float(fevd_object.decomp[response_index, last_horizon_index, impulse_index])
        lines.append(
            f"- {response_name}: {contribution:.1%} of forecast error variance explained by {impulse_name} shock"
        )
    return lines


def write_summary(
    paths: dict[str, Path],
    config: dict[str, Any],
    stationarity_table: pd.DataFrame,
    selected_lag: int,
    selected_orders: dict[str, int | None],
    results: Any,
    irf_lines: list[str],
    fevd_lines: list[str],
) -> None:
    stationary_count = int(stationarity_table["log_diff_stationary_at_5pct"].sum())
    mode_label = "SMOKE TEST" if bool(config["smoke_test"]) else "FULL RUN"
    lines = [
        f"case_id: {CASE_ID}",
        f"mode: {mode_label}",
        f"seed: {int(config['seed'])}",
        f"claim_boundary: {CLAIM_BOUNDARY}",
        "",
        "Stationarity note:",
        "- The script estimates the VAR on log-differenced series instead of level series.",
        f"- ADF check: {stationary_count}/{len(VARIABLES)} transformed series reject a unit root at the 5% level.",
        "- This is a teaching-oriented stationarity step, not a full empirical pretesting protocol.",
        "",
        "Lag-order selection:",
        f"- criterion used: {config['lag_selection_ic']}",
        f"- selected orders: {selected_orders}",
        f"- fitted lag order: {selected_lag}",
        f"- stability check: {results.is_stable(verbose=False)}",
        "",
        f"Impulse-response interpretation for a positive orthogonalized {config['shock_variable']} shock:",
        *irf_lines,
        "",
        f"FEVD interpretation at horizon {int(config['fevd_horizon'])}:",
        *fevd_lines,
        "",
        "Caution:",
        "- Orthogonalized IRF/FEVD results depend on the Cholesky ordering.",
        "- The M2 shock is a stylized liquidity innovation, not an identified central-bank shock.",
    ]
    (paths["output_dir"] / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    smoke_lines = [
        f"case_id: {CASE_ID}",
        f"mode: {mode_label}",
        f"selected_lag: {selected_lag}",
        f"artifacts_dir: {paths['output_dir'].name}",
        "status: smoke-compatible artifacts generated",
    ]
    (paths["output_dir"] / "smoke_test.txt").write_text("\n".join(smoke_lines) + "\n", encoding="utf-8")


def save_irf_plot(paths: dict[str, Path], irf_object: Any, shock_variable: str) -> None:
    figure = irf_object.plot(orth=True, impulse=shock_variable, plot_stderr=False, figsize=(10, 12))
    figure.suptitle(f"Orthogonalized IRF to {shock_variable} Shock", fontsize=14)
    figure.tight_layout(rect=(0, 0, 1, 0.97))
    figure.savefig(paths["output_dir"] / "irf_m2_shock.png", dpi=160)
    plt.close(figure)


def save_fevd_plot(paths: dict[str, Path], fevd_object: Any) -> None:
    figure = fevd_object.plot(figsize=(10, 10))
    figure.suptitle("Forecast Error Variance Decomposition", fontsize=14)
    figure.tight_layout(rect=(0, 0, 1, 0.97))
    figure.savefig(paths["output_dir"] / "fevd_overview.png", dpi=160)
    plt.close(figure)


def run(smoke_test: bool = False) -> dict[str, Path]:
    paths = resolve_paths()
    params = load_params(paths["params_file"])
    config = build_runtime_config(params, smoke_test=smoke_test)

    level_df, transformed_df = simulate_macro_levels(config)
    stationarity_table = build_stationarity_table(level_df, transformed_df)
    stationarity_table.to_csv(paths["output_dir"] / "stationarity_checks.csv", index=False)

    model = VAR(transformed_df)
    selected_lag, lag_table, selected_orders = choose_lag_order(
        model=model,
        maxlags=int(config["maxlags"]),
        criterion=str(config["lag_selection_ic"]),
    )
    lag_table.to_csv(paths["output_dir"] / "lag_order_selection.csv")

    results = model.fit(selected_lag)
    shock_variable = str(config["shock_variable"])
    irf_object = results.irf(int(config["irf_horizon"]))
    fevd_object = results.fevd(int(config["fevd_horizon"]))

    save_irf_plot(paths, irf_object=irf_object, shock_variable=shock_variable)
    save_fevd_plot(paths, fevd_object=fevd_object)

    irf_lines = describe_irf(irf_object=irf_object, impulse_name=shock_variable)
    fevd_lines = describe_fevd(fevd_object=fevd_object, impulse_name=shock_variable)
    write_summary(
        paths=paths,
        config=config,
        stationarity_table=stationarity_table,
        selected_lag=selected_lag,
        selected_orders=selected_orders,
        results=results,
        irf_lines=irf_lines,
        fevd_lines=fevd_lines,
    )
    return paths


if __name__ == "__main__":
    cli_args = parse_args()
    generated_paths = run(smoke_test=bool(cli_args.smoke_test))
    print(f"Generated outputs in: {generated_paths['output_dir']}")
