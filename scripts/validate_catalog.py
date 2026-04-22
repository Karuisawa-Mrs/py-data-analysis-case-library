from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable, cast

import yaml


VALID_CASE_DOMAINS = {
    "经济金融",
    "社会科学",
    "市场营销与运营",
}

REQUIRED_TEMPLATE_FILES = [
    Path("analysis.py"),
    Path("analysis.ipynb"),
    Path("index.md"),
    Path("params.yaml"),
    Path("references.bib"),
    Path("data") / "README.md",
    Path("outputs") / "README.md",
]

REQUIRED_INDEX_FILES = [
    Path("cases") / "index.md",
    Path("cases") / "经济金融" / "index.md",
    Path("cases") / "社会科学" / "index.md",
    Path("cases") / "市场营销与运营" / "index.md",
    Path("references") / "first-batch-source-register.md",
]

REQUIRED_CASE_FILES = REQUIRED_TEMPLATE_FILES.copy()

STRICT_FRONTMATTER_FIELDS = [
    "case_id",
    "title",
    "primary_domain",
    "secondary_tags",
    "method_tags",
    "research_question",
    "analytical_objective",
    "replication_type",
    "data_mode",
    "data_sources",
    "literature_sources",
    "seed",
    "assumption_note",
    "claim_boundary",
    "expected_artifacts",
    "validation_scope",
    "status",
]

REQUIRED_PARAMS_FIELDS = ["seed"]
FORBIDDEN_PARAMS_FIELDS = {"case_id", "data_mode", "replication_type", "claim_boundary"}

FORBIDDEN_DIRECTORIES = {".venv", "__pycache__", ".ipynb_checkpoints"}
MAX_DATA_FILE_BYTES = 25 * 1024 * 1024


