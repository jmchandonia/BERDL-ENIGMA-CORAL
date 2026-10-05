import importlib.util
import os
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SYNC_SCRIPTS = REPO_ROOT / "skills" / "sync-coral-to-berdl" / "scripts"


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, SYNC_SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pipeline = _load("run_sync_pipeline_test", "run_sync_pipeline.py")
verify = _load("verify_full_import_test", "verify_full_import.py")
full_import = _load("run_full_import_test", "run_full_import.py")


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

    def test_dotenv_resolves_token_aliases(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text(
                "KB_AUTH_TOKEN=actual-token\nKBASE_AUTH_TOKEN=$KB_AUTH_TOKEN\n",
                encoding="utf-8",
            )
            before = dict(os.environ)
            try:
                os.environ.pop("KB_AUTH_TOKEN", None)
                os.environ.pop("KBASE_AUTH_TOKEN", None)
                pipeline._load_dotenv(env_file)
                self.assertEqual(os.environ["KB_AUTH_TOKEN"], "actual-token")
                self.assertEqual(os.environ["KBASE_AUTH_TOKEN"], "actual-token")
            finally:
                os.environ.clear()
                os.environ.update(before)

    def test_dotenv_rejects_unresolved_token_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text("KBASE_AUTH_TOKEN=$MISSING_TOKEN\n", encoding="utf-8")
            before = dict(os.environ)
            try:
                os.environ.pop("KBASE_AUTH_TOKEN", None)
                os.environ.pop("MISSING_TOKEN", None)
                with self.assertRaisesRegex(ValueError, "Unresolved dotenv"):
                    pipeline._load_dotenv(env_file)
            finally:
                os.environ.clear()
                os.environ.update(before)

    def test_dotenv_can_prefer_refreshed_file_token_over_inherited_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text(
                "KB_AUTH_TOKEN=fresh-token\nKBASE_AUTH_TOKEN=$KB_AUTH_TOKEN\n",
                encoding="utf-8",
            )
            before = dict(os.environ)
            try:
                os.environ["KB_AUTH_TOKEN"] = "stale-token"
                os.environ["KBASE_AUTH_TOKEN"] = "stale-token"
                loaded = pipeline._load_dotenv(env_file, prefer_file=True)
                self.assertEqual(os.environ["KB_AUTH_TOKEN"], "fresh-token")
                self.assertEqual(os.environ["KBASE_AUTH_TOKEN"], "fresh-token")
                self.assertIn("KB_AUTH_TOKEN", loaded)
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

    def test_spark_readiness_retries_until_query_passes(self):
        failed = mock.Mock(returncode=1, stdout="", stderr="sidecar unavailable\n")
        passed = mock.Mock(returncode=0, stdout='[{"ready": 1}]\n', stderr="")
        with mock.patch.object(pipeline.Path, "is_file", return_value=True), mock.patch.object(
            pipeline.subprocess, "run", side_effect=[failed, passed]
        ) as run, mock.patch.object(pipeline.time, "sleep") as sleep:
            result = pipeline._wait_for_spark_readiness(
                attempts=3, interval_seconds=0.01
            )
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(run.call_count, 2)
        sleep.assert_called_once_with(0.01)

    def test_dual_write_stage_commands_use_separate_namespaces_and_providers(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            table_file = run_dir / "tables.txt"
            fk_file = run_dir / "fk.txt"
            table_file.write_text("sdt_genome\n", encoding="utf-8")
            fk_file.write_text("sdt_genome\n", encoding="utf-8")
            args = Namespace(
                run_dir=run_dir,
                run_id="sync-test",
                delta_namespace="enigma_coral",
                iceberg_namespace="enigma.coral",
                resume=False,
                skip_upload=False,
                skip_import=False,
                skip_delta_compat=False,
                apply_obsolete_drops=False,
                installed_skills_root=None,
            )
            with mock.patch.object(pipeline, "_resolve_worker_python", return_value="python"):
                import_cmd = pipeline._stage_command(
                    args, "import", table_file, fk_file, None
                )
                iceberg_cmd = pipeline._stage_command(
                    args, "verify_iceberg", table_file, fk_file, None
                )
                delta_cmd = pipeline._stage_command(
                    args, "verify_delta", table_file, fk_file, None
                )
                fk_cmd = pipeline._stage_command(
                    args, "foreign_keys", table_file, fk_file, None
                )
        self.assertIn("enigma.coral", import_cmd)
        self.assertIn("enigma_coral", import_cmd)
        self.assertEqual(iceberg_cmd[iceberg_cmd.index("--expected-provider") + 1], "iceberg")
        self.assertEqual(iceberg_cmd[iceberg_cmd.index("--namespace") + 1], "enigma.coral")
        self.assertEqual(delta_cmd[delta_cmd.index("--expected-provider") + 1], "delta")
        self.assertEqual(delta_cmd[delta_cmd.index("--namespace") + 1], "enigma_coral")
        self.assertEqual(fk_cmd[fk_cmd.index("--namespace") + 1], "enigma.coral")
        self.assertIn("--import-report", iceberg_cmd)
        self.assertIn("--import-report", fk_cmd)

    def test_empty_change_list_still_allows_automatic_iceberg_backfill(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            table_file = run_dir / "tables.txt"
            fk_file = run_dir / "fk.txt"
            table_file.write_text("", encoding="utf-8")
            fk_file.write_text("", encoding="utf-8")
            args = Namespace(
                run_dir=run_dir,
                run_id="sync-test",
                delta_namespace="enigma_coral",
                iceberg_namespace="enigma.coral",
                resume=False,
                skip_upload=False,
                skip_import=False,
                skip_delta_compat=False,
                apply_obsolete_drops=False,
                installed_skills_root=None,
            )
            with mock.patch.object(pipeline, "_resolve_worker_python", return_value="python"):
                command = pipeline._stage_command(
                    args, "import", table_file, fk_file, None
                )
        self.assertNotIn("--skip-import", command)
        self.assertNotIn("--skip-upload", command)


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
        sql = verify._count_sql("enigma.coral", ["sdt_genome", "ddt_brick0001693"])
        self.assertIn("FROM `enigma`.`coral`.`sdt_genome`", sql)
        self.assertIn("UNION ALL", sql)
        with self.assertRaises(ValueError):
            verify._count_sql("enigma_coral", ["bad-name"])

    def test_iceberg_verification_includes_automatic_backfill(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            table_file = root / "changed.txt"
            import_report = root / "import.json"
            table_file.write_text("changed_table\n", encoding="utf-8")
            import_report.write_text(
                '{"iceberg_backfill":{"missing_enabled_tables":["missing_table"]}}',
                encoding="utf-8",
            )
            self.assertEqual(
                verify._requested_verification_tables(
                    table_file, "iceberg", import_report
                ),
                {"changed_table", "missing_table"},
            )
            self.assertEqual(
                verify._requested_verification_tables(
                    table_file, "delta", import_report
                ),
                {"changed_table"},
            )


class SupportedFullImportTests(unittest.TestCase):
    def setUp(self):
        self.config = {"tenant": "enigma", "dataset": "coral"}
        self.table = {
            "name": "sdt_genome",
            "local_path": "/tmp/sdt_genome.tsv",
            "csv": {"quote": "\u0000", "escape": "\\", "multiLine": False},
            "table_comment": "genomes",
            "schema": [{"column": "name", "type": "STRING", "comment": "genome name"}],
        }

    def test_supported_config_targets_canonical_iceberg_namespace(self):
        config = full_import._supported_ingest_config(
            self.config, "s3a://bucket/run", self.table
        )
        self.assertEqual(config["tenant"], "enigma")
        self.assertEqual(config["dataset"], "coral")
        self.assertEqual(config["tables"][0]["bronze_path"], "s3a://bucket/run/data/sdt_genome.tsv")
        self.assertEqual(config["tables"][0]["comment"], "genomes")
        self.assertEqual(config["tables"][0]["schema"], self.table["schema"])
        # Legacy per-table preview options must not disable quoting: staged
        # TSVs are Python-csv quoted, so the reader needs quote/escape '"' and
        # multiLine, or quoted values keep literal quotes and split rows.
        self.assertEqual(config["defaults"]["tsv"]["quote"], '"')
        self.assertEqual(config["defaults"]["tsv"]["escape"], '"')
        self.assertTrue(config["defaults"]["tsv"]["multiLine"])
        self.assertEqual(config["defaults"]["tsv"]["delimiter"], "\t")

    def test_supported_writer_requires_successful_table_report(self):
        def ingest(config, **kwargs):
            return {"success": True, "tables": [{"name": "sdt_genome", "status": "success"}]}

        result = full_import._write_supported_iceberg_table(
            ingest, object(), object(), self.config, "s3a://bucket/run", self.table
        )
        self.assertEqual(result["provider"], "iceberg")
        self.assertEqual(result["namespace"], "enigma.coral")

        with self.assertRaisesRegex(RuntimeError, "failed"):
            full_import._write_supported_iceberg_table(
                lambda *args, **kwargs: {"success": False, "tables": [], "errors": ["failed"]},
                object(), object(), self.config, "s3a://bucket/run", self.table,
            )

    def test_full_table_quotes_catalog_namespace_and_table(self):
        self.assertEqual(
            full_import._full_table("enigma.coral", "sdt_genome"),
            "`enigma`.`coral`.`sdt_genome`",
        )

    def test_live_tables_supports_dotted_namespace(self):
        row = mock.Mock()
        row.asDict.return_value = {"tableName": "sdt_genome", "isTemporary": False}
        spark = mock.Mock()
        spark.sql.return_value.collect.return_value = [row]
        self.assertEqual(full_import._live_tables(spark, "enigma.coral"), {"sdt_genome"})
        spark.sql.assert_called_once_with("SHOW TABLES IN `enigma`.`coral`")


if __name__ == "__main__":
    unittest.main()
