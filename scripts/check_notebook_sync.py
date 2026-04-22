from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, cast

import yaml


VALID_CASE_DOMAINS = {
    "经济金融",
    "社会科学",
    "市场营销与运营",
}

BLOCKED_PATTERNS = [
    re.compile(r"(^|\n)\s*def\s+"),
    re.compile(r"(^|\n)\s*class\s+"),
    re.compile(r"(^|\n)\s*for\s+"),
    re.compile(r"(^|\n)\s*while\s+"),
    re.compile(r"\bimport\s+sklearn\b"),
    re.compile(r"\bfrom\s+sklearn\b"),
    re.compile(r"\bimport\s+statsmodels\b"),
    re.compile(r"\bfrom\s+statsmodels\b"),
    re.compile(r"\bfit\s*\("),
    re.compile(r"\btrain_test_split\s*\("),
]

ALLOWED_LINE_PATTERNS = [
    re.compile(r"^\s*$"),
    re.compile(r"^\s*#"),
    re.compile(r"^\s*%run\b"),
    re.compile(r"^\s*import\b"),
    re.compile(r"^\s*from\b"),
    re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_]*\s*=\s*[A-Za-z_][A-Za-z0-9_\.]*\([^=]*\)\s*$"),
    re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_\.]*\([^=]*\)\s*$"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check notebook metadata sync and logic drift.")
    _ = parser.add_argument("--root", default=".", help="Catalog root path, defaults to current directory.")
    _ = parser.add_argument(
        "--template-only",
        action="store_true",
        help="Validate the template notebook under templates/case-template without requiring case directories.",
    )
    return parser.parse_args()


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


def load_notebook(notebook_path: Path) -> dict[str, Any]:
    data = json.loads(notebook_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("notebook root must be a JSON object")
    return cast(dict[str, Any], data)


def get_notebook_text_map(notebook: dict[str, Any]) -> dict[str, str]:
    title = ""
    combined_sources: list[str] = []
    method_lines: list[str] = []

    cells = notebook.get("cells", [])
    if not isinstance(cells, list):
        return {"title": title, "combined": title, "method": ""}

    for cell in cells:
        if not isinstance(cell, dict):
            continue
        source = cell.get("source", [])
        if isinstance(source, list):
            text = "".join(part for part in source if isinstance(part, str))
        elif isinstance(source, str):
            text = source
        else:
            text = ""
        if cell.get("cell_type") == "markdown" and not title:
            for line in text.splitlines():
                if line.strip().startswith("#"):
                    title = line.lstrip("#").strip()
                    break
        combined_sources.append(text)
        if cell.get("cell_type") == "markdown":
            method_lines.append(text)

    return {
        "title": title,
        "combined": "\n".join(combined_sources),
        "method": "\n".join(method_lines),
    }


def normalize_method_tags(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def check_metadata_sync(case_dir: Path) -> list[str]:
    errors: list[str] = []
    index_path = case_dir / "index.md"
    notebook_path = case_dir / "analysis.ipynb"

    if not index_path.exists() or not index_path.is_file():
        return [f"missing index.md: {case_dir}"]
    if not notebook_path.exists() or not notebook_path.is_file():
        return [f"missing analysis.ipynb: {case_dir}"]

    try:
        frontmatter = load_frontmatter(index_path)
        notebook = load_notebook(notebook_path)
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        return [f"unable to inspect {case_dir}: {exc}"]

    text_map = get_notebook_text_map(notebook)
    combined_text = text_map["combined"]
    notebook_title = text_map["title"]
    notebook_method_text = text_map["method"]

    case_id = frontmatter.get("case_id")
    if not isinstance(case_id, str) or not case_id.strip():
        errors.append(f"missing or empty case_id in {index_path}")
    elif case_id not in combined_text:
        errors.append(f"notebook missing case_id '{case_id}' in {notebook_path}")

    title = frontmatter.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append(f"missing or empty title in {index_path}")
    elif notebook_title != title.strip():
        errors.append(
            f"notebook title mismatch for {case_dir}: expected '{title.strip()}', found '{notebook_title}'"
        )

    method_tags = normalize_method_tags(frontmatter.get("method_tags"))
    if not method_tags:
        errors.append(f"missing or empty method_tags in {index_path}")
    else:
        for tag in method_tags:
            if tag not in notebook_method_text:
                errors.append(f"notebook missing method tag '{tag}' in {notebook_path}")

    return errors


def is_allowed_line(line: str) -> bool:
    return any(pattern.match(line) for pattern in ALLOWED_LINE_PATTERNS)


def check_independent_logic(case_dir: Path) -> list[str]:
    notebook_path = case_dir / "analysis.ipynb"
    try:
        notebook = load_notebook(notebook_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"unable to inspect notebook logic for {case_dir}: {exc}"]

    errors: list[str] = []
    cells = notebook.get("cells", [])
    if not isinstance(cells, list):
        return [f"invalid notebook cells payload in {notebook_path}"]

    for index, cell in enumerate(cells, start=1):
        if not isinstance(cell, dict) or cell.get("cell_type") != "code":
            continue
        source = cell.get("source", [])
        if isinstance(source, list):
            text = "".join(part for part in source if isinstance(part, str))
        elif isinstance(source, str):
            text = source
        else:
            text = ""
        stripped = text.strip()
        if not stripped:
            continue
        if any(pattern.search(text) for pattern in BLOCKED_PATTERNS):
            errors.append(f"potential independent logic in {notebook_path} cell {index}")
            continue
        disallowed_lines = [line for line in text.splitlines() if not is_allowed_line(line)]
        if disallowed_lines:
            errors.append(f"non-wrapper code detected in {notebook_path} cell {index}")
    return errors


def main() -> int:
    args = parse_args()
    root = Path(cast(str, args.root)).resolve()
    template_only = cast(bool, args.template_only)
    case_dirs = [root / "templates" / "case-template"] if template_only else iter_case_dirs(root)

    if not case_dirs:
        if template_only:
            print("template notebook in sync")
            return 0
        print("0/0 notebooks in sync")
        return 0

    errors: list[str] = []
    for case_dir in case_dirs:
        errors.extend(check_metadata_sync(case_dir))
        errors.extend(check_independent_logic(case_dir))

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    if template_only:
        print("template notebook in sync")
        return 0

    print(f"{len(case_dirs)}/{len(case_dirs)} notebooks in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
