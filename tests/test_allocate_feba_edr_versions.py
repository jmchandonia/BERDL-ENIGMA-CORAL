import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "allocate_feba_edr_versions.py"
SPEC = importlib.util.spec_from_file_location("allocate_feba_edr_versions", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class AllocateFebaEdrVersionsTests(unittest.TestCase):
    def test_next_version_reserves_two_and_combines_histories(self):
        self.assertEqual(MODULE.next_version([], []), 1)
        self.assertEqual(MODULE.next_version([1], []), 3)
        self.assertEqual(MODULE.next_version([1, 2, 4], [3, 4, 5]), 6)


if __name__ == "__main__":
    unittest.main()
