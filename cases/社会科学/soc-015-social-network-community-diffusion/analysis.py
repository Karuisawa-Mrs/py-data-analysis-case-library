from __future__ import annotations

# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false, reportMissingTypeArgument=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportOptionalMemberAccess=false, reportArgumentType=false, reportMissingTypeStubs=false, reportUnusedCallResult=false, reportAny=false, reportExplicitAny=false

import argparse
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import yaml

matplotlib.use("Agg")

import matplotlib.pyplot as plt

try:
    import networkx as nx
except ModuleNotFoundError:  # pragma: no cover - fallback path is the contract
    nx = None


CASE_ID = "soc-015-social-network-community-diffusion"
CASE_TITLE = "社区结构与信息扩散：社会网络分析"
DATA_MODE = "simulated"
REPLICATION_TYPE = "illustration"
CLAIM_BOUNDARY = "该案例演示社会网络与扩散分析流程，不替代真实社会网络经验研究结论。"


@dataclass(frozen=True)
class CaseConfig:
    seed: int
    output_dir: str
    node_count_full: int = 300
    node_count_smoke: int = 60
    intra_prob_full: float = 0.14
    inter_prob_full: float = 0.018
    intra_prob_smoke: float = 0.18
    inter_prob_smoke: float = 0.03
    diffusion_infection_prob: float = 0.24
    diffusion_steps_full: int = 12
    diffusion_steps_smoke: int = 8
    top_seed_count: int = 3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulate a three-community social network, compute centrality and community structure, and run SI diffusion."
    )
    _ = parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run a reduced but complete network-analysis pipeline for automated validation.",
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

    return CaseConfig(
        seed=int(payload["seed"]),
        output_dir=str(payload.get("output_dir", "outputs")),
        node_count_full=int(payload.get("node_count_full", 300)),
        node_count_smoke=int(payload.get("node_count_smoke", 60)),
        intra_prob_full=float(payload.get("intra_prob_full", 0.14)),
        inter_prob_full=float(payload.get("inter_prob_full", 0.018)),
        intra_prob_smoke=float(payload.get("intra_prob_smoke", 0.18)),
        inter_prob_smoke=float(payload.get("inter_prob_smoke", 0.03)),
        diffusion_infection_prob=float(payload.get("diffusion_infection_prob", 0.24)),
        diffusion_steps_full=int(payload.get("diffusion_steps_full", 12)),
        diffusion_steps_smoke=int(payload.get("diffusion_steps_smoke", 8)),
        top_seed_count=int(payload.get("top_seed_count", 3)),
    )


def build_sbm_adjacency(config: CaseConfig, smoke_test: bool) -> tuple[np.ndarray, np.ndarray]:
    node_count = config.node_count_smoke if smoke_test else config.node_count_full
    intra_prob = config.intra_prob_smoke if smoke_test else config.intra_prob_full
    inter_prob = config.inter_prob_smoke if smoke_test else config.inter_prob_full
    rng = np.random.default_rng(config.seed + (17 if smoke_test else 0))

    sizes = distribute_nodes(node_count=node_count, groups=3)
    planted = np.concatenate([np.full(size, idx, dtype=int) for idx, size in enumerate(sizes)])
    probability_matrix = np.full((3, 3), inter_prob, dtype=float)
    np.fill_diagonal(probability_matrix, intra_prob)

    draws = rng.random((node_count, node_count))
    community_probs = probability_matrix[planted][:, planted]
    upper_mask = np.triu(np.ones((node_count, node_count), dtype=bool), k=1)
    adjacency = ((draws < community_probs) & upper_mask).astype(int)
    adjacency = adjacency + adjacency.T
    np.fill_diagonal(adjacency, 0)

    return adjacency, planted


def distribute_nodes(*, node_count: int, groups: int) -> list[int]:
    base = node_count // groups
    remainder = node_count % groups
    return [base + (1 if idx < remainder else 0) for idx in range(groups)]


def adjacency_to_neighbors(adjacency: np.ndarray) -> list[list[int]]:
    return [np.flatnonzero(adjacency[node]).astype(int).tolist() for node in range(adjacency.shape[0])]


