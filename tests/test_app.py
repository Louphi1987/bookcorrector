from __future__ import annotations

import io
import pathlib
import sys
import unittest

from docx import Document

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app


class AppTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = app.test_client()

    def test_health(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "ok")

    def test_analyze_plain_text(self) -> None:
        response = self.client.post(
            "/api/analyze",
            data={"text": "Il y a  deux chats... comme meme."},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertGreaterEqual(payload["stats"]["total"], 3)
        self.assertTrue(any(issue["replacement"] for issue in payload["issues"]))

    def test_extended_exact_replacements_and_registre(self) -> None:
        response = self.client.post(
            "/api/analyze",
            data={"text": "Sa va, c'est des problemes. Du coup, je m'excuse et tout a fait."},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        replacements = {issue["excerpt"]: issue["replacement"] for issue in payload["issues"] if issue["replacement"]}
        self.assertEqual(replacements.get("Sa va"), "Ça va")
        self.assertEqual(replacements.get("c'est des"), "ce sont des")
        self.assertEqual(replacements.get("tout a fait"), "tout à fait")
        self.assertGreaterEqual(payload["stats"]["registre"], 1)
        registre_issues = [issue for issue in payload["issues"] if issue["category"] == "registre"]
        self.assertTrue(registre_issues)
        self.assertTrue(all(issue["replacement"] is None for issue in registre_issues))

    def test_avoids_obvious_false_positives(self) -> None:
        response = self.client.post(
            "/api/analyze",
            data={"text": "Ce genre littéraire, quelque part dans le chapitre, ainsi que sa fin, il a ouvert le débat."},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        excerpts = {issue["excerpt"] for issue in payload["issues"]}
        self.assertNotIn("genre", excerpts)
        self.assertNotIn("quelque part", excerpts)
        self.assertNotIn("ainsi que", excerpts)
        self.assertNotIn("il a ouvert", excerpts)

    def test_export_docx(self) -> None:
        response = self.client.post(
            "/api/export-docx",
            json={
                "filename": "roman.txt",
                "original_text": "Il y a  deux chats...",
                "selected_ids": ["issue-1"],
                "issues": [
                    {
                        "id": "issue-1",
                        "category": "typographie",
                        "message": "Espaces multiples detectees.",
                        "excerpt": "  ",
                        "start": 6,
                        "end": 8,
                        "replacement": " ",
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 200)
        document = Document(io.BytesIO(response.data))
        self.assertTrue(document.paragraphs)


if __name__ == "__main__":
    unittest.main()
