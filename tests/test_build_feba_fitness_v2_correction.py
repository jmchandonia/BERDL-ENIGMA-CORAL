from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
SCRIPT = TOOLS / "build_feba_fitness_v2_correction.py"
SPEC = importlib.util.spec_from_file_location("build_feba_fitness_v2_correction", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def source_document() -> dict:
    base = MODULE.base
    return {
        "name": "feba_tnseq_fitness_test.1.ndarray",
        "description": "test fitness brick",
        "data_type": base.term("fitness_data"),
        "array_context": [],
        "n_dimensions": 2,
        "dim_context": [
            {
                "data_type": base.term("gene"),
                "size": 1,
                "typed_values": [base.typed_values("gene_id", "object_ref", ["test.1:locus1"])],
            },
            {
                "data_type": base.term("condition"),
                "size": 2,
                "typed_values": [
                    base.typed_values("condition_id", "object_ref", ["test:c1", "test:c2"])
                ],
            },
        ],
        "typed_values": [
            base.typed_values("fitness", "float", [1.0, -1.0], unit_key="log_ratio"),
            base.typed_values("average", "float", [2.0, -2.0], unit_key="dimensionless"),
        ],
    }


def manifest() -> dict[str, str]:
    return {
        "brick_name": "feba_tnseq_fitness_test.1.ndarray",
        "gene_count": "1",
        "condition_count": "2",
        "cell_count": "2",
    }


def test_replacement_adds_marker_without_changing_scientific_payload() -> None:
    source = source_document()
    replacement = MODULE.build_replacement_document(source, manifest())
    assert replacement["name"] == "feba_tnseq_fitness_test.1_v2.ndarray"
    assert MODULE.immutable_array_payload(replacement) == MODULE.immutable_array_payload(source)
    MODULE.base.validate_data_variables_context(replacement)


def test_replacement_rejects_already_marked_source() -> None:
    source = source_document()
    source["array_context"] = [
        MODULE.base.scalar_property(
            "data_variables_type", "oterm_ref", MODULE.base.TERMS["fitness_data"].ref
        )
    ]
    with pytest.raises(ValueError, match="already has a data-variables marker"):
        MODULE.build_replacement_document(source, manifest())