def connected_components(neighbors: list[list[int]]) -> list[list[int]]:
    seen: set[int] = set()
    components: list[list[int]] = []
    for start in range(len(neighbors)):
        if start in seen:
            continue
        queue = deque([start])
        seen.add(start)
        component: list[int] = []
        while queue:
            node = queue.popleft()
            component.append(node)
            for nbr in neighbors[node]:
                if nbr not in seen:
                    seen.add(nbr)
                    queue.append(nbr)
        components.append(component)
    return components


def shortest_path_lengths(source: int, neighbors: list[list[int]]) -> tuple[np.ndarray, list[int]]:
    n_nodes = len(neighbors)
    distances = np.full(n_nodes, -1, dtype=int)
    distances[source] = 0
    queue = deque([source])
    visit_order = [source]

    while queue:
        node = queue.popleft()
        for nbr in neighbors[node]:
            if distances[nbr] == -1:
                distances[nbr] = distances[node] + 1
                queue.append(nbr)
                visit_order.append(nbr)
    return distances, visit_order


def degree_centrality(adjacency: np.ndarray) -> np.ndarray:
    n_nodes = adjacency.shape[0]
    degrees = adjacency.sum(axis=1).astype(float)
    denom = max(n_nodes - 1, 1)
    return degrees / denom


def closeness_centrality(neighbors: list[list[int]]) -> np.ndarray:
    n_nodes = len(neighbors)
    centrality = np.zeros(n_nodes, dtype=float)
    for node in range(n_nodes):
        distances, _ = shortest_path_lengths(node, neighbors)
        reachable = distances[distances >= 0]
        if len(reachable) <= 1:
            centrality[node] = 0.0
            continue
        total_distance = float(reachable.sum())
        reach_factor = (len(reachable) - 1) / max(n_nodes - 1, 1)
        centrality[node] = reach_factor * (len(reachable) - 1) / total_distance if total_distance > 0 else 0.0
    return centrality


def betweenness_centrality(neighbors: list[list[int]]) -> np.ndarray:
    n_nodes = len(neighbors)
    betweenness = np.zeros(n_nodes, dtype=float)
    for source in range(n_nodes):
        stack: list[int] = []
        predecessors: list[list[int]] = [[] for _ in range(n_nodes)]
        sigma = np.zeros(n_nodes, dtype=float)
        sigma[source] = 1.0
        distance = np.full(n_nodes, -1, dtype=int)
        distance[source] = 0
        queue = deque([source])

        while queue:
            node = queue.popleft()
            stack.append(node)
            for nbr in neighbors[node]:
                if distance[nbr] < 0:
                    queue.append(nbr)
                    distance[nbr] = distance[node] + 1
                if distance[nbr] == distance[node] + 1:
                    sigma[nbr] += sigma[node]
                    predecessors[nbr].append(node)

        dependency = np.zeros(n_nodes, dtype=float)
        while stack:
            node = stack.pop()
            for pred in predecessors[node]:
                if sigma[node] > 0:
                    dependency[pred] += (sigma[pred] / sigma[node]) * (1.0 + dependency[node])
            if node != source:
                betweenness[node] += dependency[node]

    if n_nodes > 2:
        betweenness /= (n_nodes - 1) * (n_nodes - 2) / 2
    return betweenness


def power_iteration(matrix: np.ndarray, *, damping: float | None = None, max_iter: int = 200, tol: float = 1e-8) -> np.ndarray:
    n_nodes = matrix.shape[0]
    vector = np.full(n_nodes, 1.0 / max(n_nodes, 1), dtype=float)

    if damping is None:
        operator = matrix.astype(float)
    else:
        row_sums = matrix.sum(axis=1, keepdims=True).astype(float)
        stochastic = np.divide(
            matrix.astype(float),
            row_sums,
            out=np.full_like(matrix.astype(float), 1.0 / max(n_nodes, 1)),
            where=row_sums > 0,
        )
        operator = damping * stochastic.T + (1.0 - damping) / max(n_nodes, 1)

    for _ in range(max_iter):
        next_vector = operator @ vector
        if damping is None:
            norm = float(np.linalg.norm(next_vector, ord=2))
            if np.isclose(norm, 0.0):
                next_vector = np.full(n_nodes, 1.0 / max(n_nodes, 1), dtype=float)
            else:
                next_vector = next_vector / norm
        else:
            next_vector = next_vector / max(float(next_vector.sum()), 1e-12)
        if float(np.linalg.norm(next_vector - vector, ord=1)) < tol:
            vector = next_vector
            break
        vector = next_vector
    return vector


