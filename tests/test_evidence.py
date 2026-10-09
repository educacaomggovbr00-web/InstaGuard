"""Reproducible evidence lifecycle and migration checks using fictional data."""
import hashlib
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
import unittest
from unittest.mock import patch

from evidence import observation_time, register_evidence, verify_evidence
from instaguard import check_url, clean_username, connect, get_case, timestamp
from investigator import assess
from report import make_json_report, make_report
from security_audit import audit_database
from scripts.build_manual_package import main as package_main


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "cases.db"
        self.db = connect(self.path)
        self.addCleanup(self.db.close)
        now = timestamp()
        self.db.execute("INSERT INTO cases(username,category,reason,status,created_at,updated_at) VALUES(?,?,?,'new',?,?)",
                        ("fictional_example", "other", "Operator allegation", now, now))
        self.db.commit()
        self.source = self.root / "supplied.txt"
        self.source.write_bytes(b"Fictional evidence, not a real profile")

    def attach(self, **kwargs):
        return register_evidence(self.db, 1, "https://example.org/evidence", "Supplied test file",
                                 file=self.source, **kwargs)

    def test_preserved_copy_hash_provenance_and_report(self):
        with patch("socket.create_connection", side_effect=AssertionError("No external network")):
            self.attach(observed_at="2020-01-01T03:00:00+03:00", collector="tester")
            case = get_case(self.db, 1)
            item = case["evidence"][0]
            self.assertEqual(item["sha256"], hashlib.sha256(self.source.read_bytes()).hexdigest())
            self.assertEqual(item["observed_at"], "2020-01-01T00:00:00+00:00")
            self.assertEqual(item["collector"], "tester")
            self.assertEqual(item["method"], "operator_supplied_file")
            self.source.unlink()
            report = make_json_report(case)
        self.assertEqual(report["confirmed_facts"][0]["status"], "verified_bytes")
        self.assertEqual(report["confirmed_facts"][0]["content_authenticity"], "not_established")
        self.assertEqual(report["conclusion"], "inconclusive")
        self.assertTrue(report["unverified_information"])
        self.assertEqual(report["timeline"][0]["event"], "observation_claimed_by_operator")
        for heading in ("Fatos confirmados", "Informações não verificadas", "Resultados inconclusivos"):
            self.assertIn(heading, make_report(case))
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(Path(item["artifact_path"]).stat().st_mode), 0o600)

    def test_tampering_and_missing_copy_are_detected(self):
        self.attach()
        case = get_case(self.db, 1)
        artifact = Path(case["evidence"][0]["artifact_path"])
        artifact.write_bytes(b"Tampered")
        self.assertEqual(make_json_report(case)["integrity_checks"][0]["status"], "mismatch")
        self.assertEqual(audit_database(self.path)["result"], "fail")
        artifact.unlink()
        self.assertEqual(verify_evidence(case["evidence"][0])["status"], "unavailable")

    def test_url_only_is_never_confirmed(self):
        register_evidence(self.db, 1, "https://example.org", "Manual reference")
        report = make_json_report(get_case(self.db, 1))
        self.assertEqual(report["confirmed_facts"], [])
        self.assertEqual(report["integrity_checks"][0]["status"], "unverified")

    def test_invalid_time_rejected_before_artifact_creation(self):
        for value in ("2020-01-01T00:00:00", "not-a-date", "2999-01-01T00:00:00Z"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.attach(observed_at=value)
        self.assertEqual(get_case(self.db, 1)["evidence"], [])
        self.assertFalse((self.root / "evidence-files").exists())

    def test_oversize_copy_is_cleaned_up(self):
        with patch("evidence.MAX_BYTES", 2), self.assertRaises(ValueError):
            self.attach()
        self.assertEqual(list((self.root / "evidence-files").iterdir()), [])
        self.assertEqual(get_case(self.db, 1)["evidence"], [])

    def test_failed_database_write_cleans_copy(self):
        self.db.execute("CREATE TRIGGER reject_evidence BEFORE INSERT ON evidence BEGIN SELECT RAISE(ABORT,'test'); END")
        self.db.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.attach()
        self.assertEqual(list((self.root / "evidence-files").iterdir()), [])

    @unittest.skipUnless(os.name == "posix", "POSIX symlink test")
    def test_symlink_source_and_database_refused(self):
        link = self.root / "link"
        link.symlink_to(self.source)
        with self.assertRaises(ValueError):
            register_evidence(self.db, 1, "https://example.org", "Test", file=link)
        link.unlink()
        link.symlink_to(self.path)
        with self.assertRaises(ValueError):
            connect(link)

    def test_bad_url_and_reserved_route(self):
        for value in ("https://example.org/a\nInjected", "https://example.org:bad/", "https://example.org:65536/", "https://a:b@example.org", "https://example.org\\evil"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                check_url(value)
        with self.assertRaises(ValueError):
            clean_username("https://www.instagram.com/p/")

    def test_source_consistency_does_not_certify_content(self):
        for source, status in (("", "missing_source"),
                               ("https://www.instagram.com/Fictional_example/", "matching_profile"),
                               ("https://www.instagram.com/another_example/", "profile_mismatch"),
                               ("https://www.instagram.com/p/abc/", "not_a_profile_url"),
                               ("https://example.org", "external_source_unverified")):
            with self.subTest(source=source):
                info = assess("fictional_example", source_url=source)
                self.assertEqual(info["provenance"]["source_consistency"], status)
                self.assertFalse(info["provenance"]["independently_verified"])

    def test_markdown_cannot_embed_raw_html(self):
        case = get_case(self.db, 1)
        case["reason"] = '<img src="https://example.org/tracker">'
        output = make_report(case)
        self.assertNotIn("<img", output)
        self.assertIn("&lt;img", output)

    def test_audit_rejects_same_table_names_with_wrong_columns(self):
        path = self.root / "wrong.db"
        with sqlite3.connect(path) as db:
            db.execute("CREATE TABLE cases (unrelated TEXT)")
            db.execute("CREATE TABLE evidence (unrelated TEXT)")
        findings = {x["check"]: x["status"] for x in audit_database(path)["findings"]}
        self.assertEqual(findings["schema"], "fail")

    def test_audit_detects_invalid_case_values_and_url_without_disclosure(self):
        self.db.execute("UPDATE cases SET status='INVALID_SECRET_SENTINEL' WHERE id=1")
        self.db.execute("INSERT INTO evidence(case_id,url,description,created_at) VALUES(1,'javascript:secret','test',?)", (timestamp(),))
        self.db.commit()
        result = audit_database(self.path)
        checks = {item["check"]: item["status"] for item in result["findings"]}
        self.assertEqual(checks["case_values"], "fail")
        self.assertEqual(checks["evidence_urls"], "fail")
        self.assertNotIn("SECRET_SENTINEL", str(result))

    def test_package_permissions_and_repeat_preserves_original(self):
        destination = self.root / "package"
        args = ["--profile-url", "https://www.instagram.com/fictional_example/", "--category", "other",
                "--reason", "Fictional test", "--output-dir", str(destination)]
        self.assertEqual(package_main(args), 0)
        original = (destination / "revisao-manual.txt").read_bytes()
        self.assertEqual(package_main(args), 1)
        self.assertEqual((destination / "revisao-manual.txt").read_bytes(), original)
        if os.name == "posix":
            for file in destination.iterdir():
                self.assertEqual(stat.S_IMODE(file.stat().st_mode), 0o600)


class LegacyMigrationTests(unittest.TestCase):
    def test_legacy_case_and_evidence_survive_repeated_migration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.db"
            with sqlite3.connect(path) as db:
                db.execute("CREATE TABLE cases(id INTEGER PRIMARY KEY,username TEXT,category TEXT,reason TEXT,status TEXT,created_at TEXT,updated_at TEXT)")
                db.execute("CREATE TABLE evidence(id INTEGER PRIMARY KEY,case_id INTEGER REFERENCES cases(id),url TEXT,description TEXT,created_at TEXT)")
                db.execute("INSERT INTO cases VALUES(1,'fictional_example','other','Legacy note','new','2020-01-01','2020-01-01')")
                db.execute("INSERT INTO evidence VALUES(1,1,'https://example.org','Legacy evidence','2020-01-01')")
            for _ in range(2):
                db = connect(path)
                try:
                    case = get_case(db, 1)
                    self.assertEqual(case["reason"], "Legacy note")
                    self.assertEqual(len(case["evidence"]), 1)
                    self.assertIsNone(case["evidence"][0]["sha256"])
                    self.assertEqual(make_json_report(case)["confirmed_facts"], [])
                finally:
                    db.close()
