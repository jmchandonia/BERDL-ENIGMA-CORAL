#!/usr/bin/env python3
"""Generate and publish ENIGMA CORAL schema references to dependent skills."""

from __future__ import annotations

import argparse
import filecmp
import shutil
from pathlib import Path

from generate_schema_markdown import (
    _load_json,
    export_database_schema,
    export_table_to_markdown,
)


SCHEMA_FILES = (
    "ddt_ndarray_table.md",
    "enigma_coral_schema.md",
    "sys_ddt_typedef_table.md",
)
REPO_TARGETS = {
    "skills/berdl-mcp/references": ("enigma_coral_schema.md",),
    "skills/enigma-berdl-query/references": SCHEMA_FILES,
}


def _copy_and_verify(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    if not filecmp.cmp(source, target, shallow=False):
        raise RuntimeError(f"Schema reference differs after copy: {target}")


def _generate(run_dir: Path, schema_dir: Path, sample_rows: int) -> None:
    config = _load_json(run_dir / "ingest" / "config.dry_run.json")
    schema_dir.mkdir(parents=True, exist_ok=True)
    export_table_to_markdown(
        config,
        "ddt_ndarray",
        schema_dir / "ddt_ndarray_table.md",
    )
    export_table_to_markdown(
        config,
        "sys_ddt_typedef",
        schema_dir / "sys_ddt_typedef_table.md",
    )
    export_database_schema(
        config,
        schema_dir / "enigma_coral_schema.md",
        sample_rows,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--sample-rows", type=int, default=5)
    parser.add_argument(
        "--installed-skills-root",
        type=Path,
        help="Also refresh dependent installed skills under this directory.",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    schema_dir = repo_root / "schema"
    _generate(args.run_dir.resolve(), schema_dir, args.sample_rows)

    copied = []
    for relative_dir, names in REPO_TARGETS.items():
        target_dir = repo_root / relative_dir
        for name in names:
            target = target_dir / name
            _copy_and_verify(schema_dir / name, target)
            copied.append(target)

    if args.installed_skills_root:
        installed_root = args.installed_skills_root.expanduser().resolve()
        for relative_dir, names in REPO_TARGETS.items():
            skill_name = Path(relative_dir).parts[1]
            target_dir = installed_root / skill_name / "references"
            if not target_dir.parent.exists():
                raise FileNotFoundError(f"Installed dependent skill not found: {target_dir.parent}")
            for name in names:
                target = target_dir / name
                _copy_and_verify(schema_dir / name, target)
                copied.append(target)

    print(f"Generated {len(SCHEMA_FILES)} schema files in {schema_dir}")
    print(f"Copied and verified {len(copied)} dependent schema references")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