def eigenvector_centrality(adjacency: np.ndarray) -> np.ndarray:
    vector = power_iteration(adjacency.astype(float), damping=None)
    vector = np.abs(vector)
    scale = float(vector.max())
    return vector / scale if scale > 0 else vector


def pagerank_centrality(adjacency: np.ndarray) -> np.ndarray:
    return power_iteration(adjacency.astype(float), damping=0.85)


def clustering_coefficient(adjacency: np.ndarray, neighbors: list[list[int]]) -> np.ndarray:
    coefficients = np.zeros(len(neighbors), dtype=float)
    for node, nbrs in enumerate(neighbors):
        degree = len(nbrs)
        if degree < 2:
            coefficients[node] = 0.0
            continue
        subgraph = adjacency[np.ix_(nbrs, nbrs)]
        triangles = float(subgraph.sum() / 2)
        coefficients[node] = (2.0 * triangles) / (degree * (degree - 1))
    return coefficients


def graph_density(adjacency: np.ndarray) -> float:
    n_nodes = adjacency.shape[0]
    if n_nodes < 2:
        return 0.0
    edges = float(adjacency.sum() / 2)
    return (2.0 * edges) / (n_nodes * (n_nodes - 1))


def graph_diameter(neighbors: list[list[int]]) -> int:
    components = connected_components(neighbors)
    largest = max(components, key=len)
    diameter = 0
    for node in largest:
        distances, _ = shortest_path_lengths(node, neighbors)
        reachable = distances[np.array(largest, dtype=int)]
        diameter = max(diameter, int(reachable.max()))
    return diameter


def modularity_score(adjacency: np.ndarray, labels: np.ndarray) -> float:
    degrees = adjacency.sum(axis=1).astype(float)
    total_edge_weight = float(adjacency.sum() / 2)
    if np.isclose(total_edge_weight, 0.0):
        return 0.0
    same = labels[:, None] == labels[None, :]
    expected = np.outer(degrees, degrees) / (2.0 * total_edge_weight)
    modularity_matrix = adjacency.astype(float) - expected
    return float(modularity_matrix[same].sum() / (2.0 * total_edge_weight))


def greedy_modularity_labels(adjacency: np.ndarray) -> np.ndarray:
    n_nodes = adjacency.shape[0]
    communities = [set([node]) for node in range(n_nodes)]
    current_labels = np.arange(n_nodes, dtype=int)
    current_score = modularity_score(adjacency, current_labels)

    while len(communities) > 1:
        best_pair: tuple[int, int] | None = None
        best_labels: np.ndarray | None = None
        best_score = current_score

        for left in range(len(communities) - 1):
            for right in range(left + 1, len(communities)):
                proposal = [set(group) for group in communities]
                proposal[left] |= proposal[right]
                proposal.pop(right)
                labels = communities_to_labels(proposal, n_nodes)
                score = modularity_score(adjacency, labels)
                if score > best_score + 1e-9:
                    best_score = score
                    best_pair = (left, right)
                    best_labels = labels

        if best_pair is None or best_labels is None:
            break

        communities[best_pair[0]] |= communities[best_pair[1]]
        communities.pop(best_pair[1])
        current_labels = best_labels
        current_score = best_score

    return relabel_labels(current_labels)


def communities_to_labels(communities: list[set[int]], n_nodes: int) -> np.ndarray:
    labels = np.full(n_nodes, -1, dtype=int)
    for label, members in enumerate(communities):
        for node in sorted(members):
            labels[node] = label
    if np.any(labels < 0):
        raise ValueError("Community label assignment failed.")
    return labels


