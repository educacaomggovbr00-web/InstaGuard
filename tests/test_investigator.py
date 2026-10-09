"""Tests for public metadata review, with no Instagram access."""
import unittest

from investigator import assess


class InvestigatorTests(unittest.TestCase):
    def test_public_name_does_not_identify_creator(self):
        result = assess("@melancoolics", display_name="Nome exibido")
        self.assertEqual(result["username"], "melancoolics")
        self.assertEqual(result["review_indicators"], [])
        self.assertIn("Não determinada", result["creator_identity"])

    def test_financial_language_is_flagged_not_judged(self):
        result = assess("example", bio="Envie pix e receba lucro garantido")
        indicators = [value["indicator"] for value in result["review_indicators"]]
        self.assertIn("pedido de dinheiro", indicators)
        self.assertIn("promessa financeira", indicators)
        self.assertIn("não comprovam fraude", result["conclusion"])

    def test_url_validation_and_links(self):
        with self.assertRaises(ValueError):
            assess("example", source_url="http://example.com")
        result = assess("example", bio="Site: https://example.org/path")
        self.assertEqual(result["links_in_bio"], ["https://example.org/path"])


if __name__ == "__main__":
    unittest.main()
