import csv
import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "build_feba_phase0_manifest.py"
SPEC = importlib.util.spec_from_file_location("build_feba_phase0_manifest", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Phase0ManifestTests(unittest.TestCase):
    def make_database(self, path: Path) -> sqlite3.Connection:
        connection = sqlite3.connect(path)
        connection.executescript(
            """
            CREATE TABLE Organism(orgId TEXT PRIMARY KEY, genus TEXT, species TEXT, strain TEXT);
            CREATE TABLE ScaffoldSeq(orgId TEXT, scaffoldId TEXT, sequence TEXT);
            CREATE TABLE Gene(
                orgId TEXT, locusId TEXT, sysName TEXT, scaffoldId TEXT,
                begin INTEGER, end INTEGER, type INTEGER, strand TEXT,
                gene TEXT, desc TEXT, GC REAL
            );
            CREATE TABLE LocusXref(orgId TEXT, locusId TEXT, xrefDb TEXT, xrefId TEXT);
            CREATE TABLE Experiment(orgId TEXT, expName TEXT, mutantLibrary TEXT);
            CREATE TABLE GeneFitness(orgId TEXT, locusId TEXT, expName TEXT, fit REAL, t REAL);
            """
        )
        return connection

    def test_collect_source_row_counts_and_libraries(self):
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "feba.db"
            connection = self.make_database(database)
            connection.execute("INSERT INTO Organism VALUES ('org1','Genus','species','strain')")
            connection.executemany(
                "INSERT INTO ScaffoldSeq VALUES (?,?,?)",
                [("org1", "s1", "ACGT"), ("org1", "s2", "AAA")],
            )
            connection.executemany(
                "INSERT INTO Gene VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                [
                    ("org1", "g1", "g1", "s1", 1, 3, 1, "+", "a", "A", 0.5),
                    ("org1", "g2", "g2", "s2", 1, 3, 1, "-", "b", "B", 0.3),
                ],
            )
            connection.execute("INSERT INTO LocusXref VALUES ('org1','g1','RefSeq','x1')")
            connection.executemany(
                "INSERT INTO Experiment VALUES (?,?,?)",
                [("org1", "e1", "libB"), ("org1", "e2", "libA")],
            )
            connection.executemany(
                "INSERT INTO GeneFitness VALUES (?,?,?,?,?)",
                [("org1", "g1", "e1", 0.1, 1.0), ("org1", "g2", "e2", 0.2, 2.0)],
            )
            connection.commit()
            connection.row_factory = sqlite3.Row

            row, libraries = MODULE.collect_source_row(
                connection,
                {
                    "fitprivate_orgId": "org1",
                    "fitprivate_organism": "Genus species strain",
                    "experiment_count": "2",
                    "sdt_strain_id": "Strain1",
                    "sdt_strain_name": "strain",
                    "match_basis": "exact",
                },
            )

            self.assertEqual(row["scaffold_count"], 2)
            self.assertEqual(row["total_bases"], 7)
            self.assertEqual(row["gene_count"], 2)
            self.assertEqual(row["xref_count"], 1)
            self.assertEqual(row["gene_fitness_count"], 2)
            self.assertEqual(libraries, [("libA", 1), ("libB", 1)])
            self.assertEqual(len(row["source_assembly_sha256"]), 64)
            self.assertEqual(len(row["source_annotation_structure_sha256"]), 64)
            self.assertEqual(len(row["source_annotation_metadata_sha256"]), 64)

    def test_source_fingerprint_is_case_insensitive_for_sequence(self):
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first.db"
            second = Path(temporary) / "second.db"
            fingerprints = []
            for path, sequence in ((first, "acgt"), (second, "ACGT")):
                connection = self.make_database(path)
                connection.execute("INSERT INTO ScaffoldSeq VALUES ('org1','s1',?)", (sequence,))
                connection.commit()
                connection.row_factory = sqlite3.Row
                fingerprints.append(MODULE.source_fingerprints(connection, "org1"))
                connection.close()
            self.assertEqual(fingerprints[0], fingerprints[1])

    def test_write_tsv_atomic_replaces_complete_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.tsv"
            MODULE.write_tsv_atomic(path, ["id", "value"], [{"id": "a", "value": "b"}])
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))
            self.assertEqual(rows, [{"id": "a", "value": "b"}])
            self.assertFalse(path.with_name(".manifest.tsv.tmp").exists())

    def test_validate_crosswalk_rejects_duplicate_strains(self):
        rows = []
        for index in range(MODULE.EXPECTED_REVIEWED_ORGANISMS):
            rows.append(
                {
                    "fitprivate_orgId": f"org{index}",
                    "sdt_strain_id": "duplicate" if index < 2 else f"strain{index}",
                    "sdt_strain_name": f"name{index}",
                }
            )
        with self.assertRaisesRegex(ValueError, "duplicate sdt_strain_id"):
            MODULE.validate_crosswalk(rows)

    def test_select_scope_requires_complete_reviewed_universe(self):
        crosswalk = [
            {"fitprivate_orgId": "include_me"},
            {"fitprivate_orgId": "exclude_me"},
        ]
        scope = [
            {
                "fitprivate_orgId": "include_me",
                "include": "yes",
                "scope_class": "enigma_isolate",
                "decision_reason": "selected",
            },
            {
                "fitprivate_orgId": "exclude_me",
                "include": "no",
                "scope_class": "reference_strain",
                "decision_reason": "not an ENIGMA isolate",
            },
        ]
        selected, excluded = MODULE.select_scope(crosswalk, scope)
        self.assertEqual([row["fitprivate_orgId"] for row in selected], ["include_me"])
        self.assertEqual([row["fitprivate_orgId"] for row in excluded], ["exclude_me"])

        with self.assertRaisesRegex(ValueError, "cover exactly"):
            MODULE.select_scope(crosswalk, scope[:1])


if __name__ == "__main__":
    unittest.main()
