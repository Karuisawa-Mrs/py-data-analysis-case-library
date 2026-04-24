# pyright: basic, reportMissingTypeStubs=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportAny=false, reportExplicitAny=false, reportMissingTypeArgument=false, reportReturnType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportUnusedCallResult=false

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any
import warnings

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.arima.model import ARIMA

try:
    from arch import arch_model

    HAS_ARCH = True
except ImportError:  # pragma: no cover - exercised only when optional dependency is absent
    arch_model = None
    HAS_ARCH = False


CASE_ID = "eco-012-volatility-forecast-garch-tft"
CASE_TITLE = "Volatility forecasting with GARCH, EGARCH, and a TFT-style proxy"
CLAIM_BOUNDARY = "This simulated benchmark demonstrates volatility-forecasting methods and is not investment advice."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Volatility forecast benchmark with GARCH/EGARCH and ML baselines.")
    _ = parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run the full artifact pipeline on a reduced sample.",
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


def build_run_config(params: dict[str, Any], smoke_test: bool) -> dict[str, Any]:
    return {
        "seed": require_int(params["seed"], "seed"),
        "output_dir_name": str(params.get("output_dir", "outputs")),
        "n_obs": 320 if smoke_test else 2000,
        "burn_in": 250 if smoke_test else 500,
        "omega": 0.00002,
        "alpha": 0.10,
        "beta": 0.86,
        "rv_window": 10,
        "lag_count": 5,
        "test_size": 0.25,
        "smoke_test": smoke_test,
    }


def simulate_garch_like_returns(config: dict[str, Any]) -> pd.DataFrame:
    seed = int(config["seed"])
    n_obs = int(config["n_obs"])
    burn_in = int(config["burn_in"])
    omega = float(config["omega"])
    alpha = float(config["alpha"])
    beta = float(config["beta"])
    total_obs = n_obs + burn_in

    rng = np.random.default_rng(seed)
    shocks = rng.normal(loc=0.0, scale=1.0, size=total_obs)
    returns = np.zeros(total_obs, dtype=float)
    sigma2 = np.zeros(total_obs, dtype=float)
    sigma2[0] = omega / max(1.0 - alpha - beta, 1e-6)
    returns[0] = np.sqrt(sigma2[0]) * shocks[0]

    for t in range(1, total_obs):
        sigma2[t] = omega + alpha * (returns[t - 1] ** 2) + beta * sigma2[t - 1]
        sigma2[t] = max(sigma2[t], 1e-10)
        returns[t] = np.sqrt(sigma2[t]) * shocks[t]

    retained_returns = returns[burn_in:]
    retained_sigma = np.sqrt(sigma2[burn_in:])
    return pd.DataFrame(
        {
            "date": pd.date_range(start="2015-01-01", periods=n_obs, freq="B"),
            "returns": retained_returns,
            "true_volatility": retained_sigma,
            "squared_returns": retained_returns**2,
            "absolute_returns": np.abs(retained_returns),
        }
    )


def build_modeling_frame(data: pd.DataFrame, rv_window: int, lag_count: int) -> pd.DataFrame:
    frame = data.copy()
    frame["realized_volatility"] = np.sqrt(
        frame["squared_returns"].rolling(window=rv_window, min_periods=rv_window).mean()
    )
    frame["rolling_return_mean"] = frame["returns"].rolling(window=rv_window, min_periods=rv_window).mean()
    frame["rolling_return_std"] = frame["returns"].rolling(window=rv_window, min_periods=rv_window).std()
    frame["rolling_abs_mean"] = frame["absolute_returns"].rolling(window=rv_window, min_periods=rv_window).mean()

    for lag in range(1, lag_count + 1):
        frame[f"return_lag_{lag}"] = frame["returns"].shift(lag)
        frame[f"squared_return_lag_{lag}"] = frame["squared_returns"].shift(lag)
        frame[f"realized_vol_lag_{lag}"] = frame["realized_volatility"].shift(lag)

    frame["target_realized_volatility"] = frame["realized_volatility"].shift(-1)
    return frame.dropna().reset_index(drop=True)


