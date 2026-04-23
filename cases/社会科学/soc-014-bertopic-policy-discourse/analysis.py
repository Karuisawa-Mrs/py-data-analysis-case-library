from __future__ import annotations

# pyright: reportMissingTypeStubs=false

# Fallback implementation for Windows environments where bertopic and
# sentence-transformers are unavailable. See best-practice-roadmap.md for the
# preferred BERTopic migration path.

import argparse
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from numpy.typing import NDArray
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import TfidfVectorizer


CASE_ID = "soc-014-bertopic-policy-discourse"
CASE_TITLE = "Policy discourse mapping with fallback topic modeling"
CLAIM_BOUNDARY = "This case demonstrates a fallback topic-modeling workflow on simulated policy texts and does not substitute for substantive analysis of real policy corpora."
FALLBACK_NOTE = "Fallback mode uses sklearn TF-IDF + LDA instead of BERTopic."


@dataclass(frozen=True)
class CaseConfig:
    seed: int
    output_dir: str
    n_documents_full: int = 200
    n_documents_smoke: int = 50
    n_topics_full: int = 8
    n_topics_smoke: int = 5
    max_features: int = 500
    lda_max_iter: int = 10
    top_terms_per_topic: int = 15
    template_count: int = 10


@dataclass(frozen=True)
class TopicTemplate:
    name: str
    keywords: tuple[str, ...]
    support_terms: tuple[str, ...]


def parse_args() -> bool:
    parser = argparse.ArgumentParser(
        description="Generate simulated policy documents and run a fallback sklearn LDA topic-modeling pipeline."
    )
    _ = parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run a smaller but complete pipeline while producing all expected artifacts.",
    )
    args = parser.parse_args()
    smoke_test_value = getattr(args, "smoke_test", False)
    return smoke_test_value if isinstance(smoke_test_value, bool) else False


def resolve_paths() -> dict[str, Path]:
    case_dir = Path(__file__).resolve().parent
    return {
        "case_dir": case_dir,
        "params_file": case_dir / "params.yaml",
        "output_dir": case_dir / "outputs",
        "roadmap_file": case_dir / "best-practice-roadmap.md",
    }


def load_config(params_file: Path) -> CaseConfig:
    raw_payload = yaml.safe_load(params_file.read_text(encoding="utf-8")) or {}
    if not isinstance(raw_payload, Mapping):
        raise ValueError("params.yaml must parse to a mapping")
    payload = dict(raw_payload)

    return CaseConfig(
        seed=read_int(payload, "seed"),
        output_dir=read_str(payload, "output_dir", "outputs"),
        n_documents_full=read_int(payload, "n_documents_full", 200),
        n_documents_smoke=read_int(payload, "n_documents_smoke", 50),
        n_topics_full=read_int(payload, "n_topics_full", 8),
        n_topics_smoke=read_int(payload, "n_topics_smoke", 5),
        max_features=read_int(payload, "max_features", 500),
        lda_max_iter=read_int(payload, "lda_max_iter", 10),
        top_terms_per_topic=read_int(payload, "top_terms_per_topic", 15),
        template_count=read_int(payload, "template_count", 10),
    )


def read_int(payload: Mapping[str, object], key: str, default: int | None = None) -> int:
    value = payload.get(key, default)
    if value is None:
        raise ValueError(f"Missing required integer parameter: {key}")
    if not isinstance(value, (int, float, str, bool)):
        raise ValueError(f"Parameter {key} must be int-compatible, got {type(value).__name__}")
    return int(value)


def read_str(payload: Mapping[str, object], key: str, default: str) -> str:
    value = payload.get(key, default)
    return str(value)


def ensure_output_dir(case_dir: Path, configured_output_dir: str) -> Path:
    output_dir = case_dir / configured_output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def build_topic_templates() -> list[TopicTemplate]:
    return [
        TopicTemplate(
            name="environment protection",
            keywords=("climate", "emission", "forest", "pollution", "recycling", "carbon", "ecosystem", "green"),
            support_terms=("river", "habitat", "renewable", "conservation", "monitoring", "waste"),
        ),
        TopicTemplate(
            name="education reform",
            keywords=("school", "curriculum", "teacher", "student", "classroom", "learning", "exam", "literacy"),
            support_terms=("training", "equity", "campus", "pedagogy", "achievement", "scholarship"),
        ),
        TopicTemplate(
            name="healthcare policy",
            keywords=("hospital", "patient", "insurance", "clinic", "doctor", "care", "medicine", "prevention"),
            support_terms=("treatment", "primary", "publichealth", "vaccination", "coverage", "wellness"),
        ),
        TopicTemplate(
            name="labor market",
            keywords=("employment", "wage", "worker", "skill", "training", "firm", "vacancy", "productivity"),
            support_terms=("contract", "mobility", "earnings", "apprenticeship", "matching", "jobsearch"),
        ),
        TopicTemplate(
            name="housing affordability",
            keywords=("housing", "rent", "mortgage", "tenant", "zoning", "construction", "urban", "supply"),
            support_terms=("permit", "density", "neighborhood", "subsidy", "affordable", "landuse"),
        ),
        TopicTemplate(
            name="digital governance",
            keywords=("data", "privacy", "platform", "cyber", "algorithm", "security", "digital", "regulation"),
            support_terms=("identity", "compliance", "transparency", "network", "encryption", "oversight"),
        ),
        TopicTemplate(
            name="transport infrastructure",
            keywords=("transit", "rail", "road", "traffic", "mobility", "station", "logistics", "bridge"),
            support_terms=("highway", "bus", "commute", "freight", "capacity", "maintenance"),
        ),
        TopicTemplate(
            name="agricultural resilience",
            keywords=("farm", "crop", "irrigation", "soil", "farmer", "yield", "drought", "agriculture"),
            support_terms=("harvest", "seed", "fertilizer", "cooperative", "livestock", "water"),
        ),
        TopicTemplate(
            name="energy transition",
            keywords=("energy", "solar", "grid", "battery", "power", "electricity", "storage", "efficiency"),
            support_terms=("wind", "capacity", "demand", "generation", "utility", "resilience"),
        ),
        TopicTemplate(
            name="social welfare",
            keywords=("benefit", "poverty", "household", "support", "allowance", "childcare", "inclusion", "assistance"),
            support_terms=("transfer", "eligibility", "vulnerable", "community", "protection", "service"),
        ),
    ]


