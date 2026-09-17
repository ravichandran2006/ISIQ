import re
from typing import Dict, Any, Tuple

class BISDomainClassifier:
    """
    Classifies BIS standards into domains, safety categories, and testing designations
    using official committee mappings, ICS codes, and scope analysis.
    """

    COMMITTEE_DOMAINS = {
        "FAD": ("Food and Agriculture", "Food, Agriculture & Beverages"),
        "CED": ("Civil Engineering", "Construction, Buildings & Structural Engineering"),
        "ETD": ("Electrotechnical", "Electrical Systems, Energy, Solar & Power Equipment"),
        "LITD": ("Electronics and Information Technology", "IT, Electronics, Telecom & Software"),
        "MED": ("Mechanical Engineering", "Machinery, Boilers, Tools & Pumps"),
        "CHD": ("Chemical", "Chemicals, Petrochemicals, Paints & Polymers"),
        "PCD": ("Petroleum, Coal and Related Products", "Petroleum & Fuels"),
        "TED": ("Transport Engineering", "Automotive, Aviation & Railways"),
        "TXD": ("Textiles", "Textiles, Fabrics & Garments"),
        "MSD": ("Management and Systems", "Quality Management & Safety Systems"),
        "WRD": ("Water Resources", "Water Infrastructure & Irrigation")
    }

    SAFETY_KEYWORDS = [
        "safety", "protection", "hazard", "fire safety", "electric shock", "flammability",
        "explosion", "overheating", "radiation", "hygienic", "toxicity", "breakage"
    ]

    TESTING_KEYWORDS = [
        "methods of test", "method of test", "sampling", "determination of", "test procedure",
        "testing", "inspection", "measurement", "acceptance criteria", "test method"
    ]

    SAMPLING_KEYWORDS = [
        "sampling", "lot size", "sample preparation", "scale of sampling", "criteria for conformity"
    ]

    @classmethod
    def classify_domain(cls, committee_code: str = "", ics_code: str = "", title: str = "", scope: str = "") -> str:
        if committee_code:
            prefix = committee_code.split()[0].upper()
            if prefix in cls.COMMITTEE_DOMAINS:
                return cls.COMMITTEE_DOMAINS[prefix][0]

        if ics_code:
            ics_prefix = ics_code.split('.')[0]
            if ics_prefix == "67":
                return "Food and Agriculture"
            elif ics_prefix in ["91", "93"]:
                return "Civil Engineering"
            elif ics_prefix in ["27", "29"]:
                return "Electrotechnical"
            elif ics_prefix in ["31", "33", "35"]:
                return "Electronics and Information Technology"
            elif ics_prefix in ["13"]:
                return "Safety & Environment"

        # Fallback to title/scope keywords
        text = f"{title} {scope}".lower()
        if any(w in text for w in ["biscuit", "food", "sugar", "wheat", "maida", "milk", "tea", "coffee"]):
            return "Food and Agriculture"
        elif any(w in text for w in ["cement", "concrete", "pipe", "structural", "brick", "steel bar"]):
            return "Civil Engineering"
        elif any(w in text for w in ["solar", "inverter", "cable", "transformer", "pv", "motor", "switchgear", "led"]):
            return "Electrotechnical"
        elif any(w in text for w in ["computer", "software", "electronic", "server", "telecom"]):
            return "Electronics and Information Technology"
        elif any(w in text for w in ["fire extinguisher", "pump", "valve", "engine", "vehicle"]):
            return "Mechanical Engineering"
        
        return "General Standard"

    @classmethod
    def analyze_safety_and_testing(cls, title: str, scope: str, committee_code: str = "") -> Dict[str, Any]:
        combined_text = f"{title} {scope}".lower()
        
        is_safety = any(kw in combined_text for kw in cls.SAFETY_KEYWORDS)
        is_testing = any(kw in combined_text for kw in cls.TESTING_KEYWORDS)
        is_sampling = any(kw in combined_text for kw in cls.SAMPLING_KEYWORDS)
        is_quality = "specification" in combined_text or "requirements" in combined_text

        safety_justification = ""
        if is_safety:
            matched = [kw for kw in cls.SAFETY_KEYWORDS if kw in combined_text]
            safety_justification = f"Standard defines safety clauses and hazard protection for: {', '.join(matched[:3])}."
        
        testing_summary = ""
        if is_testing:
            testing_summary = "Includes explicit test methods, acceptance criteria, and conformity verification."

        return {
            "is_safety_related": is_safety,
            "is_testing_related": is_testing,
            "is_sampling_related": is_sampling,
            "is_quality_spec": is_quality,
            "safety_justification": safety_justification,
            "testing_methods_summary": testing_summary,
            "source_type": "rule_based"
        }
