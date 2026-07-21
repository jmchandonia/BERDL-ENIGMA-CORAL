#!/usr/bin/env python3
"""Normalize legacy ENIGMA repository links for BERDL table data."""

from __future__ import annotations

import csv
from pathlib import Path


REPOSITORY_RELATIVE_PREFIX = "enigma-data-repository/"
TEXT_REWRITES = (
    ("https://genomics.lbl.gov/enigma-data/", REPOSITORY_RELATIVE_PREFIX),
    (
        "/auto/sahara/namib/home/gtl/enigma-data-repository/",
        REPOSITORY_RELATIVE_PREFIX,
    ),
)


def normalize_repository_text(value: str) -> str:
    normalized = value or ""
    for old, new in TEXT_REWRITES:
        normalized = normalized.replace(old, new)
    return normalized


def _contains_legacy_prefix(path: Path) -> bool:
    prefixes = tuple(old.encode("utf-8") for old, _ in TEXT_REWRITES)
    overlap = max(map(len, prefixes)) - 1
    trailing = b""
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            searchable = trailing + chunk
            if any(prefix in searchable for prefix in prefixes):
                return True
            trailing = searchable[-overlap:]
    return False


def normalize_repository_links_in_tsv(path: Path) -> dict[str, int]:
    """Rewrite repository links in a TSV atomically, preserving untouched files."""
    if not _contains_legacy_prefix(path):
        return {"rows": 0, "cells_changed": 0, "replacements": 0}

    temporary = path.with_name(f".{path.name}.normalizing")
    rows = 0
    cells_changed = 0
    replacements = 0
    try:
        with (
            path.open(newline="", encoding="utf-8") as in_handle,
            temporary.open("w", newline="", encoding="utf-8") as out_handle,
        ):
            reader = csv.reader(in_handle, delimiter="\t")
            writer = csv.writer(out_handle, delimiter="\t")
            for row in reader:
                normalized_row = []
                for value in row:
                    normalized = normalize_repository_text(value)
                    if normalized != value:
                        cells_changed += 1
                        replacements += sum(value.count(old) for old, _ in TEXT_REWRITES)
                    normalized_row.append(normalized)
                writer.writerow(normalized_row)
                rows += 1
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return {
        "rows": rows,
        "cells_changed": cells_changed,
        "replacements": replacements,
    }
