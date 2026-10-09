"""Cobertura básica do painel local, sem chamadas de rede."""
import tempfile
from pathlib import Path
import unittest

from dashboard import case_page, dashboard, layout
from instaguard import connect, timestamp
from scripts.simulate_load import simulate


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.db = connect(Path(self.tempdir.name) / "test.db")
        self.addCleanup(self.db.close)

    def test_empty_dashboard_and_local_notice(self):
        page = dashboard(self.db, "token-de-teste").decode("utf-8")
        self.assertIn("Central de revisão e evidências", page)
        self.assertIn("10.000 eventos fictícios", page)
        self.assertIn('name="csrf"', page)
        self.assertIn("SEM DENÚNCIAS AUTOMÁTICAS", page)

    def test_html_escapes_untrusted_fields(self):
        now = timestamp()
        cur = self.db.execute(
            "INSERT INTO cases(username,category,reason,status,created_at,updated_at) VALUES(?,?,?,'new',?,?)",
            ("exemplo", "other", '<script>alert("x")</script>', now, now)
        )
        self.db.commit()
        main = dashboard(self.db, "token").decode("utf-8")
        detail = case_page(self.db, cur.lastrowid, "token").decode("utf-8")
        for page in (main, detail):
            self.assertNotIn("<script>", page)
            self.assertIn("&lt;script&gt;", page)
        self.assertIn("Baixar relatório Markdown", detail)

    def test_simulation_is_offline_only(self):
        result = simulate(10_000)
        self.assertTrue(result["passed"])
        self.assertEqual(result["processed_locally"], 10_000)
        self.assertEqual(result["real_reports_sent"], 0)
        self.assertEqual(result["mode"], "offline_simulation")

    def test_layout_escapes_title(self):
        page = layout("<script>", "<p>safe</p>").decode("utf-8")
        self.assertIn("&lt;script&gt;", page.split("<title>")[1].split("</title>")[0])


if __name__ == "__main__":
    unittest.main()
