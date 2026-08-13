import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "compare_feba_edr_candidate_assemblies.py"
SPEC = importlib.util.spec_from_file_location("compare_feba_edr_candidate_assemblies", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CompareFebaEdrCandidateAssembliesTests(unittest.TestCase):
    def test_fasta_fingerprint_is_order_and_case_independent(self):
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first.fna"
            second = Path(temporary) / "second.fna"
            first.write_text(">b\naaa\n>a\nACGT\n")
            second.write_text(">a description\nac\ngt\n>b\nAAA\n")
            self.assertEqual(MODULE.fasta_fingerprint(first), MODULE.fasta_fingerprint(second))


if __name__ == "__main__":
    unittest.main()
