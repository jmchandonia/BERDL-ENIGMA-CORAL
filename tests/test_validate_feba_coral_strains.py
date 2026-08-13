import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "validate_feba_coral_strains.py"
SPEC = importlib.util.spec_from_file_location("validate_feba_coral_strains", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ValidateFebaCoralStrainsTests(unittest.TestCase):
    def test_compare_live_rows_reports_all_outcomes(self):
        manifest = [
            {"fitprivate_orgId": "a", "sdt_strain_id": "S1", "sdt_strain_name": "A"},
            {"fitprivate_orgId": "b", "sdt_strain_id": "S2", "sdt_strain_name": "B"},
            {"fitprivate_orgId": "c", "sdt_strain_id": "S3", "sdt_strain_name": "C"},
            {"fitprivate_orgId": "d", "sdt_strain_id": "S4", "sdt_strain_name": "D"},
        ]
        live = [
            {"sdt_strain_id": "S1", "sdt_strain_name": "A"},
            {"sdt_strain_id": "changed", "sdt_strain_name": "B"},
            {"sdt_strain_id": "S3", "sdt_strain_name": "C"},
            {"sdt_strain_id": "other", "sdt_strain_name": "C"},
        ]
        results = MODULE.compare_live_rows(manifest, live)
        self.assertEqual(
            [row["status"] for row in results],
            ["verified", "id_mismatch", "ambiguous", "missing"],
        )


if __name__ == "__main__":
    unittest.main()
