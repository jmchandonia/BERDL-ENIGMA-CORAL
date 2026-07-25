import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "sync-coral-to-berdl"
    / "scripts"
)
sys.path.insert(0, str(SCRIPTS))

from generate_schema_markdown import export_database_schema


class GenerateSchemaMarkdownTests(unittest.TestCase):
    def test_uses_manifest_count_without_scanning_past_sample(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = root / "table.tsv"
            data.write_text("id\n1\n2\nmalformed\trow\n", encoding="utf-8")
            output = root / "schema.md"
            config = {
                "tables": [{
                    "name": "example",
                    "enabled": True,
                    "local_path": str(data),
                    "schema": [{
                        "column": "id",
                        "type": "STRING",
                        "nullable": False,
                        "comment": json.dumps({"description": "Identifier"}),
                    }],
                }],
            }

            export_database_schema(
                config,
                output,
                sample_rows=1,
                row_counts={"example": 123},
            )

            rendered = output.read_text(encoding="utf-8")
            self.assertIn("**Total Rows:** 123", rendered)
            self.assertIn("| 1 |", rendered)
            self.assertNotIn("| 2 |", rendered)
            self.assertNotIn("malformed", rendered)


if __name__ == "__main__":
    unittest.main()
