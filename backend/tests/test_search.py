import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.app.database.connection import SessionLocal
from backend.app.retrieval.search_engine import HybridSearchEngine
from backend.app.recommendation.engine import ProcurementRecommendationEngine
from backend.app.schemas.standard_schemas import ProcurementRequirementRequest

class TestSearchAndRecommendation(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        self.rec_engine = ProcurementRecommendationEngine(self.db)

    def tearDown(self):
        self.db.close()

    def test_solar_inverter_recommendation(self):
        req = ProcurementRequirementRequest(
            requirement="Procurement of 500kW grid connected solar power conditioning units (inverters) with anti-islanding protection.",
            skip_live_crawl=True
        )
        res = self.rec_engine.recommend(req)
        self.assertGreater(len(res.primary_recommendations), 0)
        top_std = res.primary_recommendations[0].standard_number
        self.assertTrue("16221" in top_std or "16169" in top_std)
        print(f"\n[PASS] Solar Recommendation: Top Standard = {top_std} | {res.primary_recommendations[0].title}")

    def test_biscuit_recommendation(self):
        req = ProcurementRequirementRequest(
            requirement="Supply of sweet biscuits for government mid-day meal nutrition program.",
            skip_live_crawl=True
        )
        res = self.rec_engine.recommend(req)
        self.assertGreater(len(res.primary_recommendations), 0)
        std_nums = [s.standard_number for s in res.primary_recommendations]
        self.assertTrue(any(x in std_nums for x in ["IS 1011", "IS 7487", "IS 8665"]))
        print(f"[PASS] Biscuit Recommendation: Matched {std_nums[0]} | References = {len(res.allied_references)}")

    def test_cement_recommendation(self):
        req = ProcurementRequirementRequest(
            requirement="Procuring 53 grade ordinary Portland cement for bridge construction.",
            skip_live_crawl=True
        )
        res = self.rec_engine.recommend(req)
        self.assertGreater(len(res.primary_recommendations), 0)
        std_nums = [s.standard_number for s in res.primary_recommendations]
        self.assertIn("IS 269", std_nums)
        print(f"[PASS] Cement Recommendation: Matched IS 269 | Rationale = {res.primary_recommendations[0].why_relevant[:60]}...")


if __name__ == "__main__":
    unittest.main()
