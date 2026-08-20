import json
import tempfile
import unittest
from pathlib import Path

from neurodiario.neurodata.config import load_study
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

    def test_summary(self):
        records = [{
            "source_type": "social_comment", "source_name": "facebook",
            "analysis": {"sentiment": "negativo", "stance": "critico", "narratives": [{"name": "agua", "score": 0.9}], "actors": ["GoldQuest"]}
        }]
        summary = summarize(records)
        self.assertEqual(summary["narratives"][0][0], "agua")
        self.assertEqual(summary["actors"][0][0], "GoldQuest")


if __name__ == "__main__":
    unittest.main()