def sample_terms(rng: np.random.Generator, pool: Sequence[str], size: int) -> list[str]:
    return [pool[int(rng.integers(0, len(pool)))] for _ in range(size)]


def generate_documents(config: CaseConfig, smoke_test: bool) -> pd.DataFrame:
    rng = np.random.default_rng(config.seed + (11 if smoke_test else 0))
    templates = build_topic_templates()[: config.template_count]
    n_documents = config.n_documents_smoke if smoke_test else config.n_documents_full
    noise_pool = (
        "policy",
        "public",
        "program",
        "national",
        "regional",
        "local",
        "committee",
        "budget",
        "evidence",
        "stakeholder",
        "implementation",
        "evaluation",
        "target",
        "framework",
        "service",
        "reform",
        "governance",
        "planning",
        "strategy",
        "outcome",
        "pilot",
        "agency",
        "ministry",
        "capacity",
        "funding",
        "reporting",
        "standard",
        "measure",
        "community",
        "development",
    )

    rows: list[dict[str, str | int]] = []
    for doc_idx in range(n_documents):
        primary_idx = int(rng.integers(0, len(templates)))
        secondary_idx = int(rng.integers(0, len(templates)))
        while secondary_idx == primary_idx:
            secondary_idx = int(rng.integers(0, len(templates)))

        use_mixed_topic = bool(rng.random() < 0.35)
        active_templates = [templates[primary_idx]]
        if use_mixed_topic:
            active_templates.append(templates[secondary_idx])

        token_list: list[str] = []
        for template in active_templates:
            token_list.extend(sample_terms(rng, template.keywords, 10))
            token_list.extend(sample_terms(rng, template.support_terms, 6))
            token_list.extend(template.name.split())

        token_list.extend(sample_terms(rng, noise_pool, 12))
        rng.shuffle(token_list)

        document_text = " ".join(token_list)
        rows.append(
            {
                "doc_id": f"doc_{doc_idx:03d}",
                "text": document_text,
                "template_primary": templates[primary_idx].name,
                "template_secondary": templates[secondary_idx].name if use_mixed_topic else "none",
            }
        )

    return pd.DataFrame(rows)


