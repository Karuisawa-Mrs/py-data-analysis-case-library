from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import yaml


VALID_CASE_DOMAINS = {
    "经济金融",
    "社会科学",
    "市场营销与运营",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run smoke tests for one case or all cases.")
    _ = parser.add_argument("--root", default=".", help="Catalog root path, defaults to current directory.")
    _ = parser.add_argument("--case", help="Single case path relative to --root or absolute path.")
    _ = parser.add_argument("--all", action="store_true", help="Run smoke tests for all cases under cases/*/*/.")
    return parser.parse_args()


def load_frontmatter(markdown_path: Path) -> dict[str, Any]:
    text = markdown_path.read_text(encoding="utf-8")
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        raise ValueError("missing YAML frontmatter start marker")
    start_marker_length = 5 if text.startswith("---\r\n") else 4
    end_marker = text.find("\n---\n", start_marker_length)
    if end_marker == -1:
        end_marker = text.find("\n---\r\n", start_marker_length)
    if end_marker == -1:
        raise ValueError("missing YAML frontmatter end marker")
    data = yaml.safe_load(text[start_marker_length:end_marker]) or {}
    if not isinstance(data, dict):
        raise ValueError("frontmatter must parse to a mapping")
    return cast(dict[str, Any], data)


def resolve_case_path(root: Path, case_value: str) -> Path:
    case_path = Path(case_value)
    if not case_path.is_absolute():
        case_path = root / case_path
    return case_path.resolve()


def iter_case_dirs(root: Path) -> list[Path]:
    case_dirs: list[Path] = []
    cases_root = root / "cases"
    if not cases_root.exists() or not cases_root.is_dir():
        return case_dirs

    for domain_dir in sorted(cases_root.iterdir(), key=lambda entry: entry.name):
        if not domain_dir.is_dir() or domain_dir.name not in VALID_CASE_DOMAINS:
            continue
        for case_dir in sorted(domain_dir.iterdir(), key=lambda entry: entry.name):
            if case_dir.is_dir():
                case_dirs.append(case_dir)
    return case_dirs


def validate_expected_artifacts(case_dir: Path) -> list[str]:
    index_path = case_dir / "index.md"
    if not index_path.exists() or not index_path.is_file():
        return [f"missing index.md: {case_dir}"]

    try:
        frontmatter = load_frontmatter(index_path)
    except (OSError, yaml.YAMLError, ValueError) as exc:
        return [f"invalid frontmatter in {index_path}: {exc}"]

    artifacts = frontmatter.get("expected_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return [f"missing or empty expected_artifacts in {index_path}"]

    errors: list[str] = []
    for artifact in artifacts:
        if not isinstance(artifact, str) or not artifact.strip():
            errors.append(f"invalid expected_artifact entry in {index_path}: {artifact!r}")
            continue
        artifact_path = case_dir / artifact
        if not artifact_path.exists() or not artifact_path.is_file():
            errors.append(f"missing expected artifact: {artifact_path}")
    return errors


def run_smoke_for_case(case_dir: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []
    analysis_path = case_dir / "analysis.py"
    if not analysis_path.exists() or not analysis_path.is_file():
        return False, [f"missing analysis.py: {case_dir}"]

    command = [sys.executable, "analysis.py", "--smoke-test"]
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run(command, cwd=case_dir, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        errors.append(f"smoke test failed for {case_dir}: exit code {result.returncode}")
        if result.stdout.strip():
            errors.append(f"stdout for {case_dir}: {result.stdout.strip()}")
        if result.stderr.strip():
            errors.append(f"stderr for {case_dir}: {result.stderr.strip()}")
        return False, errors

    errors.extend(validate_expected_artifacts(case_dir))
    return not errors, errors


def main() -> int:
    args = parse_args()
    root = Path(cast(str, args.root)).resolve()
    case_value = cast(str | None, args.case)
    run_all = cast(bool, args.all)

    if run_all == bool(case_value):
        print("Select exactly one target: --case <path> or --all.", file=sys.stderr)
        return 2

    case_dirs = [resolve_case_path(root, case_value)] if case_value else iter_case_dirs(root)

    if not case_dirs:
        print("No cases found for smoke run.")
        return 0

    failures: list[str] = []
    success_count = 0
    for case_dir in case_dirs:
        ok, errors = run_smoke_for_case(case_dir)
        if ok:
            success_count += 1
            print(f"smoke ok: {case_dir}")
            continue
        failures.extend(errors)
        print(f"smoke failed: {case_dir}", file=sys.stderr)

    if failures:
        for error in failures:
            print(error, file=sys.stderr)
        return 1

    print(f"{success_count} smoke run(s) succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
