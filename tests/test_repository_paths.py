import csv
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "skills" / "sync-coral-to-berdl" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from repository_paths import (  # noqa: E402
    TEXT_REWRITES,
    _contains_legacy_prefix,
    normalize_repository_links_in_tsv,
    normalize_repository_text,
)


class RepositoryPathTests(unittest.TestCase):
    def test_normalize_repository_text_handles_both_legacy_prefixes(self):
        self.assertEqual(
            normalize_repository_text(
                "/auto/sahara/namib/home/gtl/enigma-data-repository/a/b"
            ),
            "enigma-data-repository/a/b",
        )
        self.assertEqual(
            normalize_repository_text("https://genomics.lbl.gov/enigma-data/a/b"),
            "enigma-data-repository/a/b",
        )

    def test_normalize_tsv_rewrites_all_cells_atomically(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "brick.tsv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle, delimiter="\t")
                writer.writerow(["link_a", "link_b", "comment"])
                writer.writerow([
                    "/auto/sahara/namib/home/gtl/enigma-data-repository/reads/",
                    "https://genomics.lbl.gov/enigma-data/genomes/",
                    "unchanged",
                ])

            result = normalize_repository_links_in_tsv(path)

            self.assertEqual(result["cells_changed"], 2)
            self.assertEqual(result["replacements"], 2)
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.reader(handle, delimiter="\t"))
            self.assertEqual(
                rows[1],
                [
                    "enigma-data-repository/reads/",
                    "enigma-data-repository/genomes/",
                    "unchanged",
                ],
            )
            self.assertFalse(path.with_name(".brick.tsv.normalizing").exists())

    def test_untouched_tsv_is_not_rewritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "brick.tsv"
            original = b"name\tvalue\r\nrow\tunchanged\r\n"
            path.write_bytes(original)

            result = normalize_repository_links_in_tsv(path)

            self.assertEqual(result, {"rows": 0, "cells_changed": 0, "replacements": 0})
            self.assertEqual(path.read_bytes(), original)

    def test_prefix_detection_handles_chunk_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "brick.tsv"
            prefix = TEXT_REWRITES[1][0].encode("utf-8")
            path.write_bytes(b"x" * (1024 * 1024 - len(prefix) // 2) + prefix)

            self.assertTrue(_contains_legacy_prefix(path))

    def test_full_brick_conversion_normalizes_generated_tsv(self):
        spec = importlib.util.spec_from_file_location(
            "prepare_brick_tables", SCRIPTS / "prepare_brick_tables.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        class Converter:
            @staticmethod
            def convert(raw_path, stage_data, term_map, parent_map, type_map, brick_id):
                stage = Path(stage_data)
                stage.write_text(
                    "link_context_genome\n"
                    "/auto/sahara/namib/home/gtl/enigma-data-repository/genome/\n",
                    encoding="utf-8",
                )
                stage.with_name(f"{brick_id}_schema.py").write_text("schema = []\n")
                stage.with_name(f"{brick_id}_ddt_ndarray.tsv").write_text("id\nvalue\n")
                stage.with_name(f"{brick_id}_sys_ddt_typedef.tsv").write_text("id\nvalue\n")

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            raw_path = run_dir / "Brick0001618.csv"
            raw_path.write_text("raw\n", encoding="utf-8")

            result = module._convert_one(raw_path, run_dir, Converter(), {}, {}, {})

            self.assertEqual(result["status"], "converted")
            self.assertEqual(
                result["repository_path_normalization"]["cells_changed"], 1
            )
            output = run_dir / "berdl_upload" / "data" / "Brick0001618.tsv"
            self.assertIn("enigma-data-repository/genome/", output.read_text())
            self.assertNotIn("/auto/sahara/", output.read_text())

    def test_reused_brick_artifact_is_normalized(self):
        spec = importlib.util.spec_from_file_location(
            "prepare_brick_tables_reuse", SCRIPTS / "prepare_brick_tables.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            previous = root / "previous"
            current = root / "current"
            brick_id = "Brick0001618"
            artifacts = module._artifacts(previous, brick_id)
            for path in artifacts.values():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("value\n", encoding="utf-8")
            artifacts["data"].write_text(
                "link_context_genome\n"
                "/auto/sahara/namib/home/gtl/enigma-data-repository/genome/\n",
                encoding="utf-8",
            )

            result = module._reuse_artifacts(previous, current, brick_id)

            self.assertEqual(result["cells_changed"], 1)
            output = module._artifacts(current, brick_id)["data"].read_text()
            self.assertIn("enigma-data-repository/genome/", output)
            self.assertNotIn("/auto/sahara/", output)


if __name__ == "__main__":
    unittest.main()
