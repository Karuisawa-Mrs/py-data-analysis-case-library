# pyright: reportMissingImports=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportCallIssue=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownLambdaType=false, reportMissingTypeArgument=false, reportExplicitAny=false, reportAny=false, reportUnusedCallResult=false

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


CASE_ID = "mkt-009-rfm-customer-segmentation"


@dataclass(frozen=True)
class SegmentArchetype:
    name: str
    share: float
    mean_orders: float
    recency_bias_days: int
    aov_mean: float
    aov_std: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RFM + K-means customer segmentation demo.")
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
        "k_selection_file": tables_dir / "k_selection.csv",
        "customer_segments_file": tables_dir / "customer_segments.csv",
        "segment_profiles_file": tables_dir / "segment_profiles.csv",
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


def build_archetypes() -> list[SegmentArchetype]:
    return [
        SegmentArchetype("champions", 0.24, 15.0, 8, 240.0, 45.0),
        SegmentArchetype("growth", 0.28, 8.0, 18, 130.0, 28.0),
        SegmentArchetype("premium_occasional", 0.18, 5.0, 40, 320.0, 70.0),
        SegmentArchetype("at_risk", 0.30, 3.5, 95, 85.0, 25.0),
    ]


def simulate_transactions(params: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    seed = int(params["seed"])
    n_customers = int(params["n_customers"])
    horizon_days = int(params["observation_days"])
    min_orders = int(params["min_orders_per_customer"])
    max_orders = int(params["max_orders_per_customer"])
    observation_end = pd.Timestamp(str(params["observation_end_date"]))
    horizon_start = observation_end - pd.Timedelta(days=horizon_days - 1)
    rng = np.random.default_rng(seed)

    archetypes = build_archetypes()
    probabilities = np.array([item.share for item in archetypes], dtype=float)
    probabilities = probabilities / probabilities.sum()
    archetype_index = rng.choice(len(archetypes), size=n_customers, p=probabilities)

    customer_rows: list[dict[str, Any]] = []
    transaction_rows: list[dict[str, Any]] = []
    order_counter = 1

    for idx in range(n_customers):
        customer_id = f"C{idx + 1:05d}"
        archetype = archetypes[int(archetype_index[idx])]
        lam = max(archetype.mean_orders, 1.0)
        order_count = int(np.clip(rng.poisson(lam=lam), min_orders, max_orders))
        recency = int(
            np.clip(
                rng.normal(loc=archetype.recency_bias_days, scale=max(archetype.recency_bias_days * 0.35, 4.0)),
                1,
                horizon_days - 1,
            )
        )
        latest_day = horizon_days - 1 - recency
        offsets = rng.beta(2.2, 1.8, size=order_count)
        purchase_days = np.clip(np.round(offsets * max(latest_day, 1)).astype(int), 0, latest_day)
        purchase_days[-1] = latest_day
        purchase_days.sort()

        total_amount = 0.0
        first_purchase_day = int(purchase_days[0])
        for purchase_day in purchase_days:
            order_date = horizon_start + pd.Timedelta(days=int(purchase_day))
            amount = float(
                np.clip(
                    rng.normal(loc=archetype.aov_mean, scale=archetype.aov_std),
                    a_min=20.0,
                    a_max=None,
                )
            )
            total_amount += amount
            transaction_rows.append(
                {
                    "customer_id": customer_id,
                    "order_id": f"ORD{order_counter:07d}",
                    "order_date": order_date.normalize(),
                    "order_amount": round(amount, 2),
                    "latent_segment": archetype.name,
                }
            )
            order_counter += 1

        customer_rows.append(
            {
                "customer_id": customer_id,
                "latent_segment": archetype.name,
                "first_purchase_date": (horizon_start + pd.Timedelta(days=first_purchase_day)).normalize(),
                "last_purchase_date": (horizon_start + pd.Timedelta(days=latest_day)).normalize(),
                "simulated_orders": order_count,
                "simulated_revenue": round(total_amount, 2),
            }
        )

    customers = pd.DataFrame(customer_rows).sort_values("customer_id").reset_index(drop=True)
    transactions = pd.DataFrame(transaction_rows).sort_values(["customer_id", "order_date", "order_id"]).reset_index(drop=True)
    return customers, transactions


def construct_rfm(transactions: pd.DataFrame, observation_end: pd.Timestamp) -> pd.DataFrame:
    df = transactions.copy()
    df["order_date"] = pd.to_datetime(df["order_date"])
    rfm = df.groupby("customer_id").agg(
        Recency=("order_date", lambda x: int((observation_end - x.max()).days)),
        Frequency=("order_id", "nunique"),
        Monetary=("order_amount", "sum"),
        AvgOrderValue=("order_amount", "mean"),
        FirstPurchase=("order_date", "min"),
        LastPurchase=("order_date", "max"),
    )
    rfm = rfm.reset_index()
    rfm["Monetary"] = rfm["Monetary"].round(2)
    rfm["AvgOrderValue"] = rfm["AvgOrderValue"].round(2)
    return rfm


def build_model_matrix(rfm: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    features = rfm[["Recency", "Frequency", "Monetary"]].copy()
    transformed = pd.DataFrame(
        {
            "log_recency": np.log1p(features["Recency"]),
            "log_frequency": np.log1p(features["Frequency"]),
            "log_monetary": np.log1p(features["Monetary"]),
        },
        index=rfm.index,
    )
    scaler = StandardScaler()
    scaled = pd.DataFrame(
        scaler.fit_transform(transformed),
        columns=["scaled_recency", "scaled_frequency", "scaled_monetary"],
        index=rfm.index,
    )
    return transformed, scaled


def evaluate_k_grid(scaled_features: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
    seed = int(params["seed"])
    min_k = int(params["min_k"])
    max_k = int(params["max_k"])
    n_init = int(params["n_init"])

    rows: list[dict[str, Any]] = []
    x = scaled_features.to_numpy()
    for k in range(min_k, max_k + 1):
        model = KMeans(n_clusters=k, n_init=n_init, random_state=seed)
        labels = model.fit_predict(x)
        rows.append(
            {
                "k": k,
                "inertia": float(model.inertia_),
                "silhouette": float(silhouette_score(x, labels)),
            }
        )

    metrics = pd.DataFrame(rows)
    metrics["inertia_drop"] = metrics["inertia"].shift(1) - metrics["inertia"]
    metrics["inertia_drop_pct"] = metrics["inertia_drop"] / metrics["inertia"].shift(1)
    metrics["elbow_score"] = metrics["inertia_drop"] - metrics["inertia_drop"].shift(-1)
    return metrics


def choose_optimal_k(k_metrics: pd.DataFrame) -> tuple[int, int, int]:
    silhouette_row = k_metrics.loc[k_metrics["silhouette"].idxmax()]
    elbow_candidates = k_metrics.dropna(subset=["elbow_score"])
    elbow_row = elbow_candidates.loc[elbow_candidates["elbow_score"].idxmax()] if not elbow_candidates.empty else silhouette_row

    silhouette_k = int(silhouette_row["k"])
    elbow_k = int(elbow_row["k"])
    chosen_k = silhouette_k if abs(silhouette_k - elbow_k) <= 1 else elbow_k
    return chosen_k, elbow_k, silhouette_k


def assign_segment_name(row: pd.Series) -> str:
    if row["recency_rank"] <= 1 and row["frequency_rank"] >= 3 and row["monetary_rank"] >= 3:
        return "核心高价值客户"
    if row["recency_rank"] >= 3 and row["frequency_rank"] <= 2 and row["monetary_rank"] <= 2:
        return "沉睡/流失风险客户"
    if row["monetary_rank"] >= 3 and row["frequency_rank"] <= 2:
        return "高客单价机会客户"
    return "成长培育客户"


def strategy_for_segment(segment_name: str) -> str:
    mapping = {
        "核心高价值客户": "优先做会员分层、专属新品试用与高毛利交叉销售，重点保持服务体验。",
        "沉睡/流失风险客户": "触发召回优惠、短信/邮件再营销与流失预警，降低长期沉默比例。",
        "高客单价机会客户": "推送高端组合包与个性化推荐，目标是提高复购频次而非单次折价。",
        "成长培育客户": "通过首购后自动化培育、积分激励与内容触达，把近期活跃转化为稳定复购。",
    }
    return mapping.get(segment_name, "基于群组画像设计差异化触达与预算分配。")


def profile_segments(rfm: pd.DataFrame, labels: np.ndarray) -> tuple[pd.DataFrame, pd.DataFrame]:
    result = rfm.copy()
    result["cluster"] = labels.astype(int)

    profiles = (
        result.groupby("cluster")
        .agg(
            customers=("customer_id", "count"),
            mean_recency=("Recency", "mean"),
            median_recency=("Recency", "median"),
            mean_frequency=("Frequency", "mean"),
            median_frequency=("Frequency", "median"),
            mean_monetary=("Monetary", "mean"),
            median_monetary=("Monetary", "median"),
            mean_aov=("AvgOrderValue", "mean"),
        )
        .reset_index()
    )
    profiles["share"] = profiles["customers"] / profiles["customers"].sum()

    profiles["recency_rank"] = profiles["mean_recency"].rank(method="dense", ascending=True).astype(int)
    profiles["frequency_rank"] = profiles["mean_frequency"].rank(method="dense", ascending=True).astype(int)
    profiles["monetary_rank"] = profiles["mean_monetary"].rank(method="dense", ascending=True).astype(int)
    profiles["segment_name"] = profiles.apply(assign_segment_name, axis=1)
    profiles["strategy_suggestion"] = profiles["segment_name"].map(strategy_for_segment)

    label_map = dict(zip(profiles["cluster"], profiles["segment_name"], strict=True))
    result["segment_name"] = result["cluster"].map(label_map)

    numeric_cols = [
        "mean_recency",
        "median_recency",
        "mean_frequency",
        "median_frequency",
        "mean_monetary",
        "median_monetary",
        "mean_aov",
        "share",
    ]
    profiles[numeric_cols] = profiles[numeric_cols].round(3)
    return result, profiles.sort_values(["segment_name", "cluster"]).reset_index(drop=True)


def run_analysis(smoke_test: bool = False) -> dict[str, Any]:
    paths = resolve_paths()
    params = load_params(paths["params_file"], smoke_test=smoke_test)
    observation_end = pd.Timestamp(str(params["observation_end_date"]))
    customers, transactions = simulate_transactions(params)
    rfm = construct_rfm(transactions, observation_end=observation_end)
    rfm = rfm.merge(customers[["customer_id", "latent_segment"]], on="customer_id", how="left")

    transformed, scaled = build_model_matrix(rfm)
    k_metrics = evaluate_k_grid(scaled, params)
    chosen_k, elbow_k, silhouette_k = choose_optimal_k(k_metrics)

    seed = int(params["seed"])
    n_init = int(params["n_init"])
    final_model = KMeans(n_clusters=chosen_k, n_init=n_init, random_state=seed)
    labels = final_model.fit_predict(scaled.to_numpy())
    silhouette_value = float(silhouette_score(scaled.to_numpy(), labels))

    clustered_customers, profiles = profile_segments(rfm, labels)
    final_output = pd.concat([clustered_customers, transformed, scaled], axis=1)

    k_metrics.to_csv(paths["k_selection_file"], index=False, encoding="utf-8-sig")
    final_output.to_csv(paths["customer_segments_file"], index=False, encoding="utf-8-sig")
    profiles.to_csv(paths["segment_profiles_file"], index=False, encoding="utf-8-sig")

    strategy_lines = [
        f"- Cluster {int(row.cluster)} / {row.segment_name}: {row.strategy_suggestion}"
        for row in profiles.itertuples(index=False)
    ]

    profile_lines = [
        (
            f"- Cluster {int(row.cluster)} / {row.segment_name}: customers={int(row.customers)}, "
            f"share={row.share:.3f}, mean_recency={row.mean_recency:.1f}, "
            f"mean_frequency={row.mean_frequency:.1f}, mean_monetary={row.mean_monetary:.1f}"
        )
        for row in profiles.itertuples(index=False)
    ]

    summary_lines = [
        f"case_id: {CASE_ID}",
        f"mode: {'SMOKE TEST' if smoke_test else 'FULL RUN'}",
        f"customers: {len(customers)}",
        f"transactions: {len(transactions)}",
        f"observation_end_date: {observation_end.date().isoformat()}",
        f"k_grid: {int(params['min_k'])}-{int(params['max_k'])}",
        f"elbow_k: {elbow_k}",
        f"silhouette_k: {silhouette_k}",
        f"selected_k: {chosen_k}",
        f"selected_model_inertia: {float(final_model.inertia_):.6f}",
        f"selected_model_silhouette: {silhouette_value:.6f}",
        f"top_silhouette_value: {float(k_metrics['silhouette'].max()):.6f}",
        "segment_profiles:",
        *profile_lines,
        "",
        "strategy_suggestions:",
        *strategy_lines,
        "",
        "notes:",
        "- RFM aggregation follows the common pattern: recency = snapshot_date - last_purchase_date, frequency = order count, monetary = revenue sum.",
        "- K selection follows common K-means practice from public examples: compare inertia (elbow) and silhouette across a candidate grid.",
        "- Results are instructional and should not be interpreted as causal evidence.",
    ]
    paths["summary_file"].write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    if smoke_test:
        smoke_lines = [
            f"case_id: {CASE_ID}",
            f"customers: {len(customers)}",
            f"transactions: {len(transactions)}",
            f"selected_k: {chosen_k}",
            f"selected_model_silhouette: {silhouette_value:.6f}",
            f"summary_file: {paths['summary_file'].name}",
        ]
        paths["smoke_file"].write_text("\n".join(smoke_lines) + "\n", encoding="utf-8")

    return {
        "paths": paths,
        "customers": customers,
        "transactions": transactions,
        "rfm": rfm,
        "k_metrics": k_metrics,
        "profiles": profiles,
        "selected_k": chosen_k,
    }


if __name__ == "__main__":
    args = parse_args()
    result = run_analysis(smoke_test=bool(args.smoke_test))
    print(f"Generated: {result['paths']['summary_file']}")
    if args.smoke_test:
        print(f"Generated: {result['paths']['smoke_file']}")
