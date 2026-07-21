import importlib.util
import json
import sys
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "check-berdl-foreign-keys"
    / "scripts"
    / "check_foreign_keys.py"
)
SPEC = importlib.util.spec_from_file_location("check_foreign_keys", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def config_with_fk(reference="sdt_community.sdt_community_name"):
    return {
        "tables": [{
            "name": "ddt_brick0000013",
            "enabled": True,
            "schema": [{
                "column": "sdt_sample_name",
                "type": "STRING",
                "comment": json.dumps({
                    "description": "sample ID",
                    "type": "foreign_key",
                    "references": reference,
                }),
            }],
        }],
    }


class CheckForeignKeysTests(unittest.TestCase):
    def test_extracts_selected_relationship(self):
        relationships, errors = MODULE.extract_foreign_keys(
            config_with_fk(), {"ddt_brick0000013"}
        )
        self.assertEqual(errors, [])
        self.assertEqual(len(relationships), 1)
        self.assertEqual(relationships[0].source_column, "sdt_sample_name")
        self.assertEqual(relationships[0].target_table, "sdt_community")

    def test_ignores_unselected_table(self):
        relationships, errors = MODULE.extract_foreign_keys(
            config_with_fk(), {"ddt_brick0000012"}
        )
        self.assertEqual(relationships, [])
        self.assertEqual(
            errors, ["Selected table is absent from config: ddt_brick0000012"]
        )

    def test_rejects_malformed_reference(self):
        relationships, errors = MODULE.extract_foreign_keys(
            config_with_fk("sdt_community"), None
        )
        self.assertEqual(relationships, [])
        self.assertIn("must reference table.column", errors[0])

    def test_builds_anti_orphan_metrics_query(self):
        relation = MODULE.extract_foreign_keys(config_with_fk(), None)[0][0]
        sql = MODULE.build_metrics_sql("enigma_coral", relation)
        self.assertIn("`enigma_coral`.`ddt_brick0000013`", sql)
        self.assertIn("`enigma_coral`.`sdt_community`", sql)
        self.assertIn("COUNT(DISTINCT s.fk_value)", sql)
        self.assertIn("LEFT JOIN target_values", sql)

    def test_duplicate_check_targets_declared_column(self):
        relation = MODULE.extract_foreign_keys(config_with_fk(), None)[0][0]
        sql = MODULE.build_duplicate_sql("enigma_coral", relation)
        self.assertIn("GROUP BY `sdt_community_name`", sql)
        self.assertIn("HAVING COUNT(*) > 1", sql)

    def test_bracketed_reference_explodes_json_string_array(self):
        config = config_with_fk("[sdt_community.sdt_community_name]")
        relation = MODULE.extract_foreign_keys(config, None)[0][0]
        self.assertTrue(relation.source_is_collection)
        sql = MODULE.build_metrics_sql("enigma_coral", relation, "string")
        self.assertIn("EXPLODE(COALESCE", sql)
        self.assertIn("array<array<string>>", sql)

    def test_array_source_explodes_native_array(self):
        config = config_with_fk()
        config["tables"][0]["schema"][0]["type"] = "ARRAY<STRING>"
        relation = MODULE.extract_foreign_keys(config, None)[0][0]
        sql = MODULE.build_metrics_sql("enigma_coral", relation, "array<string>")
        self.assertIn("EXPLODE(`sdt_sample_name`)", sql)
        self.assertNotIn("FROM_JSON", sql)

    def test_nested_native_array_is_flattened(self):
        config = config_with_fk()
        config["tables"][0]["schema"][0]["type"] = "ARRAY<ARRAY<STRING>>"
        relation = MODULE.extract_foreign_keys(config, None)[0][0]
        sql = MODULE.build_metrics_sql(
            "enigma_coral", relation, "array<array<string>>"
        )
        self.assertIn("EXPLODE(FLATTEN(`sdt_sample_name`))", sql)

    def test_batched_metrics_scan_scalar_source_table_once(self):
        config = config_with_fk()
        config["tables"][0]["schema"].append({
            "column": "sdt_asv_name",
            "type": "STRING",
            "comment": json.dumps({
                "type": "foreign_key",
                "references": "sdt_asv.sdt_asv_name",
            }),
        })
        relations = MODULE.extract_foreign_keys(config, None)[0]
        types = {MODULE._relation_key(relation): "string" for relation in relations}
        sql = MODULE.build_batched_metrics_sql("enigma_coral", relations, types)
        self.assertEqual(sql.count("`enigma_coral`.`ddt_brick0000013`"), 1)
        self.assertIn("LATERAL VIEW STACK(2", sql)

    def test_batched_duplicate_query_groups_target_values(self):
        relations = MODULE.extract_foreign_keys(config_with_fk(), None)[0]
        sql = MODULE.build_batched_duplicate_sql("enigma_coral", relations)
        self.assertIn("GROUP BY target_key, target_value", sql)
        self.assertIn("duplicate_target_rows", sql)

    def test_duplicate_samples_are_bounded_per_target(self):
        relations = MODULE.extract_foreign_keys(config_with_fk(), None)[0]
        sql = MODULE.build_batched_duplicate_sample_sql(
            "enigma_coral", relations, 7
        )
        self.assertIn("PARTITION BY target_key", sql)
        self.assertIn("WHERE sample_rank <= 7", sql)


if __name__ == "__main__":
    unittest.main()
