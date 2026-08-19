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

    def test_known_brick_value_correction_is_exact_and_column_scoped(self):
        spec = importlib.util.spec_from_file_location(
            "prepare_brick_tables_values", SCRIPTS / "prepare_brick_tables.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        bad = (
            "anaerobic = 0; media name = LB, concentration = 25.0 "
            "(fold dilution); media name = Sediment Extract; "
            "temperature = 30.0 (degree Celsius)"
        )
        good = "A" + bad[1:]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Brick0000510.tsv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle, delimiter="\t")
                writer.writerow(["sdt_condition_name", "description"])
                writer.writerow([bad, bad])
                writer.writerow([good, "unchanged"])

            result = module.normalize_known_coral_values_in_tsv(
                path, "Brick0000510"
            )

            self.assertEqual(result["cells_changed"], 1)
            self.assertEqual(result["by_column"], {"sdt_condition_name": 1})
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.reader(handle, delimiter="\t"))
            self.assertEqual(rows[1], [good, bad])
            self.assertEqual(rows[2], [good, "unchanged"])

    def test_known_value_correction_ignores_other_bricks(self):
        spec = importlib.util.spec_from_file_location(
            "prepare_brick_tables_other", SCRIPTS / "prepare_brick_tables.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Brick0000511.tsv"
            original = b"sdt_condition_name\nanaerobic = 0\n"
            path.write_bytes(original)

            result = module.normalize_known_coral_values_in_tsv(
                path, "Brick0000511"
            )

            self.assertEqual(result["cells_changed"], 0)
            self.assertEqual(path.read_bytes(), original)

    def test_prepare_brick_tables_corrects_tnseq_library_reference(self):
        spec = importlib.util.spec_from_file_location(
            "prepare_brick_tables_references", SCRIPTS / "prepare_brick_tables.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            schema = root / "Brick_schema.py"
            typedef = root / "Brick_sys_ddt_typedef.tsv"
            old_reference = "sdt_tnseq.sdt_tnseq_library_name"
            new_reference = "sdt_tnseq_library.sdt_tnseq_library_name"
            schema.write_text(f'comment="{old_reference}"\n', encoding="utf-8")
            typedef.write_text(
                f"column\tobject_ref\nname\t{old_reference}\n", encoding="utf-8"
            )

            result = module.normalize_known_coral_references(
                {"schema": schema, "sys_ddt_typedef": typedef}
            )

            self.assertEqual(result["replacements"], 2)
            self.assertEqual(result["files_changed"], ["schema", "sys_ddt_typedef"])
            self.assertIn(new_reference, schema.read_text(encoding="utf-8"))
            self.assertIn(new_reference, typedef.read_text(encoding="utf-8"))
            self.assertNotIn(old_reference, schema.read_text(encoding="utf-8"))
            self.assertNotIn(old_reference, typedef.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
