import re
from typing import Dict, Any, List
from backend.app.schemas.standard_schemas import ExtractedEntities

class ProcurementNLPExtractor:
    """
    Extracts structured entities, procurement domain, product keywords,
    safety requirements, testing needs, and explicit IS numbers from raw user input.
    """

    STOP_WORDS = {
        "procure", "procurement", "purchase", "purchasing", "supply", "supplying", "tender",
        "requirement", "need", "install", "installation", "for", "with", "and", "under",
        "from", "the", "a", "an", "of", "in", "to", "units", "nos", "numbers", "bags",
        "meters", "kg", "tons", "packets", "certified", "standard", "quality", "government"
    }

    DOMAIN_MAPPINGS = {
        "Food and Agriculture": ["biscuit", "biscuits", "wheat", "maida", "flour", "milk", "sugar", "food", "edible", "snack", "bakery", "atta", "tea", "coffee", "rice", "spice", "salt", "oil"],
        "Electrotechnical": ["solar", "inverter", "pcu", "photovoltaic", "pv", "cable", "wire", "transformer", "switchgear", "led", "lamp", "battery", "ups", "generator", "motor", "meter"],
        "Civil Engineering": ["cement", "portland", "concrete", "steel", "tmt", "rebar", "brick", "aggregate", "pipe", "hdpe", "pvc pipe", "structural steel", "tiles", "water meter"],
        "Electronics and Information Technology": ["computer", "laptop", "server", "software", "biometric", "cctv", "monitor", "router", "telecom", "printer"],
        "Mechanical Engineering": ["fire extinguisher", "pump", "valve", "engine", "compressor", "crane", "cylinder", "bearing", "extinguisher", "oxygen cylinder"],
        "Personal Protective Equipment & Safety": ["mask", "n95", "helmet", "safety shoe", "safety shoes", "footwear", "gloves", "goggles", "ppe kit"]
    }

    @classmethod
    def extract_entities(cls, text: str) -> ExtractedEntities:
        cleaned = text.strip()
        lower = cleaned.lower()

        # 1. Detect explicit IS numbers (e.g. IS 1011, IS 16221, IS:456, IS-269)
        detected_is = re.findall(r'IS\s*[:\-]?\s*(\d+(?:\s*(?:\(Part\s*\d+\)|Part\s*\d+))?)', cleaned, re.IGNORECASE)
        normalized_is = [f"IS {num.strip()}" for num in detected_is]

        # 2. Extract Quantity
        qty_match = re.search(r'(\d+(?:,\d+)?(?:\s*(?:nos|numbers|units|kg|tons|metric tons|litres|meters|km|kw|mw|wp|bags|packets))?)', cleaned, re.IGNORECASE)
        quantity = qty_match.group(1).strip() if qty_match else None

        # 3. Detect Domain
        detected_domain = None
        domain_scores = {}
        for domain, keywords in cls.DOMAIN_MAPPINGS.items():
            score = sum(1 for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', lower))
            if score > 0:
                domain_scores[domain] = score

        if domain_scores:
            detected_domain = max(domain_scores, key=domain_scores.get)

        # 4. Extract Product Category and Key Search Tokens
        product_category = None
        matched_kws = []
        for kw_list in cls.DOMAIN_MAPPINGS.values():
            for kw in kw_list:
                if re.search(r'\b' + re.escape(kw) + r'\b', lower):
                    matched_kws.append(kw)

        if matched_kws:
            # Pick the most specific (longest) matched keyword
            product_category = max(matched_kws, key=len).title()
        else:
            # Fallback: extract core non-stop words
            tokens = [w for w in re.findall(r'[a-zA-Z]+', lower) if w not in cls.STOP_WORDS and len(w) > 2]
            if tokens:
                product_category = " ".join(tokens[:2]).title()

        # 5. Detect Safety and Testing requirements
        safety_critical = any(w in lower for w in ["safety", "hazard", "fire", "shock", "safe", "protective", "hygiene", "toxic", "medical", "protection"])
        testing_required = any(w in lower for w in ["test", "testing", "sampling", "inspection", "acceptance", "quality check", "lab test", "certification", "conformance"])

        # 6. Extract Application Context
        app_match = re.search(r'(?:for|in)\s+([a-zA-Z0-9\s]+?)(?:\.|$|,)', cleaned, re.IGNORECASE)
        application_context = app_match.group(1).strip() if app_match else None

        return ExtractedEntities(
            product_category=product_category,
            domain=detected_domain,
            application_context=application_context,
            safety_critical=safety_critical,
            testing_required=testing_required,
            quantity=quantity,
            detected_is_numbers=normalized_is
        )
