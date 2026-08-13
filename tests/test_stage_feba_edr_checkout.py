import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "stage_feba_edr_checkout.py"
SPEC = importlib.util.spec_from_file_location("stage_feba_edr_checkout", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class StageFebaEdrCheckoutTests(unittest.TestCase):
    def test_version_rules(self):
        self.assertEqual(MODULE.next_version([], []), 1)
        self.assertEqual(MODULE.next_version([1], []), 3)
        self.assertEqual(MODULE.next_version([1, 4], [2, 5]), 6)
        self.assertEqual(MODULE.target_number("S", "S.3"), 3)
        with self.assertRaisesRegex(ValueError, "Invalid allocated"):
            MODULE.target_number("S", "T.3")


if __name__ == "__main__":
    unittest.main()
