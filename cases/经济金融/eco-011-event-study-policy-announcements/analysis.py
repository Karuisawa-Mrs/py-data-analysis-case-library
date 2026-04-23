# pyright: basic

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, cast

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from scipy import stats


CASE_ID = "eco-011-event-study-policy-announcements"
CASE_TITLE = "政策公告事件研究：异常收益与累积异常收益分析"
CLAIM_BOUNDARY = "该案例演示事件研究方法论，不替代真实市场政策冲击的实证分析。"
ESTIMATION_START = -120
ESTIMATION_END = -11
EVENT_START = -10
EVENT_END = 10


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulated event-study case for policy announcements.")
    _ = parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run the same pipeline with fewer firms and trading days while producing all required artifacts.",
    )
    return parser.parse_args()


def resolve_paths() -> dict[str, Path]:
    case_dir = Path(__file__).resolve().parent
    output_dir = case_dir / "outputs"
    data_dir = case_dir / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    return {
        "case_dir": case_dir,
        "data_dir": data_dir,
        "output_dir": output_dir,
        "params_file": case_dir / "params.yaml",
    }


def load_params(params_file: Path) -> dict[str, Any]:
    params = yaml.safe_load(params_file.read_text(encoding="utf-8")) or {}
    if not isinstance(params, dict):
        raise ValueError("params.yaml must parse to a mapping")
    return params


def build_config(params: dict[str, Any], smoke_test: bool) -> dict[str, Any]:
    base_config: dict[str, Any] = {
        "n_firms": 50,
        "n_days": 500,
        "event_share": 0.6,
        "market_mu": 0.0003,
        "market_sigma": 0.011,
        "market_shock_sigma": 0.004,
        "alpha_sd": 0.0004,
        "beta_low": 0.8,
        "beta_high": 1.3,
        "idio_sigma": 0.018,
        "event_effect_day0": 0.02,
        "event_effect_pre": 0.003,
        "event_effect_post": 0.002,
        "event_effect_persist": 0.001,
    }
    config = {**base_config, **dict(params.get("simulation", {}))}
    if smoke_test:
        config["n_firms"] = 10
        config["n_days"] = 200
    return config


def generate_simulated_returns(seed: int, config: dict[str, Any]) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n_days = int(config["n_days"])
    n_firms = int(config["n_firms"])
    n_event_firms = max(3, int(round(n_firms * float(config["event_share"]))))
    n_event_firms = min(n_event_firms, n_firms)

    trading_dates = pd.bdate_range("2021-01-01", periods=n_days)
    market_returns = rng.normal(float(config["market_mu"]), float(config["market_sigma"]), size=n_days)
    market_df = pd.DataFrame({"trade_date": trading_dates, "day_index": np.arange(n_days), "market_return": market_returns})

    event_firm_ids = set(rng.choice([f"F{i:03d}" for i in range(n_firms)], size=n_event_firms, replace=False).tolist())
    min_event_day = abs(ESTIMATION_START) + 10
    max_event_day = n_days - (EVENT_END + 1)

    rows: list[dict[str, Any]] = []
    for firm_index in range(n_firms):
        firm_id = f"F{firm_index:03d}"
        alpha = rng.normal(0.0, float(config["alpha_sd"]))
        beta = rng.uniform(float(config["beta_low"]), float(config["beta_high"]))
        idio_noise = rng.normal(0.0, float(config["idio_sigma"]), size=n_days)
        firm_returns = alpha + beta * market_returns + idio_noise

        has_event = firm_id in event_firm_ids
        event_day_index = int(rng.integers(min_event_day, max_event_day + 1)) if has_event else -1

        if has_event:
            event_profile = {
                -2: float(config["event_effect_pre"]),
                -1: float(config["event_effect_pre"]),
                0: float(config["event_effect_day0"]),
                1: float(config["event_effect_post"]),
                2: float(config["event_effect_post"]),
                3: float(config["event_effect_persist"]),
            }
            for relative_day, effect in event_profile.items():
                target_idx = event_day_index + relative_day
                if 0 <= target_idx < n_days:
                    firm_returns[target_idx] += effect + rng.normal(0.0, float(config["market_shock_sigma"]) / 4.0)

        event_date = trading_dates[event_day_index] if has_event else pd.NaT
        for day_index, trade_date in enumerate(trading_dates):
            rows.append(
                {
                    "firm_id": firm_id,
                    "trade_date": trade_date,
                    "day_index": day_index,
                    "market_return": market_returns[day_index],
                    "stock_return": firm_returns[day_index],
                    "has_event": has_event,
                    "event_day_index": event_day_index if has_event else np.nan,
                    "event_date": event_date,
                    "relative_day": day_index - event_day_index if has_event else np.nan,
                }
            )

    panel = pd.DataFrame(rows)
    panel["trade_date"] = pd.to_datetime(panel["trade_date"])
    panel["event_date"] = pd.to_datetime(panel["event_date"])
    panel = panel.merge(market_df, on=["trade_date", "day_index", "market_return"], how="left")
    return panel.sort_values(["firm_id", "trade_date"]).reset_index(drop=True)


