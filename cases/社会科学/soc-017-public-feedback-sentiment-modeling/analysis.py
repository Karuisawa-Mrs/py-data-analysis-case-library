# This fallback implementation uses an enhanced sklearn TF-IDF baseline only.
# See best-practice-roadmap.md for the planned transformer-based migration path.

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import matplotlib
import numpy.typing as npt

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_validate
from sklearn.pipeline import FeatureUnion, Pipeline

try:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    HAS_TRANSFORMERS = True
except ImportError:  # pragma: no cover - optional best-practice dependency
    AutoModelForSequenceClassification = None
    AutoTokenizer = None
    torch = None
    HAS_TRANSFORMERS = False


CASE_ID = "soc-017-public-feedback-sentiment-modeling"
POSITIVE_LABEL = 1
NEGATIVE_LABEL = 0


@dataclass(frozen=True)
class CaseConfig:
    seed: int
    output_dir: str
    sample_size: int
    smoke_test_sample_size: int
    cv_folds: int
    logistic_max_iter: int
    top_term_count: int


@dataclass(frozen=True)
class EvaluationResult:
    fitted_pipeline: Pipeline
    metrics_df: pd.DataFrame
    report_df: pd.DataFrame
    confusion_matrix: npt.NDArray[np.int_]


@dataclass(frozen=True)
class TransformerResult:
    metrics_df: pd.DataFrame
    report_df: pd.DataFrame
    predictions: npt.NDArray[np.int_]
    confidence: npt.NDArray[np.float64]
    attention_terms: pd.DataFrame
    implementation_note: str


def parse_args() -> bool:
    parser = argparse.ArgumentParser(
        description=(
            "Simulate public feedback sentiment data and run an enhanced TF-IDF + "
            "Logistic Regression fallback baseline. analysis.py is the single source of truth."
        )
    )
    _ = parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run a smaller deterministic workflow while still generating all required artifacts.",
    )
    args = parser.parse_args()
    smoke_test_value = getattr(args, "smoke_test", False)
    return smoke_test_value if isinstance(smoke_test_value, bool) else False


def resolve_paths() -> dict[str, Path]:
    case_dir = Path(__file__).resolve().parent
    return {
        "case_dir": case_dir,
        "params_file": case_dir / "params.yaml",
        "index_file": case_dir / "index.md",
        "roadmap_file": case_dir / "best-practice-roadmap.md",
    }


def load_config(params_file: Path) -> CaseConfig:
    payload = yaml.safe_load(params_file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("params.yaml must parse to a mapping")

    return CaseConfig(
        seed=int(payload["seed"]),
        output_dir=str(payload.get("output_dir", "outputs")),
        sample_size=int(payload.get("sample_size", 500)),
        smoke_test_sample_size=int(payload.get("smoke_test_sample_size", 100)),
        cv_folds=int(payload.get("cv_folds", 5)),
        logistic_max_iter=int(payload.get("logistic_max_iter", 1000)),
        top_term_count=int(payload.get("top_term_count", 15)),
    )


def resolve_output_dir(case_dir: Path, output_dir_value: str) -> Path:
    output_dir = Path(output_dir_value)
    if not output_dir.is_absolute():
        output_dir = case_dir / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def build_feature_pipeline(config: CaseConfig) -> Pipeline:
    features = FeatureUnion(
        transformer_list=[
            (
                "word_tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 3),
                    max_features=2000,
                    sublinear_tf=True,
                    lowercase=True,
                ),
            ),
            (
                "char_ngrams",
                CountVectorizer(
                    analyzer="char_wb",
                    ngram_range=(2, 4),
                    lowercase=True,
                ),
            ),
        ]
    )
    model = LogisticRegression(
        class_weight="balanced",
        max_iter=config.logistic_max_iter,
        solver="liblinear",
        random_state=config.seed,
    )
    return Pipeline(
        steps=[
            ("features", features),
            ("model", model),
        ]
    )