def build_expected_paths(root: Path) -> list[Path]:
    return [
        root / "cases" / "经济金融",
        root / "cases" / "社会科学",
        root / "cases" / "市场营销与运营",
        root / "references",
        root / "scripts",
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate catalog structure and case contracts.")
    _ = parser.add_argument("--root", default=".", help="Catalog root path, defaults to current directory.")
    _ = parser.add_argument(
        "--case",
        help="Validate a single case directory relative to --root or as an absolute path.",
    )
    _ = parser.add_argument(
        "--structure-only",
        action="store_true",
        help="Validate only the required top-level catalog structure.",
    )
    _ = parser.add_argument(
        "--template-only",
        action="store_true",
        help="Validate only the required template files under templates/case-template/.",
    )
    _ = parser.add_argument(
        "--index-only",
        action="store_true",
        help="Validate only the required catalog and domain index files.",
    )
    _ = parser.add_argument(
        "--strict",
        action="store_true",
        help="Run strict case validation for one case or the full catalog.",
    )
    _ = parser.add_argument(
        "--artifact-hygiene",
        action="store_true",
        help="Check forbidden artifacts, notebook outputs, and oversized data files.",
    )
    _ = parser.add_argument(
        "--require-cases",
        type=int,
        metavar="N",
        help="When used with --strict, require at least N valid cases to be found.",
    )
    return parser.parse_args()


def validate_structure(root: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []

    for path in build_expected_paths(root):
        if not path.exists():
            errors.append(f"missing required path: {path.relative_to(root)}")
        elif not path.is_dir():
            errors.append(f"expected directory but found file: {path.relative_to(root)}")

    cases_root = root / "cases"
    if not cases_root.exists():
        errors.append("missing required path: cases")
        return False, errors

    if not cases_root.is_dir():
        errors.append("expected directory but found file: cases")
        return False, errors

    actual_case_domains = {entry.name for entry in cases_root.iterdir() if entry.is_dir()}
    illegal_domains = sorted(actual_case_domains - VALID_CASE_DOMAINS)
    missing_domains = sorted(VALID_CASE_DOMAINS - actual_case_domains)

    for name in missing_domains:
        errors.append(f"missing required cases domain: {name}")

    for name in illegal_domains:
        errors.append(f"illegal cases domain: {name}")

    return not errors, errors


def validate_required_files(base_dir: Path, relative_paths: Iterable[Path], label: str) -> list[str]:
    errors: list[str] = []
    for relative_path in relative_paths:
        file_path = base_dir / relative_path
        if not file_path.exists():
            errors.append(f"missing {label}: {file_path}")
        elif file_path.is_dir():
            errors.append(f"expected file but found directory for {label}: {file_path}")
    return errors


def display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def load_frontmatter(markdown_path: Path) -> dict[str, Any]:
    text = markdown_path.read_text(encoding="utf-8")
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        raise ValueError("missing YAML frontmatter start marker")

    start_marker_length = 5 if text.startswith("---\r\n") else 4
    end_marker_options = ("\n---\n", "\n---\r\n")
    end_marker = -1
    for marker in end_marker_options:
        candidate = text.find(marker, start_marker_length)
        if candidate != -1 and (end_marker == -1 or candidate < end_marker):
            end_marker = candidate
    if end_marker == -1:
        raise ValueError("missing YAML frontmatter end marker")

    payload = text[start_marker_length:end_marker]
    data = yaml.safe_load(payload) or {}
    if not isinstance(data, dict):
        raise ValueError("frontmatter must parse to a mapping")
    return cast(dict[str, Any], data)


def load_params(params_path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(params_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("params.yaml must parse to a mapping")
    return cast(dict[str, Any], payload)


def resolve_case_path(root: Path, case_value: str) -> Path:
    candidate = Path(case_value)
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve()


def iter_case_dirs(root: Path) -> list[Path]:
    cases_root = root / "cases"
    case_dirs: list[Path] = []
    if not cases_root.exists() or not cases_root.is_dir():
        return case_dirs

    for domain_dir in sorted(cases_root.iterdir(), key=lambda entry: entry.name):
        if not domain_dir.is_dir() or domain_dir.name not in VALID_CASE_DOMAINS:
            continue
        for case_dir in sorted(domain_dir.iterdir(), key=lambda entry: entry.name):
            if case_dir.is_dir():
                case_dirs.append(case_dir)
    return case_dirs


def validate_template(root: Path) -> tuple[bool, list[str]]:
    template_root = root / "templates" / "case-template"
    if not template_root.exists() or not template_root.is_dir():
        return False, [f"missing template directory: {template_root}"]
    errors = validate_required_files(template_root, REQUIRED_TEMPLATE_FILES, "template file")
    return not errors, errors


def validate_indexes(root: Path) -> tuple[bool, list[str]]:
    errors = validate_required_files(root, REQUIRED_INDEX_FILES, "index file")
    return not errors, errors


def validate_case_strict(case_dir: Path, root: Path) -> list[str]:
    errors: list[str] = []

    if not case_dir.exists():
        return [f"missing case directory: {case_dir}"]
    if not case_dir.is_dir():
        return [f"expected case directory but found file: {case_dir}"]

    errors.extend(validate_required_files(case_dir, REQUIRED_CASE_FILES, "required case file"))

    index_path = case_dir / "index.md"
    if not index_path.exists() or index_path.is_dir():
        return errors

    try:
        frontmatter = load_frontmatter(index_path)
    except (OSError, yaml.YAMLError, ValueError) as exc:
        errors.append(f"invalid frontmatter in {display_path(index_path, root)}: {exc}")
        return errors

    for field in STRICT_FRONTMATTER_FIELDS:
        value = frontmatter.get(field)
        if value is None:
            errors.append(f"missing frontmatter field '{field}' in {display_path(index_path, root)}")
            continue
        if isinstance(value, str) and not value.strip():
            errors.append(f"empty frontmatter field '{field}' in {display_path(index_path, root)}")
        if isinstance(value, list) and not value:
            errors.append(f"empty frontmatter field '{field}' in {display_path(index_path, root)}")

    params_path = case_dir / "params.yaml"
    if params_path.exists() and params_path.is_file():
        try:
            params = load_params(params_path)
        except (OSError, yaml.YAMLError, ValueError) as exc:
            errors.append(f"invalid params.yaml in {display_path(params_path, root)}: {exc}")
            params = None
        if params is not None:
            for field in REQUIRED_PARAMS_FIELDS:
                value = params.get(field)
                if value is None:
                    errors.append(f"missing params field '{field}' in {display_path(params_path, root)}")
                    continue
                if isinstance(value, str) and not value.strip():
                    errors.append(f"empty params field '{field}' in {display_path(params_path, root)}")
            for field in sorted(FORBIDDEN_PARAMS_FIELDS):
                if field in params:
                    errors.append(
                        f"forbidden duplicated metadata field '{field}' in {display_path(params_path, root)}"
                    )

    references_path = case_dir / "references.bib"
    if references_path.exists() and references_path.is_file():
        if not references_path.read_text(encoding="utf-8").strip():
            errors.append(f"empty references.bib in {display_path(case_dir, root)}")

    return errors


def validate_strict(root: Path, case_value: str | None, require_cases: int | None) -> tuple[bool, list[str], int]:
    if case_value:
        case_dirs = [resolve_case_path(root, case_value)]
    else:
        case_dirs = iter_case_dirs(root)

    all_errors: list[str] = []
    for case_dir in case_dirs:
        all_errors.extend(validate_case_strict(case_dir, root))

    if require_cases is not None and len(case_dirs) < require_cases:
        all_errors.append(
            f"expected at least {require_cases} cases, found {len(case_dirs)}"
        )

    return not all_errors, all_errors, len(case_dirs)


def notebook_has_outputs(notebook_path: Path) -> bool:
    data = json.loads(notebook_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return False
    cells = data.get("cells", [])
    if not isinstance(cells, list):
        return False
    for cell in cells:
        if not isinstance(cell, dict):
            continue
        if cell.get("cell_type") != "code":
            continue
        outputs = cell.get("outputs", [])
        execution_count = cell.get("execution_count")
        if isinstance(outputs, list) and outputs:
            return True
        if execution_count is not None:
            return True
    return False


def validate_artifact_hygiene(root: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []

    for path in root.rglob("*"):
        if path.name == ".git":
            continue
        if path.is_dir() and path.name in FORBIDDEN_DIRECTORIES:
            errors.append(f"forbidden artifact directory present: {display_path(path, root)}")
            continue
        if path.is_file() and path.suffix == ".ipynb":
            try:
                if notebook_has_outputs(path):
                    errors.append(f"notebook contains uncleared outputs: {display_path(path, root)}")
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"unable to inspect notebook {display_path(path, root)}: {exc}")
        if path.is_file() and "data" in path.parts and path.stat().st_size > MAX_DATA_FILE_BYTES:
            errors.append(
                f"oversized data file (>25MB): {display_path(path, root)} ({path.stat().st_size} bytes)"
            )

    return not errors, errors


def print_errors(errors: Iterable[str]) -> None:
    for error in errors:
        print(error, file=sys.stderr)


def main() -> int:
    args = parse_args()
    root = Path(cast(str, args.root)).resolve()

    structure_only = cast(bool, args.structure_only)
    template_only = cast(bool, args.template_only)
    index_only = cast(bool, args.index_only)
    strict = cast(bool, args.strict)
    artifact_hygiene = cast(bool, args.artifact_hygiene)
    case_value = cast(str | None, args.case)
    require_cases = cast(int | None, args.require_cases)

    selected_modes = [structure_only, template_only, index_only, strict, artifact_hygiene]
    if sum(1 for mode in selected_modes if mode) != 1:
        print(
            "Select exactly one validation mode: --structure-only, --template-only, --index-only, --strict, or --artifact-hygiene.",
            file=sys.stderr,
        )
        return 2

    if case_value and not strict:
        print("--case can only be used together with --strict.", file=sys.stderr)
        return 2

    if require_cases is not None and not strict:
        print("--require-cases can only be used together with --strict.", file=sys.stderr)
        return 2

    if structure_only:
        ok, errors = validate_structure(root)
        if ok:
            print("structure valid")
            return 0
        print_errors(errors)
        return 1

    if template_only:
        ok, errors = validate_template(root)
        if ok:
            print("template valid")
            return 0
        print_errors(errors)
        return 1

    if index_only:
        ok, errors = validate_indexes(root)
        if ok:
            print("index valid")
            return 0
        print_errors(errors)
        return 1

    if strict:
        ok, errors, count = validate_strict(root, case_value, require_cases)
        if ok:
            if case_value:
                print("case valid")
                return 0
            print(f"{count} cases validated, 0 blocking errors")
            return 0
        print_errors(errors)
        print(f"{count} cases validated, {len(errors)} blocking errors", file=sys.stderr)
        return 1

    ok, errors = validate_artifact_hygiene(root)
    if ok:
        print("artifact hygiene valid")
        return 0
    print_errors(errors)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
