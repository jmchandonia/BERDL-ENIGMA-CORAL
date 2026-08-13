import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "inventory_feba_edr_versions.py"
SPEC = importlib.util.spec_from_file_location("inventory_feba_edr_versions", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class InventoryFebaEdrVersionsTests(unittest.TestCase):
    def test_versions_are_exact_to_strain_and_numeric(self):
        text = "\n".join(
            [
                "genome_processing/FW300-N2E2/assembliesAndAnnotations/FW300-N2E2.1/",
                "genome_processing/FW300-N2E2/assembliesAndAnnotations/FW300-N2E2.3/file",
                "genome_processing/FW300-N2E20/assembliesAndAnnotations/FW300-N2E20.9/",
                "FW300-N2E2.3",
            ]
        )
        self.assertEqual(MODULE.versions_for_strain(text, "FW300-N2E2"), [1, 3])

    def test_listing_text_accepts_mc_jsonl_and_plain_lines(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "listing.jsonl"
            path.write_text(
                json.dumps({
                    "status": "success",
                    "mc_result": {"key": "a/Strain.1/file"},
                })
                + "\nplain/Strain.3/file\n"
            )
            value = MODULE.listing_text(path)
            self.assertIn("a/Strain.1/file", value)
            self.assertIn("plain/Strain.3/file", value)

    def test_listing_text_filters_structured_scope(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "listing.jsonl"
            path.write_text(
                json.dumps({
                    "scope": "genome_processing",
                    "mc_result": {"key": "a/Strain.1/"},
                })
                + "\n"
                + json.dumps({
                    "scope": "genome_processing_withdrawn",
                    "mc_result": {"key": "a/Strain.2/"},
                })
                + "\n"
            )
            value = MODULE.listing_text(path, "genome_processing")
            self.assertIn("Strain.1", value)
            self.assertNotIn("Strain.2", value)


if __name__ == "__main__":
    unittest.main()
