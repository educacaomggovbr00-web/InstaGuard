"""Testa a preparação de um único relato factual, sem requisições externas."""
import unittest

from submission import OFFICIAL_HELP_URL, prepare_statement


class PreparationTests(unittest.TestCase):
    def test_evidence_based_draft(self):
        case = {
            "username": "conta_exemplo",
            "category": "other",
            "reason": "A publicação X contém a informação Y, observada em 2026.",
            "evidence": [
                {"url": "https://example.org/prova", "description": "Registro público fornecido manualmente"}
            ],
        }
        statement = prepare_statement(case)
        self.assertIn("https://www.instagram.com/conta_exemplo/", statement)
        self.assertIn("A publicação X contém", statement)
        self.assertIn("https://example.org/prova", statement)
        self.assertIn("não enviou nenhuma denúncia", statement)
        self.assertIn("sem confirmação", statement)

    def test_empty_reason_is_rejected(self):
        case = {"username": "exemplo", "category": "other", "reason": "  ", "evidence": []}
        with self.assertRaises(ValueError):
            prepare_statement(case)

    def test_official_help_is_https(self):
        self.assertTrue(OFFICIAL_HELP_URL.startswith("https://help.instagram.com/"))


if __name__ == "__main__":
    unittest.main()
