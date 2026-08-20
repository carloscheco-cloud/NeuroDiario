import json
import tempfile
import unittest
from pathlib import Path

from neurodiario.neurodata.collectors.article_text import ArticleTextEnricher
from neurodiario.neurodata.config import StudyConfig, load_study
from neurodiario.neurodata.quality import audit_records
from neurodiario.neurodata.reporting import summarize
from neurodiario.neurodata.social_import import import_social_file


class NeuroDataTests(unittest.TestCase):
    def test_load_study(self):
        payload = {
            "study": {"slug": "demo", "client": "Demo", "title": "Demo Study", "target": "Demo", "period_start": "2026-01-01", "period_end": "2026-08-01"},
            "search_terms": ["demo"]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "study.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            study = load_study(path)
        self.assertEqual(study.slug, "demo")
        self.assertEqual(study.search_terms, ["demo"])

    def test_social_import_hashes_author(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "comments.csv"
            path.write_text("author,comment,likes\nJuan,Me preocupa el agua,5\n", encoding="utf-8")
            rows = import_social_file(path, "demo", "facebook", "https://example.com/post")
        self.assertEqual(len(rows), 1)
        self.assertNotEqual(rows[0]["author_hash"], "Juan")
        self.assertEqual(rows[0]["text"], "Me preocupa el agua")

    def test_article_text_extraction_prefers_article(self):
        html = """
        <html><body><nav>Menu</nav><article>
          <p>Este es el primer párrafo del artículo con suficiente contenido para ser relevante y conservarse.</p>
          <p>Este es el segundo párrafo del artículo y amplía la discusión sobre agua, minería y comunidad.</p>
          <p>Este es el tercer párrafo con más contexto público para que la extracción supere el mínimo esperado.</p>
          <p>Este es el cuarto párrafo que permite comprobar que el extractor reúne el cuerpo central sin el menú.</p>
          <p>Este es el quinto párrafo con información adicional sobre el proyecto y sus actores principales.</p>
          <p>Este es el sexto párrafo que completa una muestra suficientemente larga para la prueba automática.</p>
        </article><footer>Pie de página</footer></body></html>
        """
        text = ArticleTextEnricher()._extract(html)
        self.assertIn("primer párrafo", text)
        self.assertIn("sexto párrafo", text)
        self.assertNotIn("Menu", text)
        self.assertNotIn("Pie de página", text)

    def test_diario_libre_adds_public_amp_candidate(self):
        url = "https://www.diariolibre.com/actualidad/noticia-demo-AB123"
        candidates = ArticleTextEnricher._candidate_urls(url)
        self.assertEqual(candidates[0], url)
        self.assertIn("https://www.diariolibre.com/amp/actualidad/noticia-demo-AB123", candidates)

    def test_audit_marks_non_article_landing_for_review(self):
        study = StudyConfig(slug="demo", client="GoldQuest", title="Demo", target="GoldQuest", search_terms=["GoldQuest", "Proyecto Romero"])
        records = [{
            "id": "1", "source_type": "media_article", "source_name": "Hoy",
            "title": "Noticias del 30 de enero de 2018", "text": "GoldQuest Proyecto Romero",
            "published_at": "30 ene 2018", "full_text_chars": 25, "enrichment_status": "failed",
        }]
        audit = audit_records(study, records)
        self.assertEqual(audit["review"], 1)
        self.assertIn("non_article_landing", audit["review_records"][0]["flags"])
        self.assertEqual(audit["by_year"]["2018"], 1)

    def test_summary_excludes_low_relevance(self):
        records = [
            {
                "source_type": "media_article", "source_name": "Medio A",
                "analysis": {"relevance_score": 0.95, "sentiment": "negativo", "stance": "critico", "narratives": [{"name": "agua", "score": 0.9}], "actors": ["GoldQuest"]},
            },
            {
                "source_type": "media_article", "source_name": "Medio B",
                "analysis": {"relevance_score": 0.10, "sentiment": "positivo", "stance": "favorable", "narratives": [{"name": "tenis", "score": 0.9}], "actors": ["Otro"]},
            },
        ]
        summary = summarize(records)
        self.assertEqual(summary["analyzed_records"], 2)
        self.assertEqual(summary["relevant_records"], 1)
        self.assertEqual(summary["excluded_low_relevance"], 1)
        self.assertEqual(summary["narratives"][0][0], "agua")
        self.assertEqual(summary["actors"][0][0], "GoldQuest")


if __name__ == "__main__":
    unittest.main()
