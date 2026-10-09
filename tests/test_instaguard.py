"""Regression tests for the offline InstaGuard CLI."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import instaguard


class InstaGuardTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.db = str(Path(self.folder.name) / "cases.db")

    def run_cli(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = instaguard.main(["--db", self.db, *args])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_case_lifecycle_and_export(self):
        code, output, error = self.run_cli(
            "add", "@sample.account", "--category", "impersonation",
            "--reason", "Claims to be another person",
        )
        self.assertEqual((code, error), (0, ""))
        self.assertIn("case #1", output)

        code, _, error = self.run_cli(
            "evidence", "1", "--url", "https://www.instagram.com/sample.account/",
            "--description", "Profile URL supplied for human review",
        )
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(self.run_cli("status", "1", "reviewing")[0], 0)

        code, detail, _ = self.run_cli("show", "1")
        self.assertEqual(code, 0)
        case = json.loads(detail)
        self.assertEqual(case["username"], "sample.account")
        self.assertEqual(case["status"], "reviewing")
        self.assertEqual(len(case["evidence"]), 1)

        export = Path(self.folder.name) / "export.json"
        self.assertEqual(
            self.run_cli("export", "--output", str(export))[0], 0
        )
        data = json.loads(export.read_text(encoding="utf-8"))
        self.assertEqual(len(data["cases"]), 1)
        self.assertEqual(data["cases"][0]["category"], "impersonation")

    def test_invalid_usernames_and_urls(self):
        self.assertEqual(
            self.run_cli(
                "add", "name with spaces", "--category", "other",
                "--reason", "test",
            )[0], 1
        )
        self.assertEqual(
            self.run_cli(
                "add", "@safe.name", "--category", "spam", "--reason", "test",
            )[0], 0
        )
        self.assertEqual(
            self.run_cli(
                "evidence", "1", "--url", "http://example.com",
                "--description", "Non-HTTPS link",
            )[0], 1
        )
        self.assertEqual(self.run_cli("show", "900")[0], 1)

    def test_list_and_stats(self):
        self.assertEqual(
            self.run_cli(
                "add", "a.b", "--category", "scam",
                "--reason", "Possible fraudulent offer",
            )[0], 0
        )
        self.assertEqual(self.run_cli("status", "1", "closed")[0], 0)
        self.assertIn("@a.b", self.run_cli("list", "--status", "closed")[1])
        self.assertIn("closed: 1", self.run_cli("stats")[1])


if __name__ == "__main__":
    unittest.main()
