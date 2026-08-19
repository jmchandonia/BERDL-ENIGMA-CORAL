import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SYNC_SCRIPTS = REPO_ROOT / "skills" / "sync-coral-to-berdl" / "scripts"


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, SYNC_SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pipeline = _load("run_sync_pipeline_test", "run_sync_pipeline.py")
verify = _load("verify_full_import_test", "verify_full_import.py")


class SyncPipelineTests(unittest.TestCase):
    def test_dotenv_loads_without_overriding_and_normalizes_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text(
                "# comment\nKB_AUTH_TOKEN='from-file'\nKEEP=file-value\n",
                encoding="utf-8",
            )
            before = dict(os.environ)
            try:
                os.environ.pop("KB_AUTH_TOKEN", None)
                os.environ.pop("KBASE_AUTH_TOKEN", None)
                os.environ["KEEP"] = "caller-value"
                loaded = pipeline._load_dotenv(env_file)
                self.assertEqual(os.environ["KB_AUTH_TOKEN"], "from-file")
                self.assertEqual(os.environ["KBASE_AUTH_TOKEN"], "from-file")
                self.assertEqual(os.environ["KEEP"], "caller-value")
                self.assertIn("KBASE_AUTH_TOKEN", loaded)
            finally:
                os.environ.clear()
                os.environ.update(before)

    def test_pending_process_files_ignore_header_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            metadata = run_dir / "metadata"
            metadata.mkdir()
            header_only = metadata / "process_update_data_run1.tsv"
            header_only.write_text("name\ttype\n", encoding="utf-8")
            self.assertEqual(pipeline._nonempty_process_files(run_dir, "run1"), [])
            header_only.write_text("name\ttype\nprocess 1\tupdate data\n", encoding="utf-8")
            self.assertEqual(
                pipeline._nonempty_process_files(run_dir, "run1"),
                [str(header_only)],
            )

    def test_read_names_ignores_comments_and_blanks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tables.txt"
            path.write_text("# generated\n\na\n b \n", encoding="utf-8")
            self.assertEqual(pipeline._read_names(path), ["a", "b"])


class FullImportVerificationTests(unittest.TestCase):
    def test_expected_row_counts_use_manifest_values(self):
        manifest = {
            "tables": [
                {"table": "one", "row_count": 2},
                {"table": "two", "row_count": "3"},
                {"table": "missing"},
            ]
        }
        self.assertEqual(verify._expected_row_counts(manifest), {"one": 2, "two": 3})

    def test_count_sql_quotes_valid_identifiers(self):
        sql = verify._count_sql("enigma_coral", ["sdt_genome", "ddt_brick0001693"])
        self.assertIn("FROM `enigma_coral`.`sdt_genome`", sql)
        self.assertIn("UNION ALL", sql)
        with self.assertRaises(ValueError):
            verify._count_sql("enigma_coral", ["bad-name"])


if __name__ == "__main__":
    unittest.main()