def fit_topic_model(
    documents: pd.DataFrame,
    config: CaseConfig,
    smoke_test: bool,
) -> tuple[TfidfVectorizer, LatentDirichletAllocation, NDArray[np.float64], NDArray[np.float64]]:
    topic_count = config.n_topics_smoke if smoke_test else config.n_topics_full
    vectorizer = TfidfVectorizer(max_features=config.max_features, stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(documents["text"])
    lda = LatentDirichletAllocation(
        n_components=topic_count,
        max_iter=config.lda_max_iter,
        learning_method="batch",
        random_state=config.seed + (101 if smoke_test else 0),
    )
    doc_topic = np.asarray(lda.fit_transform(tfidf_matrix), dtype=np.float64)
    topic_term = np.asarray(lda.components_, dtype=np.float64)
    return vectorizer, lda, doc_topic, topic_term


def build_topic_terms_table(feature_names: NDArray[np.str_], topic_term: NDArray[np.float64], top_n: int) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    for topic_idx, weights in enumerate(topic_term):
        top_indices = np.argsort(weights)[::-1][:top_n]
        for rank, term_idx in enumerate(top_indices, start=1):
            rows.append(
                {
                    "topic_id": topic_idx,
                    "rank": rank,
                    "term": str(feature_names[term_idx]),
                    "weight": float(weights[term_idx]),
                }
            )
    return pd.DataFrame(rows)


def build_topic_info_table(topic_terms: pd.DataFrame, doc_topic: NDArray[np.float64]) -> pd.DataFrame:
    prevalence = doc_topic.mean(axis=0)
    rows: list[dict[str, float | int | str]] = []
    for topic_idx in range(doc_topic.shape[1]):
        top_words = topic_terms.loc[topic_terms["topic_id"] == topic_idx].sort_values("rank")["term"].tolist()
        rows.append(
            {
                "topic_id": topic_idx,
                "top_words": ", ".join(top_words),
                "prevalence": float(prevalence[topic_idx]),
            }
        )
    return pd.DataFrame(rows).sort_values("prevalence", ascending=False).reset_index(drop=True)


def build_document_topic_map(documents: pd.DataFrame, doc_topic: NDArray[np.float64]) -> pd.DataFrame:
    rows: list[dict[str, int | str]] = []
    for row_idx, doc_id in enumerate(documents["doc_id"].tolist()):
        probabilities = {f"topic_{topic_idx}": round(float(probability), 6) for topic_idx, probability in enumerate(doc_topic[row_idx])}
        rows.append(
            {
                "doc_id": doc_id,
                "dominant_topic": int(np.argmax(doc_topic[row_idx])),
                "topic_probabilities": json.dumps(probabilities, ensure_ascii=True, sort_keys=True),
            }
        )
    return pd.DataFrame(rows)


def save_topic_prevalence_plot(topic_info: pd.DataFrame, output_path: Path) -> None:
    ordered = topic_info.sort_values("topic_id").reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(8.5, 4.8), constrained_layout=True)
    ax.bar(ordered["topic_id"].astype(str), ordered["prevalence"], color="#4C78A8")
    ax.set_title("Topic prevalence")
    ax.set_xlabel("Topic ID")
    ax.set_ylabel("Average document weight")
    ax.grid(axis="y", alpha=0.25)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def write_summary(
    output_path: Path,
    *,
    config: CaseConfig,
    smoke_test: bool,
    documents: pd.DataFrame,
    topic_info: pd.DataFrame,
    roadmap_exists: bool,
) -> None:
    top_topic = topic_info.sort_values("prevalence", ascending=False).iloc[0]
    lines = [
        f"case_id: {CASE_ID}",
        f"title: {CASE_TITLE}",
        f"mode: {'SMOKE TEST' if smoke_test else 'FULL RUN'}",
        f"fallback_note: {FALLBACK_NOTE}",
        f"seed: {config.seed}",
        f"documents_generated: {len(documents)}",
        f"topic_count: {config.n_topics_smoke if smoke_test else config.n_topics_full}",
        f"template_count: {config.template_count}",
        f"top_topic_id: {int(top_topic['topic_id'])}",
        f"top_topic_prevalence: {float(top_topic['prevalence']):.6f}",
        f"top_topic_words: {top_topic['top_words']}",
        f"claim_boundary: {CLAIM_BOUNDARY}",
        f"roadmap_available: {'yes' if roadmap_exists else 'no'}",
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(smoke_test: bool = False) -> dict[str, Path]:
    paths = resolve_paths()
    config = load_config(paths["params_file"])
    output_dir = ensure_output_dir(paths["case_dir"], config.output_dir)

    documents = generate_documents(config=config, smoke_test=smoke_test)
    vectorizer, _, doc_topic, topic_term = fit_topic_model(documents=documents, config=config, smoke_test=smoke_test)
    feature_names = vectorizer.get_feature_names_out()

    topic_terms = build_topic_terms_table(
        feature_names=feature_names,
        topic_term=topic_term,
        top_n=config.top_terms_per_topic,
    )
    topic_info = build_topic_info_table(topic_terms=topic_terms, doc_topic=doc_topic)
    topic_document_map = build_document_topic_map(documents=documents, doc_topic=doc_topic)

    topic_info_path = output_dir / "topic_info.csv"
    topic_document_map_path = output_dir / "topic_document_map.csv"
    topic_terms_path = output_dir / "topic_terms.csv"
    plot_path = output_dir / "topic_prevalence.png"
    summary_path = output_dir / "summary.txt"
    smoke_path = output_dir / "smoke_test.txt"

    topic_info.to_csv(topic_info_path, index=False, encoding="utf-8-sig")
    topic_document_map.to_csv(topic_document_map_path, index=False, encoding="utf-8-sig")
    topic_terms.to_csv(topic_terms_path, index=False, encoding="utf-8-sig")
    save_topic_prevalence_plot(topic_info=topic_info, output_path=plot_path)

    write_summary(
        summary_path,
        config=config,
        smoke_test=smoke_test,
        documents=documents,
        topic_info=topic_info,
        roadmap_exists=paths["roadmap_file"].exists(),
    )
    write_summary(
        smoke_path,
        config=config,
        smoke_test=True,
        documents=documents,
        topic_info=topic_info,
        roadmap_exists=paths["roadmap_file"].exists(),
    )

    return {
        "summary": summary_path,
        "smoke": smoke_path,
        "topic_info": topic_info_path,
        "topic_document_map": topic_document_map_path,
        "topic_terms": topic_terms_path,
        "topic_prevalence": plot_path,
    }


if __name__ == "__main__":
    smoke_test = parse_args()
    artifact_paths = run(smoke_test=smoke_test)
    print("Generated artifacts:")
    for name, path in artifact_paths.items():
        print(f"- {name}: {path}")
