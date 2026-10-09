#!/usr/bin/env python3
"""End-to-end local CLI validation using a fictional account and temporary data."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="instaguard-smoke-") as directory:
        folder = Path(directory)
        database = str(folder / "cases.db")

        def run(script, *args):
            result = subprocess.run([sys.executable, str(root / script), *args],
                                    cwd=root, capture_output=True, text=True, check=True)
            return result.stdout

        run("instaguard.py", "--db", database, "add", "fictional_example",
            "--category", "other", "--reason", "Synthetic software test only")
        run("instaguard.py", "--db", database, "evidence", "1",
            "--url", "https://example.org/fictional-evidence",
            "--description", "Synthetic fixture", "--file", str(root / "tests/fixtures/fictional.txt"),
            "--observed-at", "2020-01-01T00:00:00Z", "--collector", "software-test")
        run("report.py", "1", "--db", database, "--format", "json", "--output", str(folder / "case.json"))
        run("report.py", "1", "--db", database, "--output", str(folder / "case.md"))
        report = json.loads((folder / "case.json").read_text(encoding="utf-8"))
        audit = json.loads(run("security_audit.py", "--db", database, "--format", "json"))
        if report["confirmed_facts"][0]["status"] != "verified_bytes" or audit["result"] != "pass":
            raise AssertionError("Evidence integrity or audit failed")
        if "Fatos confirmados" not in (folder / "case.md").read_text(encoding="utf-8"):
            raise AssertionError("Markdown report missing verification section")
        print(json.dumps({"scenario": "fictional_local_evidence", "passed": True,
                          "json_report": "validated", "markdown_report": "validated",
                          "sha256": report["confirmed_facts"][0]["sha256"],
                          "audit": audit["result"], "real_reports_sent": 0}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