def estimate_market_model(firm_panel: pd.DataFrame) -> tuple[float, float]:
    estimation_mask = firm_panel["relative_day"].between(ESTIMATION_START, ESTIMATION_END)
    estimation_sample = firm_panel.loc[estimation_mask, ["market_return", "stock_return"]].copy()
    if len(estimation_sample) < abs(ESTIMATION_START) - abs(ESTIMATION_END):
        raise ValueError("Estimation window is too short to fit the market model.")

    x = estimation_sample["market_return"].to_numpy()
    y = estimation_sample["stock_return"].to_numpy()
    beta, alpha = np.polyfit(x, y, deg=1)
    return float(alpha), float(beta)


def compute_event_window_metrics(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    event_panels = panel.loc[panel["has_event"]].copy()
    event_firms = sorted(event_panels["firm_id"].unique().tolist())

    event_window_frames: list[pd.DataFrame] = []
    for firm_id in event_firms:
        firm_panel = event_panels.loc[event_panels["firm_id"] == firm_id].copy()
        alpha_hat, beta_hat = estimate_market_model(firm_panel)
        event_window = firm_panel.loc[firm_panel["relative_day"].between(EVENT_START, EVENT_END)].copy()
        event_window["alpha_hat"] = alpha_hat
        event_window["beta_hat"] = beta_hat
        event_window["expected_return"] = alpha_hat + beta_hat * event_window["market_return"]
        event_window["abnormal_return"] = event_window["stock_return"] - event_window["expected_return"]
        event_window = event_window.sort_values("relative_day")
        event_window["car"] = event_window["abnormal_return"].cumsum()
        event_window_frames.append(event_window)

    event_window_returns = pd.concat(event_window_frames, ignore_index=True)
    event_window_returns["event_date"] = pd.to_datetime(event_window_returns["event_date"]).dt.strftime("%Y-%m-%d")
    event_window_returns["trade_date"] = pd.to_datetime(event_window_returns["trade_date"]).dt.strftime("%Y-%m-%d")

    aar_caar_rows: list[dict[str, float | int]] = []
    relative_days = sorted(int(day) for day in event_window_returns["relative_day"].unique().tolist())
    for relative_day in relative_days:
        day_slice = event_window_returns.loc[event_window_returns["relative_day"] == relative_day].copy()
        aar_caar_rows.append(
            {
                "relative_day": relative_day,
                "aar": float(day_slice["abnormal_return"].mean()),
                "caar": float(day_slice["car"].mean()),
                "cross_section_n": int(day_slice["firm_id"].nunique()),
                "mean_stock_return": float(day_slice["stock_return"].mean()),
                "mean_expected_return": float(day_slice["expected_return"].mean()),
            }
        )
    aar_caar = pd.DataFrame(aar_caar_rows)

    stats_rows: list[dict[str, Any]] = []
    for relative_day in relative_days:
        group = event_window_returns.loc[event_window_returns["relative_day"] == relative_day].copy()
        statistic, pvalue = cast(tuple[float, float], tuple(stats.ttest_1samp(group["car"].to_numpy(), popmean=0.0)))
        stats_rows.append(
            {
                "test_name": f"CAR_ttest_day_{relative_day:+d}",
                "relative_day": relative_day,
                "sample_size": int(group["firm_id"].nunique()),
                "mean_car": float(group["car"].mean()),
                "std_car": float(group["car"].std(ddof=1)),
                "t_statistic": float(statistic),
                "p_value": float(pvalue),
            }
        )

    full_window_car = (
        event_window_returns.loc[event_window_returns["relative_day"] == EVENT_END, ["firm_id", "car"]]
        .rename(columns={"car": "full_window_car"})
        .reset_index(drop=True)
    )
    full_statistic, full_pvalue = cast(
        tuple[float, float], tuple(stats.ttest_1samp(full_window_car["full_window_car"].to_numpy(), popmean=0.0))
    )
    stats_rows.append(
        {
            "test_name": "CAR_ttest_full_window_-10_to_+10",
            "relative_day": EVENT_END,
            "sample_size": int(full_window_car["firm_id"].nunique()),
            "mean_car": float(full_window_car["full_window_car"].mean()),
            "std_car": float(full_window_car["full_window_car"].std(ddof=1)),
            "t_statistic": float(full_statistic),
            "p_value": float(full_pvalue),
        }
    )
    test_statistics = pd.DataFrame(stats_rows)
    return event_window_returns, aar_caar, test_statistics


def save_car_plot(aar_caar: pd.DataFrame, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.8), constrained_layout=True)
    ax.plot(aar_caar["relative_day"], aar_caar["caar"], color="#1f77b4", linewidth=2.2, marker="o")
    ax.axhline(0.0, color="black", linewidth=1.0, linestyle="--", alpha=0.8)
    ax.axvline(0.0, color="#d62728", linewidth=1.0, linestyle=":", alpha=0.9)
    ax.set_title("Average CAR around policy announcement")
    ax.set_xlabel("Relative trading day")
    ax.set_ylabel("CAAR")
    ax.grid(alpha=0.25)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def write_summary(summary_path: Path, event_window_returns: pd.DataFrame, aar_caar: pd.DataFrame, test_statistics: pd.DataFrame, smoke_test: bool) -> None:
    final_window = test_statistics.loc[test_statistics["test_name"] == "CAR_ttest_full_window_-10_to_+10"].iloc[0]
    event_count = int(event_window_returns["firm_id"].nunique())
    lines = [
        f"case_id: {CASE_ID}",
        f"title: {CASE_TITLE}",
        f"mode: {'SMOKE TEST' if smoke_test else 'FULL RUN'}",
        f"event_firms: {event_count}",
        f"event_window: [{EVENT_START}, {EVENT_END}]",
        f"estimation_window: [{ESTIMATION_START}, {ESTIMATION_END}]",
        f"average_announcement_day_ar: {aar_caar.loc[aar_caar['relative_day'] == 0, 'aar'].iloc[0]:.6f}",
        f"average_full_window_car: {final_window['mean_car']:.6f}",
        f"full_window_t_statistic: {final_window['t_statistic']:.4f}",
        f"full_window_p_value: {final_window['p_value']:.4f}",
        "interpretation: The simulated treated firms are designed to exhibit a positive abnormal return around policy announcements, strongest on day 0 and tapering after the event.",
        f"claim_boundary: {CLAIM_BOUNDARY}",
    ]
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_smoke_manifest(smoke_path: Path, artifacts: dict[str, Path], smoke_test: bool) -> None:
    lines = [
        f"mode: {'SMOKE TEST' if smoke_test else 'FULL RUN'}",
        f"case_id: {CASE_ID}",
        f"summary_file: {artifacts['summary'].name}",
        f"event_window_returns: {artifacts['event_window_returns'].name}",
        f"aar_caar: {artifacts['aar_caar'].name}",
        f"test_statistics: {artifacts['test_statistics'].name}",
        f"car_plot: {artifacts['car_plot'].name}",
        f"claim_boundary: {CLAIM_BOUNDARY}",
    ]
    smoke_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_case(smoke_test: bool = False) -> dict[str, str]:
    paths = resolve_paths()
    params = load_params(paths["params_file"])
    seed = int(params["seed"])
    config = build_config(params, smoke_test)

    output_dir = paths["output_dir"]
    event_window_returns_path = output_dir / "event_window_returns.csv"
    aar_caar_path = output_dir / "aar_caar.csv"
    test_statistics_path = output_dir / "test_statistics.csv"
    car_plot_path = output_dir / "car_plot.png"
    summary_path = output_dir / "summary.txt"
    smoke_path = output_dir / "smoke_test.txt"

    panel = generate_simulated_returns(seed=seed, config=config)
    event_window_returns, aar_caar, test_statistics = compute_event_window_metrics(panel)

    export_columns = [
        "firm_id",
        "trade_date",
        "event_date",
        "relative_day",
        "market_return",
        "stock_return",
        "expected_return",
        "abnormal_return",
        "car",
        "alpha_hat",
        "beta_hat",
    ]
    event_window_returns.loc[:, export_columns].to_csv(event_window_returns_path, index=False)
    aar_caar.to_csv(aar_caar_path, index=False)
    test_statistics.to_csv(test_statistics_path, index=False)
    save_car_plot(aar_caar, car_plot_path)
    write_summary(summary_path, event_window_returns, aar_caar, test_statistics, smoke_test)

    artifacts = {
        "summary": summary_path,
        "event_window_returns": event_window_returns_path,
        "aar_caar": aar_caar_path,
        "test_statistics": test_statistics_path,
        "car_plot": car_plot_path,
    }
    write_smoke_manifest(smoke_path, artifacts, smoke_test)
    return {key: str(value) for key, value in {**artifacts, "smoke": smoke_path}.items()}


def read_summary_text() -> str:
    return (resolve_paths()["output_dir"] / "summary.txt").read_text(encoding="utf-8")


def print_notebook_summary() -> None:
    print(read_summary_text())


if __name__ == "__main__":
    args = parse_args()
    outputs = run_case(smoke_test=args.smoke_test)
    print(f"Generated: {outputs['summary']}")