def relabel_labels(labels: np.ndarray) -> np.ndarray:
    ordered = pd.Series(labels).astype(int)
    unique_labels = list(dict.fromkeys(ordered.tolist()))
    mapping = {old: new for new, old in enumerate(unique_labels)}
    return ordered.map(mapping).to_numpy(dtype=int)


def detect_communities(adjacency: np.ndarray, seed: int) -> tuple[np.ndarray, str]:
    if nx is not None:
        graph = nx.from_numpy_array(adjacency)
        if hasattr(nx.community, "louvain_communities"):
            communities = nx.community.louvain_communities(graph, seed=seed)
            labels = communities_to_labels([set(group) for group in communities], adjacency.shape[0])
            return relabel_labels(labels), "networkx-louvain"
    return greedy_modularity_labels(adjacency), "numpy-greedy-modularity"


def compute_network_metrics(adjacency: np.ndarray, detected_labels: np.ndarray) -> pd.DataFrame:
    neighbors = adjacency_to_neighbors(adjacency)
    rows = [
        {"metric": "node_count", "value": float(adjacency.shape[0])},
        {"metric": "edge_count", "value": float(adjacency.sum() / 2)},
        {"metric": "density", "value": graph_density(adjacency)},
        {"metric": "diameter", "value": float(graph_diameter(neighbors))},
        {
            "metric": "average_clustering_coefficient",
            "value": float(clustering_coefficient(adjacency, neighbors).mean()),
        },
        {"metric": "modularity", "value": modularity_score(adjacency, detected_labels)},
        {"metric": "detected_community_count", "value": float(pd.Series(detected_labels).nunique())},
    ]
    return pd.DataFrame(rows)


def compute_centralities(adjacency: np.ndarray) -> pd.DataFrame:
    neighbors = adjacency_to_neighbors(adjacency)
    centralities = pd.DataFrame(
        {
            "node_id": np.arange(adjacency.shape[0], dtype=int),
            "degree": degree_centrality(adjacency),
            "betweenness": betweenness_centrality(neighbors),
            "closeness": closeness_centrality(neighbors),
            "eigenvector": eigenvector_centrality(adjacency),
            "pagerank": pagerank_centrality(adjacency),
        }
    )
    for column in ["degree", "betweenness", "closeness", "eigenvector", "pagerank"]:
        centralities[f"{column}_rank"] = centralities[column].rank(method="min", ascending=False).astype(int)
    return centralities.sort_values(["degree_rank", "pagerank_rank", "node_id"]).reset_index(drop=True)


def simulate_si_diffusion(
    adjacency: np.ndarray,
    centralities: pd.DataFrame,
    config: CaseConfig,
    smoke_test: bool,
) -> pd.DataFrame:
    rng = np.random.default_rng(config.seed + (211 if smoke_test else 503))
    max_steps = config.diffusion_steps_smoke if smoke_test else config.diffusion_steps_full
    top_nodes = (
        centralities.sort_values(["degree", "pagerank", "node_id"], ascending=[False, False, True])
        .head(config.top_seed_count)["node_id"]
        .astype(int)
        .tolist()
    )

    infected = set(top_nodes)
    history = [
        {
            "step": 0,
            "new_infections": len(top_nodes),
            "infected_count": len(infected),
            "infected_share": len(infected) / adjacency.shape[0],
        }
    ]

    for step in range(1, max_steps + 1):
        new_infected: set[int] = set()
        for node in sorted(infected):
            for nbr in np.flatnonzero(adjacency[node]).astype(int).tolist():
                if nbr in infected or nbr in new_infected:
                    continue
                if rng.random() < config.diffusion_infection_prob:
                    new_infected.add(nbr)
        infected |= new_infected
        history.append(
            {
                "step": step,
                "new_infections": len(new_infected),
                "infected_count": len(infected),
                "infected_share": len(infected) / adjacency.shape[0],
            }
        )
        if len(infected) == adjacency.shape[0]:
            break

    return pd.DataFrame(history)


