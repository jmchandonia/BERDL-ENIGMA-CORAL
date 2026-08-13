from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "build_feba_coral_import.py"
SPEC = importlib.util.spec_from_file_location("build_feba_coral_import", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_stable_object_names() -> None:
    assert MODULE.qualified_gene_name("FW300-N2E2.3", "Pf6N2E2_1") == "FW300-N2E2.3:Pf6N2E2_1"
    assert MODULE.condition_name("FW300-N2E2", "set1IT012") == "FW300-N2E2:set1IT012"
    assert MODULE.library_name("FW300-N2E2.3", "pseudo6_N2E2_ML5c") == (
        "FW300-N2E2.3.pseudo6_N2E2_ML5c.tnseq_library"
    )


def test_object_refs_mirror_string_values() -> None:
    doc = MODULE.typed_values("gene_id", "object_ref", ["FW300-N2E2.3:Pf6N2E2_1"])
    assert doc["values"]["object_refs"] == doc["values"]["string_values"]


def test_assigned_ids_are_rejected() -> None:
    doc = {"values": {"object_refs": ["Gene0000001"]}}
    with pytest.raises(ValueError, match="CORAL-assigned IDs"):
        MODULE.validate_object_refs(doc, {"Gene0000001"})


def test_unknown_named_reference_is_rejected() -> None:
    doc = {"values": {"object_refs": ["FW300-N2E2.3:missing"]}}
    with pytest.raises(ValueError, match="do not resolve"):
        MODULE.validate_object_refs(doc, {"FW300-N2E2.3:Pf6N2E2_1"})


def test_aerobic_normalization() -> None:
    field = next(field for field in MODULE.EXPERIMENT_FIELDS if field.source == "aerobic")
    assert MODULE.normalize_value(field, "Aerobic") == 0
    assert MODULE.normalize_value(field, "anaerobic") == 1
    assert MODULE.normalize_value(field, "") is None


def test_identifier_components_reject_delimiters() -> None:
    with pytest.raises(ValueError, match="Unsafe FEBa locusId"):
        MODULE.qualified_gene_name("FW300-N2E2.3", "bad:locus")


def test_static_import_headers_are_coral_typedef_field_names() -> None:
    assert MODULE.STATIC_IMPORT_FIELDS == {
        "Genome": ["name", "strain", "n_contigs", "n_features", "link"],
        "Gene": ["gene_id", "genome", "aliases", "contig_number", "strand", "start", "stop", "function"],
        "Condition": ["name"],
        "TnSeq_Library": [
            "name",
            "genome",
            "primers_model",
            "n_mapped_reads",
            "n_barcodes",
            "n_usable_barcodes",
            "n_insertion_locations",
            "hit_rate_essential",
            "hit_rate_other",
        ],
    }


def test_static_import_preflight_rejects_berdl_aliases(tmp_path: Path) -> None:
    bad = tmp_path / "Genome.tsv"
    bad.write_text("name\tstrain_id\tn_contigs\tn_features\tlink\nG.1\tS\t1\t2\tpath\n")
    with pytest.raises(ValueError, match="headers do not match CORAL typedef field names"):
        MODULE.validate_static_import_tsv(bad, "Genome")


def test_static_import_preflight_rejects_missing_required_values(tmp_path: Path) -> None:
    bad = tmp_path / "Gene.tsv"
    bad.write_text(
        "gene_id\tgenome\taliases\tcontig_number\tstrand\tstart\tstop\tfunction\n"
        "G.1:locus\tnull\tlocus\t1\t+\t1\t2\tfunction\n"
    )
    with pytest.raises(ValueError, match="required CORAL property 'genome'"):
        MODULE.validate_static_import_tsv(bad, "Gene")


def test_n2e2_obsoletion_is_in_import_manifest_and_has_helper(tmp_path: Path) -> None:
    MODULE.write_import_helpers(
        tmp_path,
        [{"fitprivate_orgId": "pseudo6_N2E2", "brick_name": "feba_tnseq_fitness_FW300-N2E2.3.ndarray"}],
        "feba_tnseq_condition_metadata_20260813.ndarray",
    )
    files = tmp_path.joinpath("files_to_import.txt").read_text().splitlines()
    assert "post_import/process_update_data_n2e2_after_validation_20260813.tsv" in files
    helper = tmp_path.joinpath("import_n2e2_obsoletion_to_coral.py").read_text()
    assert helper.endswith(
        "toolx.upload_process('Update Data', 'process_update_data_n2e2_after_validation_20260813.tsv')\n"
    )
