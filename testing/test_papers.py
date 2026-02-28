import unittest
import uuid
from fastapi.testclient import TestClient

from app.app import app


class TestPapersAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def _new_paper_payload(self):
        uid = uuid.uuid4().hex
        return {
            "id": f"test-{uid}",
            "title": f"Test Paper {uid}",
            "abstract": "This is a test abstract.",
            "conference": f"UnitTestConf-{uid}",
            "keywords": ["test", "unit"],
        }

    def test_get_random_paper(self):
        resp = self.client.get("/v1/papers")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        paper = data[0]
        self.assertIn("id", paper)
        self.assertIn("title", paper)
        self.assertIn("abstract", paper)

    def test_get_paper_by_id(self):
        resp = self.client.get("/v1/papers")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        paper_id = data[0]["id"]

        resp = self.client.get(f"/v1/papers/{paper_id}")
        self.assertEqual(resp.status_code, 200)
        paper = resp.json()
        self.assertEqual(paper["id"], paper_id)
        self.assertIn("title", paper)
        self.assertIn("abstract", paper)

    def test_add_paper(self):
        payload = self._new_paper_payload()
        resp = self.client.post("/v1/papers", json=payload)
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        print(f"Created paper id: {data['id']}")
        print(f"Created paper title: {data['title']}")
        self.assertEqual(data["id"], payload["id"])
        self.assertEqual(data["title"], payload["title"])
        self.assertEqual(data["abstract"], payload["abstract"])
        self.assertEqual(data["conference"], payload["conference"])
        self.assertIn("keywords", data)

        resp = self.client.get(f"/v1/papers/{payload['id']}")
        self.assertEqual(resp.status_code, 200)

        resp = self.client.delete(f"/v1/papers/{payload['id']}")
        self.assertEqual(resp.status_code, 204)

    def test_delete_paper_by_id(self):
        payload = self._new_paper_payload()
        resp = self.client.post("/v1/papers", json=payload)
        self.assertEqual(resp.status_code, 201)

        resp = self.client.delete(f"/v1/papers/{payload['id']}")
        self.assertEqual(resp.status_code, 204)

        resp = self.client.get(f"/v1/papers/{payload['id']}")
        self.assertEqual(resp.status_code, 404)
