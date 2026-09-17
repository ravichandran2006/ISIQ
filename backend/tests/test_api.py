import unittest
import sys
import os
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.app.main import app

class TestAPIEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "healthy")
        self.assertGreater(data["total_standards_indexed"], 0)
        print("\n[PASS] Health Endpoint:", data)

    def test_list_standards_endpoint(self):
        resp = self.client.get("/api/v1/standards?limit=5")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 5)
        print(f"[PASS] List Standards: Retrieved {len(data)} standards")

    def test_get_single_standard(self):
        resp = self.client.get("/api/v1/standards/IS 1011")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["standard_number"], "IS 1011")
        self.assertGreater(len(data["references"]), 0)
        print("[PASS] Get Standard IS 1011:", data["title"])

    def test_recommend_endpoint(self):
        payload = {
            "requirement": "Procure 500kW grid-connected solar inverters with anti-islanding protection.",
            "top_k": 3,
            "skip_live_crawl": True
        }
        resp = self.client.post("/api/v1/recommend", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreater(len(data["primary_recommendations"]), 0)
        rec_nums = [r["standard_number"] for r in data["primary_recommendations"]]
        self.assertTrue(any("16221" in num or "16169" in num for num in rec_nums))
        print("[PASS] API Recommend Output:", rec_nums[0])


    def test_benchmark_endpoint(self):
        resp = self.client.get("/api/v1/evaluation/benchmark")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreater(data["mean_precision_at_1"], 0.8)
        print(f"[PASS] Benchmark API: P@1 = {data['mean_precision_at_1'] * 100:.1f}% | Latency = {data['avg_latency_ms']}ms")

if __name__ == "__main__":
    unittest.main()
