import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "export_feba_genomes_batch.py"
SPEC = importlib.util.spec_from_file_location("export_feba_genomes_batch", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ExportFebaGenomesBatchTests(unittest.TestCase):
    def test_split_version(self):
        self.assertEqual(MODULE.split_version("strain", "strain.3"), 3)
        with self.assertRaisesRegex(ValueError, "Invalid allocated"):
            MODULE.split_version("strain", "other.3")


if __name__ == "__main__":
    unittest.main()
