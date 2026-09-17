import unittest
import requests
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from backend.app.ingestion.parser import BISPreviewParser

class TestBISParser(unittest.TestCase):
    def setUp(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})

    def test_parse_biscuits_preview(self):
        url = "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=1011_2002_reff2019"
        resp = self.session.get(url, timeout=10)
        self.assertEqual(resp.status_code, 200)
        
        parsed = BISPreviewParser.parse_preview_html(resp.text, source_url=url)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['standard_number'], "IS 1011")
        self.assertEqual(parsed['publication_year'], 2002)
        self.assertEqual(parsed['reaffirmed_year'], 2019)
        self.assertIn("Biscuits", parsed['title'])
        self.assertEqual(parsed['ics_code'], "67.060")
        self.assertEqual(parsed['committee_code'], "FAD 24")
        self.assertTrue(len(parsed['scope']) > 20)
        self.assertTrue(len(parsed['references']) >= 5)
        print("\n[SUCCESS] Parsed IS 1011:", parsed['title'], f"({len(parsed['references'])} references)")

    def test_parse_cement_preview(self):
        url = "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=269_2015_reff2020"
        resp = self.session.get(url, timeout=10)
        self.assertEqual(resp.status_code, 200)
        
        parsed = BISPreviewParser.parse_preview_html(resp.text, source_url=url)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['standard_number'], "IS 269")
        self.assertEqual(parsed['publication_year'], 2015)
        self.assertEqual(parsed['reaffirmed_year'], 2020)
        self.assertIn("Portland Cement", parsed['title'])
        self.assertEqual(parsed['committee_code'], "CED 2")
        print("[SUCCESS] Parsed IS 269:", parsed['title'], f"({len(parsed['references'])} references)")

    def test_parse_env_testing_preview(self):
        url = "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=9000_1_1988_reff2019"
        resp = self.session.get(url, timeout=10)
        self.assertEqual(resp.status_code, 200)
        
        parsed = BISPreviewParser.parse_preview_html(resp.text, source_url=url)
        self.assertIsNotNone(parsed)
        self.assertIn("IS 9000", parsed['standard_number'])
        self.assertEqual(parsed['publication_year'], 1988)
        self.assertEqual(parsed['reaffirmed_year'], 2019)
        print("[SUCCESS] Parsed IS 9000:", parsed['title'])

if __name__ == "__main__":
    unittest.main()
