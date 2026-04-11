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