def simulate_feedback_dataset(config: CaseConfig, smoke_test: bool) -> pd.DataFrame:
    size = config.smoke_test_sample_size if smoke_test else config.sample_size
    rng = np.random.default_rng(config.seed + (17 if smoke_test else 0))

    positive_templates = [
        "The {service} process felt {descriptor} and the {aspect} team resolved my issue {delivery}. I am {emotion} with the {channel} support and the overall experience was {outcome}.",
        "I appreciate how {service} staff handled the {aspect} request. The response was {descriptor}, {delivery}, and left me {emotion} about future engagement.",
        "My recent interaction with the {service} office was {descriptor}. The {channel} message arrived {delivery}, the {aspect} fix worked, and the result feels {outcome}.",
        "The new {service} arrangement is {descriptor} for residents. The {aspect} update was communicated {delivery}, and I now feel {emotion} about the service quality.",
    ]
    negative_templates = [
        "The {service} process felt {descriptor} and the {aspect} team handled my issue {delivery}. I am {emotion} with the {channel} support and the whole experience was {outcome}.",
        "I am frustrated that the {service} staff managed the {aspect} request so {descriptor}. The response was {delivery} and it left me {emotion} about future contact.",
        "My recent interaction with the {service} office was {descriptor}. The {channel} message arrived {delivery}, the {aspect} problem remained, and the result feels {outcome}.",
        "The new {service} arrangement is {descriptor} for residents. The {aspect} update was communicated {delivery}, and I now feel {emotion} about the service quality.",
    ]

    services = [
        "public hotline",
        "community clinic",
        "transport desk",
        "housing office",
        "education bureau",
        "service counter",
        "digital portal",
        "neighborhood center",
    ]
    aspects = [
        "application",
        "complaint",
        "benefit",
        "appointment",
        "maintenance",
        "registration",
        "follow-up",
        "verification",
    ]
    channels = ["email", "phone", "online", "onsite", "message"]

    positive_descriptors = [
        "efficient",
        "thoughtful",
        "smooth",
        "responsive",
        "helpful",
        "well organized",
        "clear",
        "reliable",
    ]
    positive_delivery = [
        "very quickly",
        "with clear guidance",
        "with real care",
        "without confusion",
        "in a practical way",
        "faster than expected",
    ]
    positive_emotions = ["satisfied", "reassured", "optimistic", "heard", "supported", "grateful"]
    positive_outcomes = ["constructive", "positive", "encouraging", "useful", "trustworthy", "fair"]
    positive_keywords = [
        "respectful",
        "timely",
        "clear",
        "friendly",
        "stable",
        "transparent",
        "effective",
        "improved",
        "professional",
        "supportive",
    ]

    negative_descriptors = [
        "slow",
        "confusing",
        "dismissive",
        "frustrating",
        "unreliable",
        "poorly managed",
        "unclear",
        "inconsistent",
    ]
    negative_delivery = [
        "after a long delay",
        "without useful guidance",
        "with repeated errors",
        "in a rushed way",
        "with no real follow up",
        "later than promised",
    ]
    negative_emotions = ["upset", "ignored", "disappointed", "concerned", "skeptical", "tired"]
    negative_outcomes = ["negative", "stressful", "unfair", "ineffective", "worrying", "unresolved"]
    negative_keywords = [
        "delay",
        "unclear",
        "complaint",
        "waiting",
        "broken",
        "repeat",
        "error",
        "cold",
        "opaque",
        "unhelpful",
    ]
    neutral_context = [
        "city service",
        "public response",
        "local office",
        "resident request",
        "policy update",
        "community issue",
        "service standard",
        "citizen experience",
    ]

    def maybe_noisy_token(token: str) -> str:
        if rng.random() >= 0.12 or len(token) < 5:
            return token
        patterns = [
            token + token[-1],
            token.replace("e", "ee", 1),
            token.replace("i", "1", 1),
            token.replace("o", "0", 1),
        ]
        return str(rng.choice(patterns))

    def generate_text(label: int) -> str:
        is_positive = label == POSITIVE_LABEL
        template = str(rng.choice(positive_templates if is_positive else negative_templates))
        descriptor = str(rng.choice(positive_descriptors if is_positive else negative_descriptors))
        delivery = str(rng.choice(positive_delivery if is_positive else negative_delivery))
        emotion = str(rng.choice(positive_emotions if is_positive else negative_emotions))
        outcome = str(rng.choice(positive_outcomes if is_positive else negative_outcomes))
        keywords = positive_keywords if is_positive else negative_keywords
        selected_keywords = rng.choice(keywords, size=3, replace=False).tolist()
        selected_context = rng.choice(neutral_context, size=2, replace=False).tolist()

        sentence = template.format(
            service=str(rng.choice(services)),
            aspect=str(rng.choice(aspects)),
            descriptor=descriptor,
            delivery=delivery,
            emotion=emotion,
            channel=str(rng.choice(channels)),
            outcome=outcome,
        )
        noisy_keywords = [maybe_noisy_token(keyword) for keyword in selected_keywords]
        tail = " ".join(noisy_keywords + selected_context)
        emphasis = "strongly recommend" if is_positive else "needs urgent repair"
        return f"{sentence} {tail}. {emphasis}."

    labels = np.array([POSITIVE_LABEL] * (size // 2) + [NEGATIVE_LABEL] * (size - size // 2), dtype=int)
    rng.shuffle(labels)
    texts = [generate_text(int(label)) for label in labels]

    dataset = pd.DataFrame(
        {
            "feedback_id": np.arange(1, size + 1, dtype=int),
            "text": texts,
            "sentiment_label": labels,
        }
    )
    dataset["sentiment_name"] = dataset["sentiment_label"].replace(
        {NEGATIVE_LABEL: "negative", POSITIVE_LABEL: "positive"}
    )
    return dataset


def evaluate_pipeline(dataset: pd.DataFrame, config: CaseConfig) -> EvaluationResult:
    X = dataset["text"]
    y = dataset["sentiment_label"]
    pipeline = build_feature_pipeline(config)
    cv = StratifiedKFold(n_splits=config.cv_folds, shuffle=True, random_state=config.seed)

    scores = cross_validate(
        pipeline,
        X,
        y,
        cv=cv,
        scoring=["accuracy", "precision", "recall", "f1"],
        return_train_score=False,
        n_jobs=None,
    )
    predictions = np.asarray(cross_val_predict(pipeline, X, y, cv=cv, n_jobs=None), dtype=int)

    fitted_pipeline = build_feature_pipeline(config)
    _ = fitted_pipeline.fit(X, y)

    report = classification_report(
        y,
        predictions,
        output_dict=True,
        target_names=["negative", "positive"],
        zero_division="warn",
    )
    confusion = np.asarray(
        confusion_matrix(y, predictions, labels=[NEGATIVE_LABEL, POSITIVE_LABEL]),
        dtype=np.int_,
    )

    metrics_rows = [
        {"model": "tfidf_logistic_regression", "metric": "accuracy_mean", "value": float(np.mean(scores["test_accuracy"]))},
        {"model": "tfidf_logistic_regression", "metric": "accuracy_std", "value": float(np.std(scores["test_accuracy"]))},
        {"model": "tfidf_logistic_regression", "metric": "precision_mean", "value": float(np.mean(scores["test_precision"]))},
        {"model": "tfidf_logistic_regression", "metric": "precision_std", "value": float(np.std(scores["test_precision"]))},
        {"model": "tfidf_logistic_regression", "metric": "recall_mean", "value": float(np.mean(scores["test_recall"]))},
        {"model": "tfidf_logistic_regression", "metric": "recall_std", "value": float(np.std(scores["test_recall"]))},
        {"model": "tfidf_logistic_regression", "metric": "f1_mean", "value": float(np.mean(scores["test_f1"]))},
        {"model": "tfidf_logistic_regression", "metric": "f1_std", "value": float(np.std(scores["test_f1"]))},
        {"model": "tfidf_logistic_regression", "metric": "support_total", "value": float(len(dataset))},
        {"model": "tfidf_logistic_regression", "metric": "positive_rate", "value": float(dataset["sentiment_label"].mean())},
        {"model": "tfidf_logistic_regression", "metric": "tn", "value": float(confusion[0, 0])},
        {"model": "tfidf_logistic_regression", "metric": "fp", "value": float(confusion[0, 1])},
        {"model": "tfidf_logistic_regression", "metric": "fn", "value": float(confusion[1, 0])},
        {"model": "tfidf_logistic_regression", "metric": "tp", "value": float(confusion[1, 1])},
    ]

    report_df = pd.DataFrame(report).transpose().reset_index(names="label")
    report_df.insert(0, "model", "tfidf_logistic_regression")
    return EvaluationResult(
        fitted_pipeline=fitted_pipeline,
        metrics_df=pd.DataFrame(metrics_rows),
        report_df=report_df,
        confusion_matrix=confusion,
    )


def extract_top_terms(fitted_pipeline: Pipeline, top_term_count: int) -> pd.DataFrame:
    features = fitted_pipeline.named_steps["features"]
    model = fitted_pipeline.named_steps["model"]
    coefficients = model.coef_.ravel()

    feature_rows: list[dict[str, object]] = []
    offset = 0
    for name, transformer in features.transformer_list:
        feature_names = transformer.get_feature_names_out()
        width = len(feature_names)
        sub_coefficients = coefficients[offset : offset + width]
        offset += width

        source = "word" if name == "word_tfidf" else "char"
        for term, coefficient in zip(feature_names, sub_coefficients):
            feature_rows.append(
                {
                    "source": source,
                    "term": str(term),
                    "coefficient": float(coefficient),
                }
            )

    feature_df = pd.DataFrame(feature_rows)
    negative_terms = (
        feature_df.sort_values("coefficient", ascending=True)
        .head(top_term_count)
        .assign(polarity="negative", rank=lambda df: np.arange(1, len(df) + 1))
    )
    positive_terms = (
        feature_df.sort_values("coefficient", ascending=False)
        .head(top_term_count)
        .assign(polarity="positive", rank=lambda df: np.arange(1, len(df) + 1))
    )
    top_terms = pd.concat([positive_terms, negative_terms], ignore_index=True)
    return pd.DataFrame(top_terms.loc[:, ["polarity", "rank", "source", "term", "coefficient"]]).copy()


def evaluate_transformer_model(dataset: pd.DataFrame, config: CaseConfig) -> TransformerResult:
    if not HAS_TRANSFORMERS or AutoTokenizer is None or AutoModelForSequenceClassification is None or torch is None:
        raise ImportError("transformers and torch are required for the Transformer branch")

    model_name = "distilbert-base-uncased-finetuned-sst-2-english"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name, output_attentions=True)
    model.eval()

    texts = dataset["text"].astype(str).tolist()
    labels = dataset["sentiment_label"].to_numpy(dtype=int)
    predictions: list[int] = []
    confidences: list[float] = []
    attention_rows: list[dict[str, float | int | str]] = []

    batch_size = 16
    with torch.no_grad():
        for start in range(0, len(texts), batch_size):
            batch_texts = texts[start : start + batch_size]
            encoded = tokenizer(batch_texts, padding=True, truncation=True, max_length=160, return_tensors="pt")
            outputs = model(**encoded)
            probabilities = torch.softmax(outputs.logits, dim=-1)
            batch_confidence, batch_prediction = torch.max(probabilities, dim=-1)
            predictions.extend(int(value) for value in batch_prediction.cpu().numpy())
            confidences.extend(float(value) for value in batch_confidence.cpu().numpy())

            if start == 0 and outputs.attentions:
                tokens = tokenizer.convert_ids_to_tokens(encoded["input_ids"][0])
                cls_attention = outputs.attentions[-1][0, :, 0, :].mean(dim=0).cpu().numpy()
                for rank, token_index in enumerate(np.argsort(cls_attention)[::-1][: config.top_term_count], start=1):
                    token = str(tokens[int(token_index)])
                    if token in {"[CLS]", "[SEP]", "[PAD]"}:
                        continue
                    attention_rows.append(
                        {
                            "polarity": "attention",
                            "rank": rank,
                            "source": "transformer_attention",
                            "term": token,
                            "coefficient": float(cls_attention[int(token_index)]),
                        }
                    )

    prediction_array = np.asarray(predictions, dtype=int)
    confidence_array = np.asarray(confidences, dtype=np.float64)
    report = classification_report(
        labels,
        prediction_array,
        output_dict=True,
        target_names=["negative", "positive"],
        zero_division=0,
    )
    confusion = confusion_matrix(labels, prediction_array, labels=[NEGATIVE_LABEL, POSITIVE_LABEL])
    report_df = pd.DataFrame(report).transpose().reset_index(names="label")
    report_df.insert(0, "model", "distilbert_sst2_zero_shot")
    metrics_df = pd.DataFrame(
        [
            {"model": "distilbert_sst2_zero_shot", "metric": "accuracy", "value": float(np.mean(prediction_array == labels))},
            {"model": "distilbert_sst2_zero_shot", "metric": "confidence_mean", "value": float(confidence_array.mean())},
            {"model": "distilbert_sst2_zero_shot", "metric": "confidence_std", "value": float(confidence_array.std())},
            {"model": "distilbert_sst2_zero_shot", "metric": "tn", "value": float(confusion[0, 0])},
            {"model": "distilbert_sst2_zero_shot", "metric": "fp", "value": float(confusion[0, 1])},
            {"model": "distilbert_sst2_zero_shot", "metric": "fn", "value": float(confusion[1, 0])},
            {"model": "distilbert_sst2_zero_shot", "metric": "tp", "value": float(confusion[1, 1])},
        ]
    )
    attention_terms = pd.DataFrame(attention_rows)
    if attention_terms.empty:
        attention_terms = pd.DataFrame(
            [{"polarity": "attention", "rank": 1, "source": "transformer_attention", "term": "unavailable", "coefficient": 0.0}]
        )
    return TransformerResult(
        metrics_df=metrics_df,
        report_df=report_df,
        predictions=prediction_array,
        confidence=confidence_array,
        attention_terms=attention_terms,
        implementation_note=f"Transformer branch used {model_name}",
    )


def write_confidence_distribution(confidence: npt.NDArray[np.float64], output_path: Path) -> None:
    figure, axis = plt.subplots(figsize=(6.5, 4.2), constrained_layout=True)
    axis.hist(confidence, bins=12, color="#4C78A8", edgecolor="white")
    axis.set_title("Transformer confidence distribution")
    axis.set_xlabel("Softmax confidence")
    axis.set_ylabel("Count")
    axis.grid(axis="y", alpha=0.25)
    figure.savefig(output_path, dpi=160)
    plt.close(figure)


def build_misclassified_examples(
    dataset: pd.DataFrame,
    predictions: npt.NDArray[np.int_],
    confidence: npt.NDArray[np.float64],
) -> pd.DataFrame:
    frame = dataset.loc[:, ["feedback_id", "text", "sentiment_label", "sentiment_name"]].copy()
    frame["predicted_label"] = predictions
    frame["predicted_name"] = frame["predicted_label"].replace({NEGATIVE_LABEL: "negative", POSITIVE_LABEL: "positive"})
    frame["confidence"] = confidence
    frame = frame[frame["sentiment_label"] != frame["predicted_label"]].sort_values("confidence", ascending=False)
    if frame.empty:
        return pd.DataFrame(
            [
                {
                    "feedback_id": 0,
                    "text": "No misclassified examples in this deterministic run.",
                    "sentiment_label": -1,
                    "sentiment_name": "none",
                    "predicted_label": -1,
                    "predicted_name": "none",
                    "confidence": 0.0,
                }
            ]
        )
    return frame.head(20).reset_index(drop=True)


def write_confusion_matrix_figure(confusion: npt.NDArray[np.int_], output_path: Path) -> None:
    figure, axis = plt.subplots(figsize=(5.5, 4.5))
    image = axis.imshow(confusion, cmap="Blues")
    _ = figure.colorbar(image, ax=axis, shrink=0.85)
    axis.set_xticks([0, 1], labels=["Negative", "Positive"])
    axis.set_yticks([0, 1], labels=["Negative", "Positive"])
    axis.set_xlabel("Predicted label")
    axis.set_ylabel("True label")
    axis.set_title("Sentiment confusion matrix")

    for row_index in range(confusion.shape[0]):
        for col_index in range(confusion.shape[1]):
            axis.text(
                col_index,
                row_index,
                f"{int(confusion[row_index, col_index])}",
                ha="center",
                va="center",
                color="black",
            )

    figure.tight_layout()
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)