def train_test_split_time_series(frame: pd.DataFrame, test_size: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1")
    split_index = int(len(frame) * (1.0 - test_size))
    split_index = max(split_index, 30)
    train = frame.iloc[:split_index].copy()
    test = frame.iloc[split_index:].copy()
    if test.empty:
        raise ValueError("test split is empty; increase sample size")
    return train, test


def fit_arima_baseline(train_returns: pd.Series, forecast_steps: int) -> tuple[np.ndarray, pd.Series, pd.DataFrame]:
    model = ARIMA(train_returns, order=(1, 0, 1), trend="n")
    fitted = model.fit()
    forecast_result = fitted.get_forecast(steps=forecast_steps)
    forecast_variance = np.asarray(forecast_result.var_pred_mean, dtype=float)
    arima_vol_forecast = np.sqrt(np.maximum(forecast_variance, 1e-10))

    squared_residuals = pd.Series(np.square(np.asarray(fitted.resid, dtype=float)), name="squared_residual")
    lb_table = acorr_ljungbox(squared_residuals, lags=[5, 10], return_df=True)
    diagnostics = (
        lb_table.reset_index()
        .rename(columns={"index": "lag", "lb_stat": "statistic", "lb_pvalue": "pvalue"})
        .assign(test="Ljung-Box on squared ARIMA residuals", null_hypothesis="No ARCH-style serial dependence")
    )
    return arima_vol_forecast, pd.Series(fitted.resid, copy=True), diagnostics


def fit_arch_family(
    train_returns: pd.Series,
    full_returns: pd.Series,
    forecast_steps: int,
    output_dir: Path,
) -> tuple[dict[str, np.ndarray], pd.DataFrame, pd.DataFrame, list[str]]:
    predictions: dict[str, np.ndarray] = {}
    summary_rows: list[dict[str, float | str]] = []
    conditional_rows: list[pd.DataFrame] = []
    notes: list[str] = []

    if not HAS_ARCH or arch_model is None:
        note = "arch package unavailable; GARCH/EGARCH artifacts contain degraded placeholders."
        notes.append(note)
        (output_dir / "garch_summary.txt").write_text(note + "\n", encoding="utf-8")
        (output_dir / "egarch_summary.txt").write_text(note + "\n", encoding="utf-8")
        empty_parameters = pd.DataFrame(columns=["model", "parameter", "estimate"])
        empty_conditional = pd.DataFrame(columns=["date_index", "model", "conditional_volatility"])
        return predictions, empty_parameters, empty_conditional, notes

    scaled_train = train_returns.astype(float) * 100.0
    scaled_full = full_returns.astype(float) * 100.0
    specs = {
        "garch_1_1": {"vol": "GARCH", "p": 1, "o": 0, "q": 1},
        "egarch_1_1": {"vol": "EGARCH", "p": 1, "o": 0, "q": 1},
    }

    for model_name, spec in specs.items():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fitted = arch_model(scaled_train, mean="Zero", dist="normal", **spec).fit(disp="off")
            full_fit = arch_model(scaled_full, mean="Zero", dist="normal", **spec).fit(disp="off")

        forecast_method = "simulation" if model_name == "egarch_1_1" else "analytic"
        forecast = fitted.forecast(horizon=forecast_steps, method=forecast_method, simulations=200, reindex=False)
        variance = np.asarray(forecast.variance.iloc[-1], dtype=float)
        predictions[model_name] = np.sqrt(np.maximum(variance, 1e-10)) / 100.0

        summary_rows.extend(
            {
                "model": model_name,
                "parameter": str(parameter),
                "estimate": float(value),
            }
            for parameter, value in fitted.params.items()
        )
        conditional_rows.append(
            pd.DataFrame(
                {
                    "date_index": np.arange(len(scaled_full), dtype=int),
                    "model": model_name,
                    "conditional_volatility": np.asarray(full_fit.conditional_volatility, dtype=float) / 100.0,
                }
            )
        )

        summary_file = "garch_summary.txt" if model_name == "garch_1_1" else "egarch_summary.txt"
        (output_dir / summary_file).write_text(str(fitted.summary()) + "\n", encoding="utf-8")

    conditional = pd.concat(conditional_rows, ignore_index=True) if conditional_rows else pd.DataFrame()
    return predictions, pd.DataFrame(summary_rows), conditional, notes


def fit_gradient_boosting_baseline(
    train_frame: pd.DataFrame,
    test_frame: pd.DataFrame,
    seed: int,
) -> tuple[np.ndarray, list[str], GradientBoostingRegressor]:
    excluded_columns = {"date", "target_realized_volatility", "true_volatility"}
    feature_columns = [column for column in train_frame.columns if column not in excluded_columns]

    model = GradientBoostingRegressor(
        n_estimators=250,
        learning_rate=0.05,
        max_depth=2,
        min_samples_leaf=5,
        subsample=0.9,
        random_state=seed,
    )
    model.fit(train_frame[feature_columns], train_frame["target_realized_volatility"])
    predictions = np.maximum(model.predict(test_frame[feature_columns]), 1e-8)
    return predictions, feature_columns, model


def build_tft_proxy_outputs(
    gb_forecast: np.ndarray,
    feature_columns: list[str],
    model: GradientBoostingRegressor,
    test_frame: pd.DataFrame,
    output_dir: Path,
) -> np.ndarray:
    # The heavyweight TFT stack is optional for this asset library; when absent,
    # a tree-based proxy keeps the artifact contract deterministic and explicit.
    tft_predictions = pd.DataFrame(
        {
            "date": test_frame["date"].to_numpy(),
            "model": "degraded_tft_proxy_gradient_boosting",
            "forecast_volatility": gb_forecast,
            "implementation_note": "pytorch-forecasting unavailable; GradientBoostingRegressor used as TFT proxy",
        }
    )
    tft_predictions.to_csv(output_dir / "tft_predictions.csv", index=False)

    importances = np.asarray(model.feature_importances_, dtype=float)
    total = float(importances.sum()) or 1.0
    attention = pd.DataFrame(
        {
            "feature": feature_columns,
            "proxy_attention_weight": importances / total,
            "implementation_note": "feature importance proxy for TFT attention weights",
        }
    ).sort_values("proxy_attention_weight", ascending=False)
    attention.to_csv(output_dir / "tft_attention_weights.csv", index=False)
    return gb_forecast


def qlike_loss(actual_volatility: pd.Series, predicted_volatility: np.ndarray) -> float:
    actual_variance = np.maximum(np.square(actual_volatility.to_numpy(dtype=float)), 1e-10)
    predicted_variance = np.maximum(np.square(np.asarray(predicted_volatility, dtype=float)), 1e-10)
    return float(np.mean(np.log(predicted_variance) + actual_variance / predicted_variance))


def build_comparison_table(actual: pd.Series, predictions: dict[str, np.ndarray]) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    for model_name, values in predictions.items():
        rmse = float(np.sqrt(mean_squared_error(actual, values)))
        mae = float(mean_absolute_error(actual, values))
        rows.append({"model": model_name, "rmse": rmse, "mae": mae, "qlike": qlike_loss(actual, values)})
    table = pd.DataFrame(rows).sort_values(["rmse", "mae"]).reset_index(drop=True)
    table["rank"] = np.arange(1, len(table) + 1)
    return table[["rank", "model", "rmse", "mae", "qlike"]]


def build_residual_diagnostics(
    arima_residuals: pd.Series,
    ljung_box_table: pd.DataFrame,
    arch_parameter_table: pd.DataFrame,
) -> pd.DataFrame:
    summary_rows = [
        {
            "section": "residual_summary",
            "metric": "residual_mean",
            "value": float(arima_residuals.mean()),
            "notes": "ARIMA(1,0,1) residual mean on training returns",
        },
        {
            "section": "residual_summary",
            "metric": "residual_std",
            "value": float(arima_residuals.std(ddof=1)),
            "notes": "ARIMA(1,0,1) residual standard deviation on training returns",
        },
    ]
    test_rows = [
        {
            "section": "arch_test",
            "metric": f"ljung_box_sq_resid_lag_{int(row['lag'])}",
            "value": float(row["pvalue"]),
            "notes": f"statistic={float(row['statistic']):.4f}; pvalue below 0.05 suggests ARCH effects remain",
        }
        for _, row in ljung_box_table.iterrows()
    ]
    parameter_rows = [
        {
            "section": "arch_parameter",
            "metric": f"{row.model}_{row.parameter}",
            "value": float(row.estimate),
            "notes": "arch package parameter estimate",
        }
        for row in arch_parameter_table.itertuples(index=False)
    ]
    return pd.DataFrame(summary_rows + test_rows + parameter_rows)


def save_volatility_plot(forecast_frame: pd.DataFrame, figure_path: Path) -> None:
    fig, axis = plt.subplots(figsize=(10, 5), constrained_layout=True)
    plot_columns = [
        ("actual_realized_volatility", "#111111", 2.0),
        ("garch_1_1_forecast", "#1f77b4", 1.6),
        ("egarch_1_1_forecast", "#9467bd", 1.6),
        ("gradient_boosting_forecast", "#d62728", 1.6),
        ("tft_proxy_forecast", "#2ca02c", 1.4),
    ]
    for column, color, width in plot_columns:
        if column in forecast_frame:
            _ = axis.plot(forecast_frame["date"], forecast_frame[column], label=column, color=color, linewidth=width)
    _ = axis.set_title("Actual vs predicted volatility")
    _ = axis.set_xlabel("Date")
    _ = axis.set_ylabel("Volatility")
    _ = axis.legend(frameon=False)
    axis.grid(alpha=0.25)
    fig.autofmt_xdate()
    fig.savefig(figure_path, dpi=160)
    plt.close(fig)


def write_summary(
    output_dir: Path,
    config: dict[str, Any],
    comparison_table: pd.DataFrame,
    diagnostics_table: pd.DataFrame,
    feature_columns: list[str],
    forecast_frame: pd.DataFrame,
    optional_notes: list[str],
) -> None:
    best_model = str(comparison_table.iloc[0]["model"])
    best_rmse = float(comparison_table.iloc[0]["rmse"])
    best_mae = float(comparison_table.iloc[0]["mae"])
    mode_label = "SMOKE TEST" if bool(config["smoke_test"]) else "FULL RUN"

    arch_rows = diagnostics_table[diagnostics_table["section"] == "arch_test"].copy()
    arch_lines = [f"- {row.metric}: pvalue={row.value:.4f}" for row in arch_rows.itertuples(index=False)]
    notes = optional_notes or ["arch package branch executed; TFT branch emitted degraded proxy artifacts."]

    lines = [
        f"case_id: {CASE_ID}",
        f"title: {CASE_TITLE}",
        f"mode: {mode_label}",
        f"seed: {int(config['seed'])}",
        f"n_obs: {int(config['n_obs'])}",
        "implementation_note: best available branch uses arch GARCH/EGARCH; TFT artifacts use a documented proxy unless pytorch-forecasting is added.",
        f"claim_boundary: {CLAIM_BOUNDARY}",
        "",
        "Model comparison:",
        *[
            f"- {row.model}: RMSE={row.rmse:.6f}, MAE={row.mae:.6f}, QLIKE={row.qlike:.6f}"
            for row in comparison_table.itertuples(index=False)
        ],
        f"- best model: {best_model} (RMSE={best_rmse:.6f}, MAE={best_mae:.6f})",
        "",
        "Residual diagnostics for ARIMA baseline:",
        *arch_lines,
        "",
        "Optional dependency notes:",
        *[f"- {note}" for note in notes],
        "",
        "Feature design for ML/TFT proxy baseline:",
        f"- feature count: {len(feature_columns)}",
        f"- representative features: {', '.join(feature_columns[:8])}",
        "",
        "Output note:",
        f"- generated {len(forecast_frame)} out-of-sample forecasts in outputs/volatility_forecasts.csv",
    ]
    (output_dir / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    smoke_lines = [
        f"case_id: {CASE_ID}",
        f"mode: {mode_label}",
        f"seed: {int(config['seed'])}",
        f"observations: {int(config['n_obs'])}",
        f"forecast_rows: {len(forecast_frame)}",
        f"best_model: {best_model}",
        "status: smoke-compatible artifacts generated",
    ]
    (output_dir / "smoke_test.txt").write_text("\n".join(smoke_lines) + "\n", encoding="utf-8")


def run(smoke_test: bool = False) -> dict[str, Path]:
    paths = resolve_paths()
    params = load_params(paths["params_file"])
    config = build_run_config(params, smoke_test=smoke_test)

    raw_data = simulate_garch_like_returns(config)
    modeling_frame = build_modeling_frame(
        raw_data,
        rv_window=int(config["rv_window"]),
        lag_count=int(config["lag_count"]),
    )
    train_frame, test_frame = train_test_split_time_series(modeling_frame, test_size=float(config["test_size"]))

    arima_forecast, arima_residuals, ljung_box_table = fit_arima_baseline(
        train_returns=train_frame["returns"],
        forecast_steps=len(test_frame),
    )
    arch_predictions, arch_parameter_table, conditional_volatility, optional_notes = fit_arch_family(
        train_returns=train_frame["returns"],
        full_returns=modeling_frame["returns"],
        forecast_steps=len(test_frame),
        output_dir=paths["output_dir"],
    )
    conditional_volatility.to_csv(paths["output_dir"] / "conditional_volatility.csv", index=False)

    gb_forecast, feature_columns, gb_model = fit_gradient_boosting_baseline(
        train_frame=train_frame,
        test_frame=test_frame,
        seed=int(config["seed"]),
    )
    tft_proxy_forecast = build_tft_proxy_outputs(
        gb_forecast=gb_forecast,
        feature_columns=feature_columns,
        model=gb_model,
        test_frame=test_frame,
        output_dir=paths["output_dir"],
    )

    forecast_payload: dict[str, Any] = {
        "date": test_frame["date"].to_numpy(),
        "actual_realized_volatility": test_frame["target_realized_volatility"].to_numpy(),
        "arima_volatility_forecast": arima_forecast,
        "gradient_boosting_forecast": gb_forecast,
        "tft_proxy_forecast": tft_proxy_forecast,
        "returns": test_frame["returns"].to_numpy(),
        "true_volatility": test_frame["true_volatility"].to_numpy(),
    }
    for model_name, values in arch_predictions.items():
        forecast_payload[f"{model_name}_forecast"] = values
    forecast_frame = pd.DataFrame(forecast_payload)
    forecast_frame.to_csv(paths["output_dir"] / "volatility_forecasts.csv", index=False)

    prediction_map = {
        "arima_baseline": arima_forecast,
        "gradient_boosting": gb_forecast,
        "degraded_tft_proxy": tft_proxy_forecast,
        **arch_predictions,
    }
    comparison_table = build_comparison_table(actual=test_frame["target_realized_volatility"], predictions=prediction_map)
    comparison_table.to_csv(paths["output_dir"] / "model_comparison.csv", index=False)

    diagnostics_table = build_residual_diagnostics(
        arima_residuals=arima_residuals,
        ljung_box_table=ljung_box_table,
        arch_parameter_table=arch_parameter_table,
    )
    diagnostics_table.to_csv(paths["output_dir"] / "residual_diagnostics.csv", index=False)

    save_volatility_plot(forecast_frame=forecast_frame, figure_path=paths["output_dir"] / "volatility_paths.png")
    write_summary(
        output_dir=paths["output_dir"],
        config=config,
        comparison_table=comparison_table,
        diagnostics_table=diagnostics_table,
        feature_columns=feature_columns,
        forecast_frame=forecast_frame,
        optional_notes=optional_notes,
    )
    return paths


if __name__ == "__main__":
    cli_args = parse_args()
    generated_paths = run(smoke_test=bool(cli_args.smoke_test))
    print(f"Generated outputs in: {generated_paths['output_dir']}")
