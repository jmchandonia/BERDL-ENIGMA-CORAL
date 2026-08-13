import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "record_feba_genomes_260812.py"
SPEC = importlib.util.spec_from_file_location("record_feba_genomes_260812", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RecordFebaGenomesTests(unittest.TestCase):
    def test_manifest_contains_version(self):
        text = "S\t2026-01-01\tGenome\tS/assembliesAndAnnotations/S.3/S_Prodigal.gff\n"
        self.assertTrue(MODULE.manifest_contains_version(text, "S", "S.3"))
        self.assertFalse(MODULE.manifest_contains_version(text, "S", "S.4"))
        self.assertFalse(MODULE.manifest_contains_version("S.30\n", "S", "S.3"))
        with self.assertRaisesRegex(ValueError, "does not belong"):
            MODULE.manifest_contains_version(text, "S", "T.3")

    def test_read_genomes_requires_columns(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "genomes.tsv"
            path.write_text("strain\nS\n")
            with self.assertRaisesRegex(ValueError, "missing columns"):
                MODULE.read_genomes(path)


if __name__ == "__main__":
    unittest.main()