def write_summary_files(
    dataset: pd.DataFrame,
    metrics_df: pd.DataFrame,
    top_terms: pd.DataFrame,
    output_dir: Path,
    smoke_test: bool,
    implementation_note: str,
) -> None:
    metrics_lookup = dict(zip(metrics_df["metric"], metrics_df["value"]))
    mode_label = "SMOKE TEST" if smoke_test else "FULL RUN"
    summary_lines = [
        f"case_id: {CASE_ID}",
        f"mode: {mode_label}",
        f"sample_size: {len(dataset)}",
        f"positive_rate: {metrics_lookup['positive_rate']:.3f}",
        f"cv_accuracy_mean: {metrics_lookup['accuracy_mean']:.4f}",
        f"cv_precision_mean: {metrics_lookup['precision_mean']:.4f}",
        f"cv_recall_mean: {metrics_lookup['recall_mean']:.4f}",
        f"cv_f1_mean: {metrics_lookup['f1_mean']:.4f}",
        f"confusion_matrix: tn={int(metrics_lookup['tn'])}, fp={int(metrics_lookup['fp'])}, fn={int(metrics_lookup['fn'])}, tp={int(metrics_lookup['tp'])}",
        f"model_note: {implementation_note}",
        "top_positive_terms: " + ", ".join(top_terms.loc[top_terms["polarity"] == "positive", "term"].head(5).tolist()),
        "top_negative_terms: " + ", ".join(top_terms.loc[top_terms["polarity"] == "negative", "term"].head(5).tolist()),
    ]
    (output_dir / "summary.txt").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    smoke_lines = [
        f"smoke_test: {'true' if smoke_test else 'false'}",
        f"sample_size: {len(dataset)}",
        "artifacts:",
        "- summary.txt",
        "- smoke_test.txt",
        "- model_metrics.csv",
        "- classification_report.csv",
        "- confusion_matrix.png",
        "- top_terms_or_attention.csv",
    ]
    (output_dir / "smoke_test.txt").write_text("\n".join(smoke_lines) + "\n", encoding="utf-8")


