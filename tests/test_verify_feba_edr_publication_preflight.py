import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "verify_feba_edr_publication_preflight.py"
SPEC = importlib.util.spec_from_file_location("verify_feba_edr_publication_preflight", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class VerifyFebaEdrPublicationPreflightTests(unittest.TestCase):
    def test_next_version(self):
        self.assertEqual(MODULE.next_version([], []), 1)
        self.assertEqual(MODULE.next_version([1], []), 3)
        self.assertEqual(MODULE.next_version([1, 4], [2, 5]), 6)


if __name__ == "__main__":
    unittest.main()
