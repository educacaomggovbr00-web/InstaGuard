"""Regression tests for the offline security audit and local export safeguards."""
import contextlib
import io
import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
import unittest

import instaguard
from security_audit import audit_database, main as audit_main


class SecurityAuditTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.db_path = Path(self.folder.name) / "cases.db"

    def prepare_db(self):
        db = instaguard.connect(self.db_path)
        db.close()

    def test_valid_database_audit(self):
        self.prepare_db()
        result = audit_database(self.db_path)
        self.assertEqual(result["result"], "pass")
        self.assertEqual(result["external_requests"], 0)
        self.assertFalse(result["records_or_private_data_included"])
        statuses = {item["check"]: item["status"] for item in result["findings"]}
        self.assertEqual(statuses["sqlite_integrity"], "pass")
        self.assertEqual(statuses["foreign_keys"], "pass")
        self.assertEqual(statuses["schema"], "pass")

    def test_missing_database_does_not_create_file(self):
        result = audit_database(self.db_path)
        self.assertEqual(result["result"], "fail")
        self.assertFalse(self.db_path.exists())

    def test_invalid_database_is_reported(self):
        self.db_path.write_bytes(b"not sqlite")
        result = audit_database(self.db_path)
        self.assertEqual(result["result"], "fail")
        self.assertIn("sqlite_read", [x["check"] for x in result["findings"]])

    def test_invalid_schema_is_reported(self):
        with sqlite3.connect(self.db_path) as db:
            db.execute("CREATE TABLE unrelated (id INTEGER)")
        result = audit_database(self.db_path)
        checks = {x["check"]: x["status"] for x in result["findings"]}
        self.assertEqual(checks["schema"], "fail")

    @unittest.skipUnless(os.name == "posix", "Requires Unix permissions")
    def test_insecure_permissions_are_reported(self):
        self.prepare_db()
        self.db_path.chmod(0o644)
        result = audit_database(self.db_path)
        self.assertEqual(result["result"], "fail")
        checks = {x["check"]: x["status"] for x in result["findings"]}
        self.assertEqual(checks["file_permissions"], "fail")

    @unittest.skipUnless(os.name == "posix", "Requires Unix permissions")
    def test_existing_custom_parent_directory_not_chmodded(self):
        parent = Path(self.folder.name)
        parent.chmod(0o755)
        self.prepare_db()
        self.assertEqual(stat.S_IMODE(parent.stat().st_mode), 0o755)

    @unittest.skipUnless(os.name == "posix", "Requires symlinks")
    def test_database_symlink_refused(self):
        self.prepare_db()
        link = Path(self.folder.name) / "database-link.db"
        link.symlink_to(self.db_path)
        result = audit_database(link)
        self.assertEqual(result["result"], "fail")
        self.assertEqual(result["findings"][0]["check"], "database_path")

    def test_json_audit_does_not_disclose_case_data(self):
        self.prepare_db()
        with contextlib.redirect_stdout(io.StringIO()):
            code = instaguard.main([
                "--db", str(self.db_path), "add", "testexample",
                "--category", "other", "--reason", "UNIQUE_SECRET_SENTINEL",
            ])
        self.assertEqual(code, 0)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = audit_main(["--db", str(self.db_path), "--format", "json"])
        self.assertEqual(code, 0)
        payload = output.getvalue()
        self.assertNotIn("UNIQUE_SECRET_SENTINEL", payload)
        self.assertNotIn("testexample", payload)
        self.assertEqual(json.loads(payload)["scope"], "local_sqlite_only")

    def test_export_rejects_existing_output_and_preserves_content(self):
        self.prepare_db()
        output = Path(self.folder.name) / "existing.json"
        output.write_text("NEVER OVERWRITE", encoding="utf-8")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = instaguard.main([
                "--db", str(self.db_path), "export", "--output", str(output),
            ])
        self.assertEqual(code, 1)
        self.assertEqual(output.read_text(encoding="utf-8"), "NEVER OVERWRITE")

    @unittest.skipUnless(os.name == "posix", "Requires Unix permissions")
    def test_new_export_private_from_creation(self):
        self.prepare_db()
        output = Path(self.folder.name) / "new-export.json"
        with contextlib.redirect_stdout(io.StringIO()):
            code = instaguard.main([
                "--db", str(self.db_path), "export", "--output", str(output),
            ])
        self.assertEqual(code, 0)
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
