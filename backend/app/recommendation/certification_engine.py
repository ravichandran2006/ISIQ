import re
from typing import Dict, Any, List, Optional, Tuple

class CertificationRequirementEngine:
    """
    Intelligent Grounded Certification and Regulatory Mandate Engine for BISense.
    Determines:
    1. Mandatory vs Voluntary certification under Indian statutory regulations.
    2. Applicable BIS Scheme:
       - BIS Product Certification (ISI Mark Scheme-I) [Mandatory under QCO vs Voluntary]
       - Compulsory Registration Scheme (CRS Scheme-II) [MeitY / MNRE]
       - BIS Hallmarking Scheme [DoCA Gold & Silver Orders]
       - Voluntary Standards & Codes of Practice
    3. Governing Quality Control Orders (QCO) and Central Ministry citations.
    4. Grounded justification for procurement officers on GeM.
    """

    # 1. Official MeitY & MNRE Compulsory Registration Scheme (CRS - Scheme II)
    CRS_PATTERNS = [
        # IS Numbers under CRS
        r"IS\s*13252",  # IT Equipment / Computers / Servers / Laptops / Printers
        r"IS\s*16221",  # Photovoltaic Power Converters / Solar Inverters
        r"IS\s*16169",  # Anti-islanding for Solar Inverters
        r"IS\s*16102",  # Self-ballasted LED lamps
        r"IS\s*16046",  # Secondary Lithium / Nickel cells and batteries
        r"IS\s*15885",  # Lamp control gear / LED drivers
        r"IS\s*16242",  # UPS / Inverters
        r"IS\s*616\b",   # Audio, video and electronic apparatus
        r"IS\s*302\s*\(Part\s*2\s*Sec\s*25\)",  # Microwave ovens
        r"IS\s*302\s*\(Part\s*2\s*Sec\s*26\)",  # Clocks
    ]

    CRS_KEYWORDS = [
        "solar inverter", "photovoltaic inverter", "pv inverter", "power converter",
        "laptop", "server", "desktop computer", "information technology equipment",
        "secondary cell", "lithium battery", "lithium ion", "led lamp", "led luminaire",
        "ups", "uninterruptible power supply", "tablet", "mobile phone", "smart card reader"
    ]

    # 2. BIS Hallmarking Scheme (Precious Metals)
    HALLMARKING_PATTERNS = [
        r"IS\s*1417",   # Gold and Gold Alloys, Jewellery/Artefacts (Mandatory)
        r"IS\s*1418",   # Assaying of Gold
        r"IS\s*2112",   # Silver and Silver Alloys (Voluntary/Applicable)
        r"IS\s*2113",   # Assaying of Silver
    ]

    HALLMARKING_KEYWORDS = [
        "gold", "gold jewellery", "gold jewelry", "gold artefact", "gold bullion",
        "silver jewellery", "silver jewelry", "silver artefact", "hallmark", "hallmarked", "huid",
        "22k", "24k", "18k", "carat gold", "karat gold"
    ]

    # 3. Known Mandatory Quality Control Orders (QCO) under Scheme-I (ISI Mark)
    QCO_MANDATES = [
        # Steel & Stainless Steel Products (Ministry of Steel)
        {
            "patterns": [r"IS\s*1786", r"IS\s*2062", r"IS\s*277\b", r"IS\s*1239", r"IS\s*1248", r"IS\s*2830", r"IS\s*2831", r"IS\s*1875"],
            "keywords": ["tmt", "rebar", "structural steel", "mild steel", "galvanized sheet", "stainless steel", "cable tray", "steel wire", "steel plate"],
            "ministry": "Ministry of Steel",
            "order": "Steel and Steel Products (Quality Control) Order",
            "scheme": "Mandatory ISI Scheme-I",
            "legal_act": "Section 16 of Bureau of Indian Standards Act, 2016"
        },
        # Cement Products (DPIIT / Ministry of Commerce & Industry)
        {
            "patterns": [r"IS\s*269\b", r"IS\s*455\b", r"IS\s*1489", r"IS\s*8112", r"IS\s*12269"],
            "keywords": ["cement", "portland cement", "opc", "ppc", "slag cement"],
            "ministry": "DPIIT, Ministry of Commerce & Industry",
            "order": "Cement (Quality Control) Order",
            "scheme": "Mandatory ISI Scheme-I",
            "legal_act": "Section 16 of Bureau of Indian Standards Act, 2016"
        },
        # Electrical Wires, Cables & Transformers (DPIIT / Ministry of Power)
        {
            "patterns": [r"IS\s*694\b", r"IS\s*1554", r"IS\s*7098", r"IS\s*2026", r"IS\s*1180"],
            "keywords": ["pvc cable", "electric cable", "power transformer", "distribution transformer", "flexible cord", "wiring cable"],
            "ministry": "DPIIT / Ministry of Heavy Industries",
            "order": "Electrical Wires, Cables & Transformers (Quality Control) Order",
            "scheme": "Mandatory ISI Scheme-I",
            "legal_act": "Section 16 of Bureau of Indian Standards Act, 2016"
        },
        # Plastic & Polymer Pipes (Department of Chemicals & Petrochemicals)
        {
            "patterns": [r"IS\s*4984", r"IS\s*4985", r"IS\s*12818", r"IS\s*13592"],
            "keywords": ["hdpe pipe", "pvc pipe", "polyethylene pipe", "water supply pipe"],
            "ministry": "Department of Chemicals and Petrochemicals (DCPC)",
            "order": "Polyethylene & PVC Pipes (Quality Control) Order",
            "scheme": "Mandatory ISI Scheme-I",
            "legal_act": "Section 16 of Bureau of Indian Standards Act, 2016"
        },
        # Personal Protective Equipment & Fire Safety (MHA / Textiles / DPIIT)
        {
            "patterns": [r"IS\s*15683", r"IS\s*2925", r"IS\s*9473", r"IS\s*636"],
            "keywords": ["fire extinguisher", "safety helmet", "industrial helmet", "half mask", "respirator", "n95", "ffp2"],
            "ministry": "Ministry of Home Affairs & Ministry of Textiles",
            "order": "Fire Safety Equipment & Protective Equipment (Quality Control) Order",
            "scheme": "Mandatory ISI Scheme-I",
            "legal_act": "Section 16 of Bureau of Indian Standards Act, 2016"
        },
        # Infant Food & Dairy Substitutes (Ministry of Health / FSSAI / Consumer Affairs)
        {
            "patterns": [r"IS\s*1165", r"IS\s*14433", r"IS\s*13428", r"IS\s*14543"],
            "keywords": ["milk powder", "infant formula", "packaged drinking water", "mineral water"],
            "ministry": "FSSAI & Ministry of Consumer Affairs",
            "order": "Infant Milk Substitutes Act & Food Safety (Mandatory Certification) Regulations",
            "scheme": "Mandatory ISI Scheme-I",
            "legal_act": "Food Safety and Standards Act, 2006 & BIS Act 2016"
        },
        # Metallic Cable Trays & Raceways (Ministry of Heavy Industries)
        {
            "patterns": [r"IS\s*4759", r"IS\s*15669"],
            "keywords": ["cable tray", "cable ladder", "perforated cable tray"],
            "ministry": "Ministry of Heavy Industries",
            "order": "Cable Management Systems & Metallic Trays Mandate",
            "scheme": "Mandatory ISI Scheme-I",
            "legal_act": "Section 16 of Bureau of Indian Standards Act, 2016"
        }
    ]

    # 4. Strictly Voluntary Codes of Practice & Engineering Standards
    VOLUNTARY_PATTERNS = [
        r"IS\s*456\b",   # Plain and reinforced concrete - Code of Practice
        r"IS\s*800\b",   # General construction in steel - Code of Practice
        r"IS\s*732\b",   # Electrical wiring code of practice
        r"IS\s*5059\b",  # Hygiene conditions for bakery units (Advisory code)
        r"IS\s*7463\b",  # Wheat flour (Maida) for biscuit industry (Raw material)
        r"IS\s*1011\b",  # Biscuits specification (Voluntary ISI scheme)
        r"IS\s*2102\b",  # General tolerances for dimensions
        r"IS\s*1608\b",  # Tensile testing method
        r"IS\s*516\b",   # Method of tests for strength of concrete
        r"IS\s*4031\b",  # Physical tests for hydraulic cement
        r"IS\s*4032\b",  # Chemical analysis of hydraulic cement
        r"IS\s*3535\b",  # Sampling hydraulic cements
        r"IS\s*2629\b",  # Recommended practice for hot dip galvanizing
        r"IS\s*8082\b",  # Electroplated coatings of zinc
    ]

    @classmethod
    def evaluate_standard(cls, standard_number: str, title: str = "", scope: str = "", domain: str = "") -> Dict[str, Any]:
        """
        Dynamically evaluates an individual standard and classifies:
        - is_mandatory: bool
        - certification_scheme: str
        - mandate_type: str ("QCO", "CRS", "HALLMARKING", "VOLUNTARY", "CODE_OF_PRACTICE")
        - governing_order: str
        - mandate_reason: str
        - legal_act: str
        """
        std_clean = standard_number.upper().strip()
        combined_text = f"{std_clean} {title} {scope} {domain}".lower()

        # 1. Check if strictly Voluntary / Code of Practice
        for pat in cls.VOLUNTARY_PATTERNS:
            if re.search(pat, std_clean, re.IGNORECASE):
                is_code = "code" in combined_text or "practice" in combined_text or "method" in combined_text or "tolerance" in combined_text
                mandate_type = "CODE_OF_PRACTICE" if is_code else "VOLUNTARY"
                scheme_name = "Code of Practice / Design Standard" if is_code else "Voluntary ISI Scheme-I"
                return {
                    "is_mandatory": False,
                    "certification_scheme": scheme_name,
                    "mandate_type": mandate_type,
                    "governing_order": "None (Voluntary Standard)",
                    "mandate_reason": "Prescribes voluntary technical guidelines, test methods, or design codes. Compliance is advisory unless explicitly stipulated in the procurement tender contract.",
                    "legal_act": "BIS Act, 2016 (Voluntary Standard Publication)"
                }

        # 2. Check Compulsory Registration Scheme (CRS)
        for pat in cls.CRS_PATTERNS:
            if re.search(pat, std_clean, re.IGNORECASE):
                is_solar = "solar" in combined_text or "inverter" in combined_text or "16221" in std_clean or "16169" in std_clean
                authority = "MNRE (Ministry of New and Renewable Energy)" if is_solar else "MeitY (Ministry of Electronics & IT)"
                order_name = "Solar Photovoltaics, Systems & Devices (Compulsory Registration) Order" if is_solar else "Electronics & IT Goods (Compulsory Registration Scheme - CRS) Order"
                return {
                    "is_mandatory": True,
                    "certification_scheme": f"Mandatory CRS Scheme-II ({'MNRE' if is_solar else 'MeitY'})",
                    "mandate_type": "CRS",
                    "governing_order": order_name,
                    "mandate_reason": f"Mandatory Compulsory Registration Scheme (CRS) notified by {authority}. Supply without valid BIS registration is prohibited on GeM under Central Procurement Rules.",
                    "legal_act": "BIS (Conformity Assessment) Regulations, 2018 (Scheme-II)"
                }

        # Keyword match for CRS if title/scope clearly indicates IT goods or Solar Inverter
        for kw in cls.CRS_KEYWORDS:
            if kw in combined_text and ("safety" in combined_text or "specification" in combined_text):
                is_solar = "solar" in combined_text or "photovoltaic" in combined_text
                authority = "MNRE" if is_solar else "MeitY"
                return {
                    "is_mandatory": True,
                    "certification_scheme": f"Mandatory CRS Scheme-II ({authority})",
                    "mandate_type": "CRS",
                    "governing_order": f"{authority} Compulsory Registration Scheme (CRS) Order",
                    "mandate_reason": f"Notified under {authority} Compulsory Registration Scheme (CRS). Manufacturers must register product models with BIS before commercial distribution.",
                    "legal_act": "BIS (Conformity Assessment) Regulations, 2018 (Scheme-II)"
                }

        # 3. Check BIS Hallmarking Scheme (Gold & Silver)
        for pat in cls.HALLMARKING_PATTERNS:
            if re.search(pat, std_clean, re.IGNORECASE):
                is_gold = "1417" in std_clean or "1418" in std_clean or "gold" in combined_text
                if is_gold:
                    return {
                        "is_mandatory": True,
                        "certification_scheme": "Mandatory Hallmarking Scheme (DoCA)",
                        "mandate_type": "HALLMARKING",
                        "governing_order": "Hallmarking of Gold Jewellery and Gold Artefacts Order, 2020",
                        "mandate_reason": "Mandatory hallmarking enforced by Department of Consumer Affairs. Sale of gold jewellery without 6-digit alphanumeric HUID (Hallmark Unique Identification) is illegal.",
                        "legal_act": "Section 14 & 16 of BIS Act, 2016"
                    }
                else:
                    return {
                        "is_mandatory": False,
                        "certification_scheme": "Voluntary Hallmarking Scheme",
                        "mandate_type": "HALLMARKING",
                        "governing_order": "Silver Jewellery Hallmarking Guidelines",
                        "mandate_reason": "Hallmarking for silver articles is currently voluntary under BIS guidelines, providing recognized third-party purity assurance.",
                        "legal_act": "BIS Act, 2016"
                    }

        for kw in cls.HALLMARKING_KEYWORDS:
            if kw in combined_text:
                is_gold = "gold" in combined_text or "22k" in combined_text or "24k" in combined_text
                if is_gold:
                    return {
                        "is_mandatory": True,
                        "certification_scheme": "Mandatory Hallmarking Scheme (DoCA)",
                        "mandate_type": "HALLMARKING",
                        "governing_order": "Hallmarking of Gold Jewellery and Gold Artefacts Order",
                        "mandate_reason": "Mandatory hallmarking with HUID laser marking is statutorily enforced for all gold articles.",
                        "legal_act": "Section 14 & 16 of BIS Act, 2016"
                    }
                else:
                    return {
                        "is_mandatory": False,
                        "certification_scheme": "Voluntary Hallmarking Scheme",
                        "mandate_type": "HALLMARKING",
                        "governing_order": "Silver Hallmarking Guidelines",
                        "mandate_reason": "Third-party recognized hallmarking scheme for silver fineness verification.",
                        "legal_act": "BIS Act, 2016"
                    }

        # 4. Check Known QCO Mandates (Scheme-I)
        for qco in cls.QCO_MANDATES:
            matched_pattern = any(re.search(p, std_clean, re.IGNORECASE) for p in qco["patterns"])
            matched_keyword = any(k in combined_text for k in qco["keywords"])
            if matched_pattern or (matched_keyword and ("specification" in combined_text or "standard" in combined_text)):
                return {
                    "is_mandatory": True,
                    "certification_scheme": f"{qco['scheme']} (QCO Enforced)",
                    "mandate_type": "QCO",
                    "governing_order": f"{qco['order']} ({qco['ministry']})",
                    "mandate_reason": f"Mandatory compliance notified under Gazette QCO by {qco['ministry']}. No supplier can sell, manufacture, or import without BIS Standard Mark (ISI mark).",
                    "legal_act": qco["legal_act"]
                }

        # 5. Default Fallback based on text heuristics
        if any(term in combined_text for term in ["method of test", "testing method", "sampling", "code of practice", "general principles"]):
            return {
                "is_mandatory": False,
                "certification_scheme": "Normative Reference / Test Method",
                "mandate_type": "CODE_OF_PRACTICE",
                "governing_order": "None (Normative Reference)",
                "mandate_reason": "Advisory normative testing or sampling procedure referenced in technical specifications.",
                "legal_act": "BIS Act, 2016"
            }

        # Generic product specification without explicit QCO notification
        return {
            "is_mandatory": False,
            "certification_scheme": "Voluntary ISI Scheme-I",
            "mandate_type": "VOLUNTARY",
            "governing_order": "No Mandatory QCO Order",
            "mandate_reason": "Indian Standard product specification under voluntary ISI marking scheme. Mandatory only if specifically mandated in GeM contract terms.",
            "legal_act": "BIS Act, 2016"
        }

    @classmethod
    def evaluate_procurement_compliance(
        cls,
        query: str,
        evaluated_candidates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Synthesizes the overall dynamic compliance profile for Card 5 in the dashboard:
        - BIS Product Certification (ISI Mark)
        - Quality Control Order (QCO)
        - Compulsory Registration Scheme (CRS)
        - Hallmarking
        - Counts of Mandatory vs Voluntary standards
        """
        q_lower = query.lower()

        mandatory_items = [c for c in evaluated_candidates if c.get("is_mandatory")]
        voluntary_items = [c for c in evaluated_candidates if not c.get("is_mandatory")]

        has_qco = any(c.get("mandate_type") == "QCO" for c in evaluated_candidates)
        has_crs = any(c.get("mandate_type") == "CRS" for c in evaluated_candidates)
        has_hallmark = any(c.get("mandate_type") == "HALLMARKING" for c in evaluated_candidates)
        has_gold_hallmark = any(c.get("mandate_type") == "HALLMARKING" and c.get("is_mandatory") for c in evaluated_candidates)
        has_isi_voluntary = any(c.get("mandate_type") == "VOLUNTARY" and "ISI" in c.get("certification_scheme", "") for c in evaluated_candidates)

        # Fallback check on query text if candidate list is small
        if any(kw in q_lower for kw in ["gold", "jewellery", "jewelry", "hallmark", "huid"]):
            has_hallmark = True
            has_gold_hallmark = True
        if any(kw in q_lower for kw in ["solar inverter", "photovoltaic", "laptop", "server", "lithium battery", "led lamp"]):
            has_crs = True
        if any(kw in q_lower for kw in ["cable tray", "cement", "tmt", "steel", "pipe", "fire extinguisher", "cable"]):
            has_qco = True

        # 1. BIS Product Certification Status
        if has_qco:
            bis_product_status = "Mandatory (QCO)"
            bis_product_class = "pill-green"
            bis_product_desc = "Mandatory ISI mark Scheme-I license required under statutory Quality Control Order."
        elif has_isi_voluntary or len(voluntary_items) > 0:
            bis_product_status = "Applicable (Voluntary)"
            bis_product_class = "pill-amber"
            bis_product_desc = "Voluntary BIS Product Certification (ISI Mark) available for quality differentiation."
        else:
            bis_product_status = "Not Applicable"
            bis_product_class = "pill-gray"
            bis_product_desc = "Goods are governed by other schemes (CRS / Hallmarking) or advisory codes."

        # 2. QCO Status
        if has_qco:
            qco_item = next((c for c in evaluated_candidates if c.get("mandate_type") == "QCO"), None)
            order_name = qco_item.get("governing_order") if qco_item else "Central Government Quality Control Order"
            qco_status = "Mandatory QCO Enforced"
            qco_class = "pill-green"
            qco_desc = f"Enforced under {order_name}. Non-certified goods are summarily rejected on GeM."
        else:
            qco_status = "Not Applicable"
            qco_class = "pill-gray"
            qco_desc = "No mandatory Quality Control Order (QCO) currently notified for this category."

        # 3. CRS Status
        if has_crs:
            crs_item = next((c for c in evaluated_candidates if c.get("mandate_type") == "CRS"), None)
            crs_order = crs_item.get("governing_order") if crs_item else "MeitY / MNRE Compulsory Registration Order"
            crs_status = "Mandatory CRS (MeitY/MNRE)"
            crs_class = "pill-green"
            crs_desc = f"Mandatory Self-Declaration of Conformity under {crs_order} (Scheme-II)."
        else:
            crs_status = "Not Applicable"
            crs_class = "pill-gray"
            crs_desc = "Compulsory Registration Scheme applies exclusively to notified IT, electronics, and solar items."

        # 4. Hallmarking Status
        if has_gold_hallmark:
            hallmark_status = "Mandatory (DoCA Order)"
            hallmark_class = "pill-green"
            hallmark_desc = "Mandatory 6-digit HUID Hallmarking required under Central Consumer Protection Order."
        elif has_hallmark:
            hallmark_status = "Applicable (Silver)"
            hallmark_class = "pill-amber"
            hallmark_desc = "Voluntary / Applicable Hallmarking scheme for silver jewellery and artefacts."
        else:
            hallmark_status = "Not Applicable"
            hallmark_class = "pill-gray"
            hallmark_desc = "Hallmarking scheme applies strictly to precious metal articles (Gold & Silver)."

        # Overall recommendation tier
        if len(mandatory_items) > 0 and len(voluntary_items) == 0:
            relevance_tier = "Primary Mandatory Standard"
            score_tier_text = "Mandatory Compliance Required"
        elif len(mandatory_items) > 0 and len(voluntary_items) > 0:
            relevance_tier = "Mandatory & Advisory Standards"
            score_tier_text = "Mandatory & Advisory Standards Identified"
        else:
            relevance_tier = "Voluntary Technical Standard"
            score_tier_text = "Voluntary Quality Standard / Advisory"

        return {
            "bis_product": {
                "status": bis_product_status,
                "badge_class": bis_product_class,
                "description": bis_product_desc
            },
            "qco": {
                "status": qco_status,
                "badge_class": qco_class,
                "description": qco_desc
            },
            "crs": {
                "status": crs_status,
                "badge_class": crs_class,
                "description": crs_desc
            },
            "hallmarking": {
                "status": hallmark_status,
                "badge_class": hallmark_class,
                "description": hallmark_desc
            },
            "mandatory_count": len(mandatory_items),
            "voluntary_count": len(voluntary_items),
            "mandatory_standards": [m.get("standard_number") for m in mandatory_items],
            "voluntary_standards": [v.get("standard_number") for v in voluntary_items],
            "relevance_tier": relevance_tier,
            "score_tier_text": score_tier_text,
            "legal_directive": (
                "Under Sections 16 and 17 of the Bureau of Indian Standards Act, 2016, where a mandatory Quality Control Order (QCO), "
                "CRS notification, or Hallmarking directive is enforced, no person shall manufacture, import, sell, or distribute goods "
                "without the prescribed Standard Mark. Bids on Government e-Marketplace (GeM) failing to provide valid certification licenses "
                "are subject to immediate technical rejection."
            )
        }
