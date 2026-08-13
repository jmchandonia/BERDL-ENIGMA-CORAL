import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "download_feba_edr_candidates.py"
SPEC = importlib.util.spec_from_file_location("download_feba_edr_candidates", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DownloadFebaEdrCandidatesTests(unittest.TestCase):
    def test_selected_files_requires_and_selects_exact_pair(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "files.jsonl"
            records = []
            for filename, size in (("S_contigs.fasta", 10), ("S_Prodigal.gff", 20)):
                records.append(
                    {
                        "scope": "genome_processing",
                        "strain": "S",
                        "version_key": "S.1/",
                        "prefix": "alias/root/S.1/",
                        "mc_result": {
                            "type": "file",
                            "key": filename,
                            "size": size,
                            "etag": filename,
                        },
                    }
                )
            path.write_text("".join(json.dumps(row) + "\n" for row in records))
            selected = MODULE.selected_files(path)
            self.assertEqual(len(selected), 2)
            self.assertEqual({row["expected_size"] for row in selected}, {10, 20})
            self.assertTrue(all(row["version"] == "S.1" for row in selected))

            path.write_text(json.dumps(records[0]) + "\n")
            with self.assertRaisesRegex(ValueError, "missing"):
                MODULE.selected_files(path)


if __name__ == "__main__":
    unittest.main()