def layout_positions(labels: np.ndarray, seed: int) -> dict[int, tuple[float, float]]:
    rng = np.random.default_rng(seed)
    unique_labels = sorted(pd.Series(labels).unique().tolist())
    radius = 4.0
    positions: dict[int, tuple[float, float]] = {}
    for idx, community in enumerate(unique_labels):
        angle = (2.0 * np.pi * idx) / max(len(unique_labels), 1)
        center = np.array([radius * np.cos(angle), radius * np.sin(angle)])
        members = np.flatnonzero(labels == community)
        for member in members:
            jitter = rng.normal(0.0, 0.8, size=2)
            positions[int(member)] = (float(center[0] + jitter[0]), float(center[1] + jitter[1]))
    return positions


def draw_network_map(
    adjacency: np.ndarray,
    detected_labels: np.ndarray,
    planted_labels: np.ndarray,
    centralities: pd.DataFrame,
    output_path: Path,
    seed: int,
) -> None:
    fig, ax = plt.subplots(figsize=(10, 8))
    color_map = np.array(["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"])
    positions = layout_positions(detected_labels, seed)
    node_sizes = 180 + 1200 * centralities.set_index("node_id").loc[:, "degree"].to_numpy(dtype=float)

    for left in range(adjacency.shape[0] - 1):
        right_nodes = np.flatnonzero(adjacency[left, left + 1 :]).astype(int) + left + 1
        x0, y0 = positions[left]
        for right in right_nodes.tolist():
            x1, y1 = positions[right]
            ax.plot([x0, x1], [y0, y1], color="#bdbdbd", linewidth=0.5, alpha=0.25, zorder=1)

    for community in sorted(pd.Series(detected_labels).unique().tolist()):
        members = np.flatnonzero(detected_labels == community)
        xs = [positions[int(node)][0] for node in members]
        ys = [positions[int(node)][1] for node in members]
        ax.scatter(
            xs,
            ys,
            s=node_sizes[members],
            c=color_map[community % len(color_map)],
            alpha=0.9,
            edgecolors="white",
            linewidths=0.6,
            label=f"Detected community {community + 1}",
            zorder=2,
        )

    top_nodes = centralities.nsmallest(3, "degree_rank")["node_id"].astype(int).tolist()
    for node in top_nodes:
        x_pos, y_pos = positions[node]
        ax.text(x_pos, y_pos, str(node), fontsize=8, ha="center", va="center", color="black", zorder=3)

    planted_overlap = float(np.mean(planted_labels == relabel_labels(detected_labels)))
    ax.set_title(f"Simulated social network map (community alignment={planted_overlap:.2f})")
    ax.set_xlabel("Layout X")
    ax.set_ylabel("Layout Y")
    ax.legend(loc="upper right", fontsize=8, frameon=False)
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def build_community_assignments(
    adjacency: np.ndarray,
    planted_labels: np.ndarray,
    detected_labels: np.ndarray,
    centralities: pd.DataFrame,
) -> pd.DataFrame:
    degrees = adjacency.sum(axis=1).astype(int)
    assignments = pd.DataFrame(
        {
            "node_id": np.arange(adjacency.shape[0], dtype=int),
            "planted_community": planted_labels.astype(int),
            "detected_community": detected_labels.astype(int),
            "degree_count": degrees,
        }
    )
    return assignments.merge(centralities[["node_id", "degree", "pagerank"]], on="node_id", how="left")


