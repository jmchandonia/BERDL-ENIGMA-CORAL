import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "compare_feba_edr_candidate_annotations.py"
SPEC = importlib.util.spec_from_file_location("compare_feba_edr_candidate_annotations", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CompareFebaEdrCandidateAnnotationsTests(unittest.TestCase):
    def test_compare_rejects_extra_features_and_metadata_difference(self):
        source = {
            "g1": {
                "sys_name": "g1", "scaffold_id": "c", "begin": 1, "end": 3,
                "feature_type": "CDS", "strand": "+", "gene": "x",
                "description": "source", "xrefs": {("refseq", "R1")},
                "gc_fraction": "0.5",
            }
        }
        candidate = {
            "g1": {
                "scaffold_id": "c", "begin": 1, "end": 3, "feature_type": "CDS",
                "strand": "+", "attributes": {
                    "locus_tag": "g1", "gene": "x", "product": "candidate",
                    "gc_fraction": "0.5", "Dbxref": "RefSeq:R1",
                },
            },
            "extra": {
                "scaffold_id": "c", "begin": 4, "end": 5, "feature_type": "ncRNA",
                "strand": "+", "attributes": {},
            },
        }
        result = MODULE.compare(source, candidate)
        self.assertFalse(result["exact_annotation_match"])
        self.assertEqual(result["extra_candidate_feature_ids"], ["extra"])
        self.assertEqual(len(result["metadata_mismatches"]), 1)


if __name__ == "__main__":
    unittest.main()
