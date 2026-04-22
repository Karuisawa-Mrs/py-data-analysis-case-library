from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> bool:
    parser = argparse.ArgumentParser(
        description="Case analysis script template. This file is the single source of truth."
    )
    _ = parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run the minimal pipeline and emit a lightweight artifact.",
    )
    args = parser.parse_args()
    smoke_test_value = getattr(args, "smoke_test", False)
    return smoke_test_value if isinstance(smoke_test_value, bool) else False


def resolve_paths() -> dict[str, Path]:
    case_dir = Path(__file__).resolve().parent
    paths = {
        "case_dir": case_dir,
        "data_dir": case_dir / "data",
        "output_dir": case_dir / "outputs",
        "params_file": case_dir / "params.yaml",
        "index_file": case_dir / "index.md",
    }
    _ = paths["output_dir"].mkdir(parents=True, exist_ok=True)
    return paths


def run(smoke_test: bool = False) -> Path:
    paths = resolve_paths()
    artifact_name = "smoke_test.txt" if smoke_test else "summary.txt"
    artifact_path = paths["output_dir"] / artifact_name
    mode_label = "SMOKE TEST" if smoke_test else "FULL RUN"

    lines = [
        f"mode: {mode_label}",
        f"case_dir: {paths['case_dir'].name}",
        f"params_file: {paths['params_file'].name}",
        f"index_file: {paths['index_file'].name}",
        "note: replace this stub with case-specific analysis logic.",
    ]
    _ = artifact_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return artifact_path


if __name__ == "__main__":
    smoke_test = parse_args()
    output_path = run(smoke_test=smoke_test)
    print(f"Generated: {output_path}")
