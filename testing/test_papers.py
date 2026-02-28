import unittest
from fastapi.testclient import TestClient

from app.app import app


class TestPapersAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

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