def write_outputs(
    *,
    paths: dict[str, Path],
    config: CaseConfig,
    network_metrics: pd.DataFrame,
    assignments: pd.DataFrame,
    centralities: pd.DataFrame,
    diffusion: pd.DataFrame,
    figure_path: Path,
    detection_method: str,
    smoke_test: bool,
) -> dict[str, Path]:
    output_dir = paths["output_dir"]
    network_metrics_path = output_dir / "network_metrics.csv"
    assignments_path = output_dir / "community_assignments.csv"
    centralities_path = output_dir / "centrality_rankings.csv"
    summary_path = output_dir / "summary.txt"
    smoke_path = output_dir / "smoke_test.txt"

    network_metrics.to_csv(network_metrics_path, index=False, encoding="utf-8-sig")
    assignments.to_csv(assignments_path, index=False, encoding="utf-8-sig")
    centralities.to_csv(centralities_path, index=False, encoding="utf-8-sig")

    metric_lookup = network_metrics.set_index("metric")["value"]
    top_seed_nodes = (
        centralities.nsmallest(config.top_seed_count, "degree_rank")["node_id"].astype(int).tolist()
    )
    last_diffusion = diffusion.iloc[-1]
    diffusion_records = [
        {
            "step": int(row.step),
            "infected_count": int(row.infected_count),
        }
        for row in diffusion.loc[:, ["step", "infected_count"]].itertuples(index=False)
    ]

    summary_lines = [
        f"case_id: {CASE_ID}",
        f"title: {CASE_TITLE}",
        f"mode: {'SMOKE TEST' if smoke_test else 'FULL RUN'}",
        f"seed: {config.seed}",
        f"node_count: {int(metric_lookup['node_count'])}",
        f"edge_count: {int(metric_lookup['edge_count'])}",
        f"data_mode: {DATA_MODE}",
        f"replication_type: {REPLICATION_TYPE}",
        f"community_detection: {detection_method}",
        (
            "network_metrics: "
            f"density={metric_lookup['density']:.4f}, "
            f"diameter={metric_lookup['diameter']:.0f}, "
            f"average_clustering_coefficient={metric_lookup['average_clustering_coefficient']:.4f}, "
            f"modularity={metric_lookup['modularity']:.4f}"
        ),
        (
            "top_degree_seeds: "
            + ", ".join(str(node) for node in top_seed_nodes)
        ),
        (
            "diffusion_summary: "
            f"steps={int(last_diffusion['step'])}, "
            f"infected_count={int(last_diffusion['infected_count'])}, "
            f"infected_share={float(last_diffusion['infected_share']):.4f}"
        ),
        f"diffusion_reach_by_step: {diffusion_records}",
        f"artifacts: {network_metrics_path.name}, {assignments_path.name}, {centralities_path.name}, {figure_path.name}",
        f"claim_boundary: {CLAIM_BOUNDARY}",
    ]
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    smoke_lines = [
        f"case_id: {CASE_ID}",
        f"mode: {'SMOKE TEST' if smoke_test else 'FULL RUN'}",
        f"node_count: {int(metric_lookup['node_count'])}",
        f"detected_community_count: {int(metric_lookup['detected_community_count'])}",
        f"community_detection: {detection_method}",
        f"network_metrics: {network_metrics_path.name}",
        f"community_assignments: {assignments_path.name}",
        f"centrality_rankings: {centralities_path.name}",
        f"network_map: {figure_path.name}",
        f"summary: {summary_path.name}",
    ]
    smoke_path.write_text("\n".join(smoke_lines) + "\n", encoding="utf-8")

    return {
        "summary": summary_path,
        "smoke_test": smoke_path,
        "network_metrics": network_metrics_path,
        "community_assignments": assignments_path,
        "centrality_rankings": centralities_path,
        "network_map": figure_path,
    }


def run(smoke_test: bool = False) -> dict[str, Path]:
    paths = resolve_paths()
    config = load_config(paths["params_file"])
    adjacency, planted_labels = build_sbm_adjacency(config, smoke_test=smoke_test)
    centralities = compute_centralities(adjacency)
    detected_labels, detection_method = detect_communities(adjacency, seed=config.seed)
    network_metrics = compute_network_metrics(adjacency, detected_labels)
    assignments = build_community_assignments(adjacency, planted_labels, detected_labels, centralities)
    diffusion = simulate_si_diffusion(adjacency, centralities, config, smoke_test=smoke_test)
    figure_path = paths["output_dir"] / "network_map.png"
    draw_network_map(
        adjacency,
        detected_labels,
        planted_labels,
        centralities,
        figure_path,
        seed=config.seed + (17 if smoke_test else 0),
    )

    return write_outputs(
        paths=paths,
        config=config,
        network_metrics=network_metrics,
        assignments=assignments,
        centralities=centralities,
        diffusion=diffusion,
        figure_path=figure_path,
        detection_method=detection_method,
        smoke_test=smoke_test,
    )


def main() -> int:
    args = parse_args()
    artifacts = run(smoke_test=bool(args.smoke_test))
    print(f"Generated {len(artifacts)} artifacts for {CASE_ID}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
