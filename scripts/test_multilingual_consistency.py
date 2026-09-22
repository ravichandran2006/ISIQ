import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

def test_query(label, q):
    url = "http://localhost:8000/api/v1/recommend"
    payload = {"requirement": q, "top_k": 3, "skip_live_crawl": True}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        recs = [(r["standard_number"], r["title"]) for r in res.get("primary_recommendations", [])]
        print(f"[{label}] Query: {q}")
        print(f"  Detected Lang : {res.get('detected_language')}")
        print(f"  Translated To : {res.get('translated_query')}")
        print("  Recommendations:")
        for num, title in recs:
            print(f"    * {num} - {title}")
        print()
        return [r[0] for r in recs]

print("=== VERIFYING RECOMMENDATION CONSISTENCY ACROSS LANGUAGES ===")
en_recs = test_query("ENGLISH", "Procurement of protein fortified bread for hospital canteen")
hi_recs = test_query("HINDI", "अस्पताल के लिए प्रोटीन युक्त ब्रेड की खरीद")
ta_recs = test_query("TAMIL", "மருத்துவமனை கேண்டீனுக்கு புரோட்டீன் ரொட்டி கொள்முதல்")

if en_recs and hi_recs and en_recs[0] == hi_recs[0]:
    print(f"SUCCESS: Both English and Hindi returned the EXACT same top standard: {en_recs[0]}")
else:
    print(f"DIFFERENCE: EN={en_recs}, HI={hi_recs}")
