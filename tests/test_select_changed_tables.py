import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "sync-coral-to-berdl"
    / "scripts"
    / "select_changed_tables.py"
)


def table_manifest(name: str) -> dict:
    return {
        "table": name,
        "hashes": {
            "data_sha256": "data",
            "schema_sha256": "schema",
            "comments_sha256": "comments",
        },
    }


class SelectChangedTablesTests(unittest.TestCase):
    def run_selector(
        self,
        *,
        prior_enabled: bool = True,
        force: bool = False,
        live: bool | None = None,
    ) -> dict:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "current"
            (run_dir / "manifests").mkdir(parents=True)
            (run_dir / "ingest").mkdir()
            (run_dir / "reports").mkdir()
            table = table_manifest("ddt_brick0000012")
            (run_dir / "manifests" / "current.json").write_text(
                json.dumps({"run_id": "current", "tables": [table]})
            )
            (run_dir / "ingest" / "config.dry_run.json").write_text(
                json.dumps({"tables": [{"name": table["table"], "enabled": True}]})
            )
            previous_manifest = root / "previous.json"
            previous_manifest.write_text(
                json.dumps({"run_id": "previous", "tables": [table_manifest(table["table"])]})
            )
            previous_config = root / "previous_config.json"
            previous_config.write_text(
                json.dumps({"tables": [{"name": table["table"], "enabled": prior_enabled}]})
            )
            command = [
                sys.executable,
                str(SCRIPT),
                "--run-dir",
                str(run_dir),
                "--previous-manifest",
                str(previous_manifest),
                "--previous-config",
                str(previous_config),
            ]
            if force:
                force_file = root / "force.txt"
                force_file.write_text(f"{table['table']}\n")
                command.extend(["--force-reload-file", str(force_file)])
            if live is not None:
                live_file = root / "live.txt"
                live_file.write_text(f"{table['table']}\n" if live else "")
                command.extend(["--live-tables-file", str(live_file)])
            subprocess.run(command, check=True, capture_output=True, text=True)
            return json.loads((run_dir / "reports" / "manifest_diff.json").read_text())

    def test_reactivates_prior_obsolete_table(self):
        report = self.run_selector(prior_enabled=False)
        self.assertEqual(report["reactivated_tables"], ["ddt_brick0000012"])
        self.assertEqual(report["ingest_tables"], ["ddt_brick0000012"])

    def test_unchanged_current_table_is_not_reloaded(self):
        report = self.run_selector(prior_enabled=True, live=True)
        self.assertEqual(report["unchanged_tables"], ["ddt_brick0000012"])
        self.assertEqual(report["ingest_tables"], [])

    def test_force_reload_marks_import_strategy_change(self):
        report = self.run_selector(force=True)
        self.assertEqual(report["forced_reload_tables"], ["ddt_brick0000012"])
        self.assertEqual(report["ingest_tables"], ["ddt_brick0000012"])

    def test_missing_live_table_is_reloaded(self):
        report = self.run_selector(live=False)
        self.assertEqual(report["missing_live_reload_tables"], ["ddt_brick0000012"])
        self.assertEqual(report["ingest_tables"], ["ddt_brick0000012"])


if __name__ == "__main__":
    unittest.main()
