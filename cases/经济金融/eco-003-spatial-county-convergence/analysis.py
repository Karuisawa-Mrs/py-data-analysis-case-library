# pyright: reportMissingImports=false

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from esda import Moran, Moran_Local
from libpysal.weights import W, lag_spatial
from spreg import ML_Lag


CASE_ID = "eco-003-spatial-county-convergence"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Spatial county convergence demo with Moran's I, LISA, and SDM."
    )
    _ = parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run a lightweight version for repository validation.",
    )
    return parser.parse_args()


def resolve_paths() -> dict[str, Path]:
    case_dir = Path(__file__).resolve().parent
    output_dir = case_dir / "outputs"
    tables_dir = output_dir / "tables"
    output_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    return {
        "case_dir": case_dir,
        "data_dir": case_dir / "data",
        "output_dir": output_dir,
        "tables_dir": tables_dir,
        "params_file": case_dir / "params.yaml",
        "summary_file": output_dir / "summary.txt",
        "smoke_file": output_dir / "smoke_test.txt",
        "model_table": tables_dir / "model_data.csv",
        "lisa_table": tables_dir / "lisa_clusters.csv",
    }


def load_params(params_file: Path, smoke_test: bool) -> dict[str, Any]:
    config = yaml.safe_load(params_file.read_text(encoding="utf-8")) or {}
    if not isinstance(config, dict):
        raise ValueError("params.yaml must parse to a mapping")

    run_cfg = dict(config)
    smoke_cfg = run_cfg.pop("smoke_test", {}) if smoke_test else {}
    if isinstance(smoke_cfg, dict):
        run_cfg.update(smoke_cfg)
    return run_cfg


def normalize_county_name(value: str) -> str:
    return value.replace("\n", "").replace(" ", "").strip()


