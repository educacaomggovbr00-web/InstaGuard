"""Testa a geração de relatórios locais sem requisições à internet."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest

import instaguard
import report


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.db = str(Path(self.folder.name) / "cases.db")
        with contextlib.redirect_stdout(io.StringIO()):
            code = instaguard.main([
                "--db", self.db, "add", "@conta.exemplo",
                "--category", "other",
                "--reason", "Observação preliminar, sem acusação confirmada",
            ])
            self.assertEqual(code, 0)

    def run_report(self, *args):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = report.main(["1", "--db", self.db, *args])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_report_does_not_infer_identity(self):
        code, output, error = self.run_report(
            "--display-name", "Nome público declarado",
            "--bio", "Envie pix para participar",
            "--source", "https://www.instagram.com/conta.exemplo/",
        )
        self.assertEqual((code, error), (0, ""))
        self.assertIn("identidade de quem criou ou administra o perfil: não determinada", output.lower())
        self.assertIn("pedido de dinheiro", output)
        self.assertIn("Inconclusivo", output)
        self.assertIn("Nome público declarado", output)
        self.assertIn("informações fornecidas manualmente", output)

    def test_report_includes_registered_evidence(self):
        with contextlib.redirect_stdout(io.StringIO()):
            code = instaguard.main([
                "--db", self.db, "evidence", "1",
                "--url", "https://www.instagram.com/conta.exemplo/",
                "--description", "Link anotado pelo operador",
            ])
        self.assertEqual(code, 0)
        code, output, _ = self.run_report()
        self.assertEqual(code, 0)
        self.assertIn("Link anotado pelo operador", output)

    def test_saving_report_does_not_overwrite(self):
        destination = Path(self.folder.name) / "case.md"
        self.assertEqual(self.run_report("--output", str(destination))[0], 0)
        self.assertIn("# InstaGuard", destination.read_text(encoding="utf-8"))
        self.assertEqual(self.run_report("--output", str(destination))[0], 1)
        self.assertEqual(self.run_report("--output", self.db)[0], 1)

    def test_nonexistent_case_and_invalid_source(self):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = report.main(["9999", "--db", self.db])
        self.assertEqual(code, 1)
        self.assertEqual(self.run_report("--source", "http://site.invalid")[0], 1)

    def test_escape_markdown_from_user_content(self):
        case = {
            "id": 1, "username": "conta.exemplo", "category": "other",
            "status": "new", "reason": "# Manchete inventada", "evidence": [],
        }
        output = report.make_report(case, display_name="**Nome**")
        self.assertIn("\\# Manchete inventada", output)
        self.assertIn("\\*\\*Nome\\*\\*", output)


    def test_machine_readable_report_does_not_claim_private_identity(self):
        import json
        code, output, error = self.run_report(
            "--format", "json",
            "--display-name", "Nome exibido",
            "--source", "https://www.instagram.com/conta.exemplo/",
        )
        self.assertEqual((code, error), (0, ""))
        data = json.loads(output)
        self.assertEqual(data["mode"], "offline_manual_review")
        self.assertEqual(data["conclusion"], "inconclusive")
        self.assertEqual(data["identity_of_profile_creator"]["status"], "unknown")
        self.assertIs(data["public_fields_supplied_manually"]["independently_verified"], False)
        self.assertEqual(data["public_fields_supplied_manually"]["display_name"], "Nome exibido")
        self.assertEqual(data["case"]["username"], "conta.exemplo")

    def test_json_report_saved_without_overwriting(self):
        import json
        destination = Path(self.folder.name) / "case.json"
        self.assertEqual(
            self.run_report("--format", "json", "--output", str(destination))[0], 0
        )
        data = json.loads(destination.read_text(encoding="utf-8"))
        self.assertEqual(data["case"]["id"], 1)
        self.assertEqual(self.run_report("--format", "json", "--output", str(destination))[0], 1)


if __name__ == "__main__":
    unittest.main()
