import sys
import json
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

pairs = [
    ("Protein-fortified bread for hospital", "अस्पताल के लिए प्रोटीन युक्त ब्रेड"),
    ("Biscuits for children nutrition", "बच्चों के पोषण के लिए बिस्कुट"),
    ("Portland cement for construction", "निर्माण के लिए पोर्टलैंड सीमेंट"),
    ("Solar inverter for rooftop photovoltaic power", "छत पर सौर ऊर्जा के लिए सौर इन्वर्टर"),
    ("Fire extinguisher portable type", "पोर्टेबल प्रकार का अग्निशामक"),
    ("Stainless steel cable tray with perforated type", "छिद्रित प्रकार के साथ स्टेनलेस स्टील केबल ट्रे"),
    ("XLPE insulated power cables 11kV", "11kV एक्सएलपीई इन्सुलेटेड पावर केबल")
]

url = "http://localhost:8000/api/v1/recommend"

for en, hi in pairs:
    def get_top(q):
        payload = {"requirement": q, "top_k": 5, "skip_live_crawl": True}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            top = res.get("primary_recommendations", [])
            top_stds = [t["standard_number"] for t in top]
            return (top_stds, res.get("translated_query"))

    top_en, _ = get_top(en)
    top_hi, trans = get_top(hi)
    match = "MATCH" if (top_en and top_hi and top_en[0] == top_hi[0]) else "MISMATCH"
    print(f"[{match}]")
    print(f"  EN: '{en}' -> {top_en}")
    print(f"  HI: '{hi}' (translated: '{trans}') -> {top_hi}")
    print("-" * 60)