def load_data(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    panel = pd.read_csv(data_dir / "county_panel.csv")
    adjacency = pd.read_csv(data_dir / "county_adjacency.csv")

    panel["county"] = panel["county"].map(normalize_county_name)
    adjacency["source"] = adjacency["source"].map(normalize_county_name)
    adjacency["target"] = adjacency["target"].map(normalize_county_name)
    return panel, adjacency


def build_weights(counties: list[str], adjacency: pd.DataFrame) -> W:
    neighbors: dict[str, list[str]] = {county: [] for county in counties}
    for source, target in adjacency[["source", "target"]].itertuples(index=False, name=None):
        source = str(source)
        target = str(target)
        if source not in neighbors or target not in neighbors:
            raise ValueError(f"adjacency references unknown county pair: {source}, {target}")
        neighbors[source].append(target)
        neighbors[target].append(source)

    if any(len(v) == 0 for v in neighbors.values()):
        empty = [k for k, v in neighbors.items() if not v]
        raise ValueError(f"isolated counties found in adjacency list: {empty}")

    weights = W(neighbors, id_order=counties)
    weights.transform = "r"
    return weights


def engineer_features(panel: pd.DataFrame, start_year: int, end_year: int) -> pd.DataFrame:
    years = end_year - start_year
    if years <= 0:
        raise ValueError("end_year must be greater than start_year")

    df = panel.copy()
    df["gdp_growth_pct"] = ((df["gdp_2025"] / df["gdp_2019"]) ** (1 / years) - 1) * 100
    df["log_gdp_2019"] = np.log(df["gdp_2019"])
    df["log_fiscal_2019"] = np.log(df["fiscal_2019"])
    df["urban_rural_ratio_2019"] = df["urban_income_2019"] / df["rural_income_2019"]
    return df


def classify_lisa(quadrant: int, significant: bool) -> str:
    if not significant:
        return "Not significant"
    return {
        1: "High-High",
        2: "Low-High",
        3: "Low-Low",
        4: "High-Low",
    }.get(int(quadrant), "Unknown")


def run_analysis(smoke_test: bool = False) -> dict[str, Any]:
    paths = resolve_paths()
    params = load_params(paths["params_file"], smoke_test=smoke_test)
    panel, adjacency = load_data(paths["data_dir"])

    df = engineer_features(
        panel,
        start_year=int(params["analysis_year_start"]),
        end_year=int(params["analysis_year_end"]),
    )
    counties = df["county"].tolist()
    weights = build_weights(counties, adjacency)

    permutations = int(params["moran_permutations"])
    lisa_alpha = float(params["lisa_alpha"])
    seed = int(params["seed"])
    sdm_method = str(params["sdm_method"])

    y = df["gdp_growth_pct"].to_numpy()
    np.random.seed(seed)
    moran = Moran(y, weights, permutations=permutations)
    local = Moran_Local(y, weights, permutations=permutations, seed=seed)

    df["spatial_lag_growth_pct"] = lag_spatial(weights, y)
    df["lisa_p_value"] = local.p_sim
    df["lisa_quadrant"] = local.q
    df["lisa_cluster"] = [
        classify_lisa(int(quadrant), bool(p_value < lisa_alpha))
        for quadrant, p_value in zip(local.q, local.p_sim, strict=True)
    ]

    x_columns = ["log_gdp_2019", "log_fiscal_2019"]
    x = df[x_columns].to_numpy()
    reg = ML_Lag(
        y.reshape((-1, 1)),
        x,
        w=weights,
        slx_lags=1,
        method=sdm_method,
        name_y="gdp_growth_pct",
        name_x=x_columns,
        name_w="xinzhou_manual_adjacency",
        name_ds=CASE_ID,
    )

    df.to_csv(paths["model_table"], index=False, encoding="utf-8-sig")
    df[["county", "gdp_growth_pct", "spatial_lag_growth_pct", "lisa_p_value", "lisa_cluster"]].to_csv(
        paths["lisa_table"],
        index=False,
        encoding="utf-8-sig",
    )

    significant_clusters = df.loc[df["lisa_cluster"] != "Not significant", ["county", "lisa_cluster", "lisa_p_value"]]
    cluster_lines = [
        f"- {row.county}: {row.lisa_cluster} (p={row.lisa_p_value:.4f})"
        for row in significant_clusters.itertuples(index=False)
    ] or ["- no significant local clusters under the configured alpha"]

    summary_lines = [
        f"case_id: {CASE_ID}",
        f"mode: {'SMOKE TEST' if smoke_test else 'FULL RUN'}",
        f"sample_counties: {len(df)}",
        f"period: {int(params['analysis_year_start'])}-{int(params['analysis_year_end'])}",
        f"weights: manual contiguity list, row-standardized ({adjacency.shape[0]} undirected edges)",
        f"global_moran_i: {moran.I:.6f}",
        f"global_moran_p_sim: {moran.p_sim:.6f}",
        f"growth_mean_pct: {df['gdp_growth_pct'].mean():.4f}",
        f"growth_std_pct: {df['gdp_growth_pct'].std(ddof=1):.4f}",
        f"sdm_rho: {float(reg.rho):.6f}",
        f"sdm_aic: {float(reg.aic):.6f}",
        "significant_lisa_clusters:",
        *cluster_lines,
        "",
        "sdm_summary:",
        str(getattr(reg, "summary", "summary unavailable")).strip(),
    ]

    paths["summary_file"].write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    if smoke_test:
        smoke_lines = [
            f"case_id: {CASE_ID}",
            f"sample_counties: {len(df)}",
            f"global_moran_i: {moran.I:.6f}",
            f"global_moran_p_sim: {moran.p_sim:.6f}",
            f"sdm_rho: {float(reg.rho):.6f}",
            f"summary_file: {paths['summary_file'].name}",
        ]
        paths["smoke_file"].write_text("\n".join(smoke_lines) + "\n", encoding="utf-8")

    return {
        "paths": paths,
        "moran": moran,
        "local": local,
        "reg": reg,
        "data": df,
    }


if __name__ == "__main__":
    args = parse_args()
    result = run_analysis(smoke_test=bool(args.smoke_test))
    print(f"Generated: {result['paths']['summary_file']}")
    if args.smoke_test:
        print(f"Generated: {result['paths']['smoke_file']}")
