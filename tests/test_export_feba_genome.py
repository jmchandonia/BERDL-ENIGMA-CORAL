import importlib.util
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "tools" / "export_feba_genome.py"
sys.path.insert(0, str(REPO_ROOT / "tools"))
SPEC = importlib.util.spec_from_file_location("export_feba_genome", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ExportFebaGenomeTests(unittest.TestCase):
    def make_database(self, path: Path) -> None:
        connection = sqlite3.connect(path)
        connection.executescript(
            """
            CREATE TABLE Organism(
                orgId TEXT PRIMARY KEY, genus TEXT, species TEXT, strain TEXT
            );
            CREATE TABLE ScaffoldSeq(
                orgId TEXT, scaffoldId TEXT, sequence TEXT,
                PRIMARY KEY(orgId, scaffoldId)
            );
            CREATE TABLE Gene(
                orgId TEXT, locusId TEXT, sysName TEXT, scaffoldId TEXT,
                begin INTEGER, end INTEGER, type INTEGER, strand TEXT,
                gene TEXT, desc TEXT, GC REAL,
                PRIMARY KEY(orgId, locusId)
            );
            CREATE TABLE LocusXref(
                orgId TEXT, locusId TEXT, xrefDb TEXT, xrefId TEXT
            );
            """
        )
        connection.execute("INSERT INTO Organism VALUES ('org1','Genus','species','strain')")
        connection.execute("INSERT INTO ScaffoldSeq VALUES ('org1','contig1','atgcaa')")
        connection.execute(
            "INSERT INTO Gene VALUES "
            "('org1','locus1','sys1','contig1',1,6,1,'+','abc','protein',0.5)"
        )
        connection.execute(
            "INSERT INTO LocusXref VALUES ('org1','locus1','uniprot','P12345')"
        )
        connection.commit()
        connection.close()

    def test_repository_mode_uses_required_names_and_validates_round_trip(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            database = root / "feba.db"
            output = root / "Strain-A.3"
            self.make_database(database)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(database),
                    "org1",
                    str(output),
                    "--strain-name",
                    "Strain-A",
                    "--genome-version",
                    "3",
                    "--source-database-sha256",
                    "a" * 64,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn('"status": "passed"', result.stdout)
            self.assertTrue((output / "Strain-A_contigs.fasta").is_file())
            self.assertTrue((output / "Strain-A_Prodigal.gff").is_file())
            self.assertTrue((output / "Strain-A.3_export_manifest.json").is_file())
            self.assertNotIn(str(database), (output / "Strain-A_Prodigal.gff").read_text())

    def test_fasta_parser_rejects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.fasta"
            path.write_text(">a\nAC\n>a\nGT\n")
            with self.assertRaisesRegex(ValueError, "duplicate FASTA ID"):
                MODULE.read_fasta(path)


if __name__ == "__main__":
    unittest.main()
