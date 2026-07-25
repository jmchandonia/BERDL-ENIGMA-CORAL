import csv
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "sync-coral-to-berdl"
    / "scripts"
)
sys.path.insert(0, str(SCRIPT_DIR))

from coral_metadata import (  # noqa: E402
    add_unresolved_terms,
    collect_brick_referenced_terms,
    collect_referenced_terms,
    load_ontology_terms,
    parse_obo_file,
    write_sys_oterm,
)


def term(name: str, parent: str = "") -> dict:
    return {
        "name": name,
        "parent": parent,
        "synonyms": [],
        "xrefs": [],
        "property_values": {},
    }


class CoralMetadataOntologyTests(unittest.TestCase):
    def test_collects_terms_from_brick_ontology_columns_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data_dir = root / "data"
            schema_dir = root / "schema"
            data_dir.mkdir()
            schema_dir.mkdir()
            (data_dir / "Brick0000012.tsv").write_text(
                "taxonomic_level_sys_oterm_id\tdescription\n"
                "ME:0000252\tCHEBI:15377 is only descriptive text\n",
                encoding="utf-8",
            )

            referenced = collect_referenced_terms(
                data_dir,
                schema_dir,
                {"ME:0000252", "CHEBI:15377"},
                [],
            )

            self.assertEqual(referenced, {"ME:0000252"})

    def test_collects_unresolved_brick_term_with_fallback_name(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "Brick.tsv"
            path.write_text(
                "compound_sys_oterm_id\tcompound_sys_oterm_name\n"
                "CHEBI:48505\tchemical role\n",
                encoding="utf-8",
            )
            names = {}
            referenced = collect_brick_referenced_terms(
                path, set(), fallback_names=names
            )

        self.assertEqual(referenced, {"CHEBI:48505"})
        self.assertEqual(names, {"CHEBI:48505": "chemical role"})

    def test_adds_unresolved_term_to_canonical_ontology(self):
        ontology_terms = {"chebi": {}}
        term_lookup = {}
        added = add_unresolved_terms(
            ontology_terms,
            term_lookup,
            {"CHEBI:48505"},
            {"CHEBI:48505": "chemical role"},
        )

        self.assertEqual(added, ["CHEBI:48505"])
        self.assertEqual(
            ontology_terms["chebi"]["CHEBI:48505"]["name"],
            "chemical role",
        )

    def test_obo_alternate_id_inherits_canonical_term_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "chebi.obo"
            path.write_text(
                "[Term]\n"
                "id: CHEBI:15963\n"
                "name: ribitol\n"
                "alt_id: CHEBI:48505\n",
                encoding="utf-8",
            )
            terms = parse_obo_file(path)

        self.assertEqual(terms["CHEBI:48505"]["name"], "ribitol")
        self.assertEqual(
            terms["CHEBI:48505"]["property_values"]["canonical_term_id"],
            ["CHEBI:15963"],
        )

    def test_write_sys_oterm_uses_canonical_source_once(self):
        ontology_terms = {
            "chebi": {"CHEBI:15377": term("water")},
            "envo": {"CHEBI:15377": term("imported water")},
        }
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "sys_oterm.tsv"
            stats = write_sys_oterm(ontology_terms, {"CHEBI:15377"}, output)
            with output.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["sys_oterm_id"], "CHEBI:15377")
            self.assertEqual(rows[0]["sys_oterm_ontology"], "chebi")
            self.assertEqual(rows[0]["sys_oterm_name"], "water")
            self.assertEqual(stats["chebi"]["included_terms"], 1)
            self.assertEqual(stats["envo"]["included_terms"], 0)

    def test_load_ontology_terms_uses_same_canonical_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            ontology_dir = Path(temporary)
            (ontology_dir / "chebi.obo").write_text(
                "[Term]\nid: CHEBI:15377\nname: water\n",
                encoding="utf-8",
            )
            (ontology_dir / "envo.obo").write_text(
                "[Term]\nid: CHEBI:15377\nname: imported water\n",
                encoding="utf-8",
            )

            _, lookup, names, _ = load_ontology_terms(ontology_dir)

            self.assertEqual(lookup["CHEBI:15377"][0], "chebi")
            self.assertEqual(names["CHEBI:15377"], "water")

    def test_unit_labels_remain_stable_when_canonical_name_differs(self):
        with tempfile.TemporaryDirectory() as temporary:
            ontology_dir = Path(temporary)
            (ontology_dir / "unit.obo").write_text(
                "[Term]\nid: UO:0000190\nname: ratio\n",
                encoding="utf-8",
            )
            (ontology_dir / "uo.obo").write_text(
                "[Term]\nid: UO:0000190\nname: ratio unit\n",
                encoding="utf-8",
            )

            _, lookup, names, _ = load_ontology_terms(ontology_dir)

            self.assertEqual(lookup["UO:0000190"][0], "uo")
            self.assertEqual(names["UO:0000190"], "ratio")


if __name__ == "__main__":
    unittest.main()
