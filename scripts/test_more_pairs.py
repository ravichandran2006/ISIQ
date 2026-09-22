import sys
import json
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
url = "http://localhost:8000/api/v1/recommend"

test_cases = [
    ("Solar panel for electricity", "बिजली के लिए सोलर पैनल"),
    ("Electric wire for house wiring", "घर की वायरिंग के लिए बिजली का तार"),
    ("Steel bars for concrete reinforcement", "कंक्रीट सुदृढीकरण के लिए स्टील की छड़ें"),
    ("Wheat flour for bakery", "बेकरी के लिए गेहूं का आटा"),
    ("Milk powder for children", "बच्चों के लिए दूध पाउडर"),
    ("Fire hose delivery coupling", "फायर होज डिलीवरी कपलिंग"),
    ("Submersible water pump", "सबमर्सिबल पानी का पंप"),
    ("LED street light luminaire", "एलईडी स्ट्रीट लाइट ल्यूमिनेयर")
]

for en, hi in test_cases:
    def get_res(q):
        data = json.dumps({"requirement": q, "top_k": 3, "skip_live_crawl": True}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        res = json.loads(urllib.request.urlopen(req).read().decode("utf-8"))
        top = [r["standard_number"] for r in res.get("primary_recommendations", [])]
        return top, res.get("translated_query")

    top_en, _ = get_res(en)
    top_hi, trans = get_res(hi)
    match = "MATCH" if (top_en and top_hi and top_en[0] == top_hi[0]) else "MISMATCH"
    print(f"[{match}] EN: '{en}' -> {top_en}")
    print(f"       HI: '{hi}' -> (trans: '{trans}') -> {top_hi}")
    print()
