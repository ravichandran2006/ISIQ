import sys
import json
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
url = "http://localhost:8000/api/v1/recommend"

def test(q):
    data = json.dumps({"requirement": q, "top_k": 3, "skip_live_crawl": True}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    res = json.loads(urllib.request.urlopen(req).read().decode("utf-8"))
    recs = [r["standard_number"] + " - " + r["title"][:45] for r in res.get("primary_recommendations", [])]
    print(f"Query: '{q}'")
    print(f"  Detected: {res.get('detected_language')}, Translated: '{res.get('translated_query')}'")
    print(f"  Top: {recs}\n")

test("Protein-fortified bread for hospital")
test("protein rich bread for hospital")
test("bread for hospital")
test("अस्पताल के लिए प्रोटीन युक्त ब्रेड की खरीद")
test("अस्पताल के लिए ब्रेड")