def run(smoke_test: bool = False) -> dict[str, Path]:
    paths = resolve_paths()
    config = load_config(paths["params_file"])
    output_dir = resolve_output_dir(paths["case_dir"], config.output_dir)

    dataset = simulate_feedback_dataset(config, smoke_test=smoke_test)
    evaluation = evaluate_pipeline(dataset, config)

    metrics_df = evaluation.metrics_df
    report_df = evaluation.report_df
    top_terms = extract_top_terms(evaluation.fitted_pipeline, config.top_term_count)
    implementation_note = "TF-IDF baseline completed; Transformer branch not yet evaluated."

    transformer_metrics_path = output_dir / "transformer_metrics.csv"
    confidence_distribution_path = output_dir / "confidence_distribution.png"
    misclassified_examples_path = output_dir / "misclassified_examples.csv"

    try:
        transformer_result = evaluate_transformer_model(dataset, config)
        implementation_note = f"TF-IDF baseline plus {transformer_result.implementation_note}"
        metrics_df = pd.concat([metrics_df, transformer_result.metrics_df], ignore_index=True)
        report_df = pd.concat([report_df, transformer_result.report_df], ignore_index=True)
        top_terms = pd.concat([top_terms, transformer_result.attention_terms], ignore_index=True)
        transformer_result.metrics_df.to_csv(transformer_metrics_path, index=False)
        write_confidence_distribution(transformer_result.confidence, confidence_distribution_path)
        build_misclassified_examples(dataset, transformer_result.predictions, transformer_result.confidence).to_csv(
            misclassified_examples_path,
            index=False,
        )
    except (ImportError, OSError, ValueError, RuntimeError) as exc:
        implementation_note = f"TF-IDF baseline completed; Transformer branch degraded: {type(exc).__name__}: {exc}"
        baseline_probabilities = evaluation.fitted_pipeline.predict_proba(dataset["text"])
        baseline_confidence = np.max(baseline_probabilities, axis=1).astype(np.float64)
        baseline_predictions = evaluation.fitted_pipeline.predict(dataset["text"]).astype(int)
        fallback_metrics = pd.DataFrame(
            [
                {
                    "model": "transformer_unavailable",
                    "metric": "branch_status",
                    "value": 0.0,
                    "note": implementation_note,
                }
            ]
        )
        fallback_metrics.to_csv(transformer_metrics_path, index=False)
        write_confidence_distribution(baseline_confidence, confidence_distribution_path)
        build_misclassified_examples(dataset, baseline_predictions, baseline_confidence).to_csv(
            misclassified_examples_path,
            index=False,
        )

    model_metrics_path = output_dir / "model_metrics.csv"
    classification_report_path = output_dir / "classification_report.csv"
    top_terms_path = output_dir / "top_terms_or_attention.csv"
    confusion_matrix_path = output_dir / "confusion_matrix.png"

    metrics_df.to_csv(model_metrics_path, index=False)
    report_df.to_csv(classification_report_path, index=False)
    top_terms.to_csv(top_terms_path, index=False)
    write_confusion_matrix_figure(evaluation.confusion_matrix, confusion_matrix_path)
    write_summary_files(dataset, metrics_df, top_terms, output_dir, smoke_test=smoke_test, implementation_note=implementation_note)

    return {
        "summary": output_dir / "summary.txt",
        "smoke_test": output_dir / "smoke_test.txt",
        "model_metrics": model_metrics_path,
        "classification_report": classification_report_path,
        "confusion_matrix": confusion_matrix_path,
        "top_terms": top_terms_path,
        "transformer_metrics": transformer_metrics_path,
        "confidence_distribution": confidence_distribution_path,
        "misclassified_examples": misclassified_examples_path,
    }


if __name__ == "__main__":
    smoke_test = parse_args()
    artifact_paths = run(smoke_test=smoke_test)
    print("Generated artifacts:")
    for artifact_name, artifact_path in artifact_paths.items():
        print(f"- {artifact_name}: {artifact_path}")
