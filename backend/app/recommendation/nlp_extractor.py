import re
from typing import Dict, Any, List, Optional
from backend.app.schemas.standard_schemas import (
    ExtractedEntities,
    SpecificationGapAnalysis,
    SpecificationGapItem
)

class ProcurementNLPExtractor:
    """
    Extracts structured entities, procurement domain, product keywords,
    safety requirements, testing needs, explicit IS numbers, user specifications,
    and conducts procurement intent classification and specification gap detection.
    """

    STOP_WORDS = {
        "procure", "procurement", "purchase", "purchasing", "supply", "supplying", "tender",
        "requirement", "need", "install", "installation", "for", "with", "and", "under",
        "from", "the", "a", "an", "of", "in", "to", "units", "nos", "numbers", "bags",
        "meters", "kg", "tons", "packets", "certified", "standard", "quality", "government"
    }

    SYNONYM_MAP = {
        # Household Appliances & Functional Descriptions
        "machine used to wash clothes": "washing machine clothes washing machine",
        "machine to wash clothes": "washing machine clothes washing machine",
        "machine for washing clothes": "washing machine clothes washing machine",
        "used to wash clothes": "washing machine clothes washing machine",
        "wash clothes": "washing machine clothes washing machine",
        "washing clothes": "washing machine clothes washing machine",
        "cloth washing machine": "washing machine",
        "clothes washing machine": "washing machine",
        "clothes washer": "washing machine",
        "wash machine": "washing machine",
        "water purifier": "drinking water purifier filter",
        "water purification": "drinking water purification",
        "water filter": "drinking water purifier filter",
        "air cooler": "evaporative air cooler",
        "ac": "air conditioner",
        "air con": "air conditioner",
        "fridge": "refrigerator household refrigerator",
        "geyser": "water heater electrical water heater",
        "electric iron": "electric clothes iron",
        "clothes iron": "electric clothes iron",
        "ceiling fan": "electric ceiling fan",
        "home": "house",
        "baby": "children",
        "babies": "children",
        "infants": "children",
        "infant": "children",
        "rich in protein": "protein fortified",
        "protein rich": "protein fortified",
        "protein-rich": "protein fortified",
        "rods": "bars",
        "rod": "bar",
        "steel rods": "steel bars",
        "tubes": "pipes",
        "tube": "pipe",
        "pv": "photovoltaic",
        "solar panels": "solar photovoltaic panel",
        "solar panel": "solar photovoltaic panel",
        "electric wire": "electric cable wire",
        "electrical wire": "electric cable wire",
        "electrical wiring": "electric cable wiring",
        "wiring": "wiring cable",
        "extinguisher": "fire extinguisher",
        "light luminaire": "street light luminaire",
        "portable computer": "laptop",
        "portable computers": "laptop",
        "notebook computer": "laptop",
        "notebooks": "laptop",
        "gold biscuit": "gold bullion bar refined gold bar",
        "gold biscuits": "gold bullion bars refined gold bars",
        "silver biscuit": "silver bullion bar refined silver bar",
        "silver biscuits": "silver bullion bars refined silver bars"
    }

    DOMAIN_MAPPINGS = {
        "Precious Metals and Hallmarking": [
            "gold", "silver", "bullion", "hallmark", "hallmarking", "jewellery", "jewelry",
            "precious metal", "carat", "karat", "gold bar", "gold biscuit", "gold bullion",
            "fineness", "assay", "cupellation", "gold coin", "ingot", "refinery"
        ],
        "Food and Agriculture": [
            "bread", "biscuit", "biscuits", "protein", "fortified", "wheat", "maida", "flour",
            "milk", "sugar", "food", "edible", "snack", "bakery", "atta", "tea", "coffee",
            "rice", "spice", "salt", "oil", "supplement", "agricultural"
        ],
        "Electrotechnical": [
            "solar", "inverter", "pcu", "photovoltaic", "pv", "cable", "wire", "transformer",
            "switchgear", "led", "lamp", "battery", "ups", "generator", "motor", "meter",
            "wiring", "luminaire", "house", "washing machine", "refrigerator", "appliance",
            "appliances", "water heater", "air conditioner", "fan", "iron", "electrical",
            "vacuum cleaner", "toaster", "microwave", "domestic electric"
        ],
        "Civil Engineering": [
            "cement", "portland", "concrete", "steel", "tmt", "rebar", "bar", "bars", "rod",
            "rods", "brick", "aggregate", "pipe", "hdpe", "pvc pipe", "structural steel",
            "tiles", "water meter", "sanitary", "glaze"
        ],
        "Electronics and Information Technology": [
            "computer", "computers", "laptop", "laptops", "server", "servers", "software",
            "biometric", "cctv", "monitor", "router", "telecom", "printer", "notebook",
            "communication", "display", "storage"
        ],
        "Mechanical Engineering": [
            "fire extinguisher", "pump", "valve", "engine", "compressor", "crane", "cylinder",
            "bearing", "extinguisher", "oxygen cylinder", "centrifuge", "machinery", "machine"
        ],
        "Personal Protective Equipment & Safety": [
            "mask", "n95", "helmet", "safety shoe", "safety shoes", "footwear", "gloves",
            "goggles", "ppe kit", "protective"
        ],
        "Textiles": [
            "textile", "textiles", "fabric", "cloth", "clothes", "cotton", "wool", "yarn",
            "flannel", "blanket", "colour fastness"
        ]
    }

    PRODUCT_STANDARD_PARAMETERS = {
        "washing machine": [
            {"parameter": "Rated Wash & Spin Capacity (kg)", "recommendation": "Specify nominal dry linen wash load capacity (e.g., 7.0 kg, 8.5 kg, or 10.0 kg).", "risk": "High"},
            {"parameter": "Loading Architecture & Tub Configuration", "recommendation": "Specify Top Load Fully-Automatic, Front Load Fully-Automatic, or Semi-Automatic twin tub.", "risk": "High"},
            {"parameter": "Electrical Safety & Moisture Ingress Conformance", "recommendation": "Mandatory conformity to IS 302 (Part 2 : Sec 7) with IPX4 water splash protection.", "risk": "High"},
            {"parameter": "Energy Efficiency & Water Benchmark (BEE Star)", "recommendation": "Specify BEE 5-Star efficiency rating and maximum water consumption (<= 9 litres/kg/cycle).", "risk": "Moderate"},
            {"parameter": "Motor Drive Technology & Spin Speed", "recommendation": "Specify Direct Drive Inverter BLDC motor and maximum rotational spin speed (>= 1200 RPM).", "risk": "Moderate"},
            {"parameter": "In-built Heater & Temperature Cycles", "recommendation": "Specify in-built heating element with variable thermal wash settings (up to 60°C/90°C).", "risk": "Low"},
            {"parameter": "Statutory QCO Compliance & Standard Mark", "recommendation": "Mandatory valid BIS ISI Mark under Central Electrical Appliances Quality Control Order.", "risk": "High"}
        ],
        "refrigerator": [
            {"parameter": "Storage Capacity & Compartment Volume (Litres)", "recommendation": "Specify gross and net storage volume (e.g. 240L, 350L, 500L) and freezer ratio.", "risk": "High"},
            {"parameter": "Defrost & Door Architecture", "recommendation": "Specify Frost-Free or Direct Cool, and Single Door / Double Door / Side-by-Side layout.", "risk": "High"},
            {"parameter": "BEE Star Energy Rating & Eco Refrigerant", "recommendation": "Specify minimum BEE 4 or 5-Star energy label with eco-friendly R600a refrigerant.", "risk": "High"},
            {"parameter": "Electrical Safety Conformance", "recommendation": "Conformity to IS 302 (Part 2 : Sec 24) and IS 1751 under Household Appliances Safety Order.", "risk": "High"}
        ],
        "air conditioner": [
            {"parameter": "Cooling Capacity (Tonnage / Watts)", "recommendation": "Specify nominal cooling capacity (e.g. 1.0 Ton / 3500W, 1.5 Ton / 5200W).", "risk": "High"},
            {"parameter": "Compressor & Inverter Technology", "recommendation": "Specify Variable Speed Inverter Rotary Compressor with 100% copper condenser tubes.", "risk": "High"},
            {"parameter": "ISEER Energy Rating & BEE Star", "recommendation": "Specify minimum ISEER rating >= 4.5 conforming to BEE 5-Star efficiency benchmarks.", "risk": "Moderate"},
            {"parameter": "Safety & Performance Standards", "recommendation": "Mandatory conformity to IS 1391 (Part 1/2) and IS/IEC 60335-2-40 under statutory QCO.", "risk": "High"}
        ],
        "water purifier": [
            {"parameter": "Purification Technology & Stages", "recommendation": "Specify multi-stage RO + UV + UF + Mineraliser technology as per feed water TDS level.", "risk": "High"},
            {"parameter": "Recovery Rate & Water Wastage", "recommendation": "Specify high recovery membrane with minimum 50% clean water recovery benchmark.", "risk": "Moderate"},
            {"parameter": "Microbiological & Chemical Safety", "recommendation": "Treated water must strictly conform to drinking water standard IS 10500.", "risk": "High"}
        ],
        "laptop": [
            {"parameter": "Processor", "recommendation": "Specify processor architecture, generation and clock speed (e.g., minimum multi-core processor benchmark).", "risk": "High"},
            {"parameter": "RAM (Memory)", "recommendation": "Specify required RAM capacity, memory type and expandable capacity.", "risk": "High"},
            {"parameter": "Storage", "recommendation": "Specify solid-state storage (SSD) capacity and interface (e.g., PCIe NVMe).", "risk": "High"},
            {"parameter": "Display", "recommendation": "Specify screen diagonal size, resolution (e.g., FHD 1920x1080) and anti-glare finish.", "risk": "Moderate"},
            {"parameter": "Battery & Power", "recommendation": "Specify required battery operating backup hours and power adapter rating.", "risk": "Moderate"},
            {"parameter": "Operating System", "recommendation": "Specify pre-loaded operating system version and OEM license type.", "risk": "Moderate"},
            {"parameter": "Connectivity & I/O Ports", "recommendation": "Specify required wireless standards (Wi-Fi 6, Bluetooth) and physical ports (USB-C, HDMI).", "risk": "Low"},
            {"parameter": "Warranty & AMC", "recommendation": "Specify comprehensive OEM on-site warranty duration (e.g., 3-year on-site).", "risk": "Moderate"},
            {"parameter": "Electrical Safety & Energy Conformity", "recommendation": "Conformity to IS 13252 (Part 1) / IEC 60950-1 and BEE Star energy efficiency requirements.", "risk": "High"}
        ],
        "solar": [
            {"parameter": "Solar PV Cell Technology", "recommendation": "Specify Mono-crystalline / Poly-crystalline cell technology and module efficiency (> 20%).", "risk": "High"},
            {"parameter": "Power Capacity (Wp / kW)", "recommendation": "Specify rated peak output wattage (Wp) and total system capacity.", "risk": "High"},
            {"parameter": "Inverter & Grid Protection", "recommendation": "Specify inverter topology, anti-islanding trip limits (< 2.0s), and THD (< 5%).", "risk": "High"},
            {"parameter": "Mechanical Load & Weather Resistance", "recommendation": "Specify wind/snow load tolerance (minimum 2400 Pa) and IP65/IP67 ingress protection.", "risk": "Moderate"},
            {"parameter": "Safety & BIS Mandate", "recommendation": "Mandatory conformity to IS 14286 / IS 16221 / IS 16169 under MNRE QCO.", "risk": "High"}
        ],
        "cable": [
            {"parameter": "Conductor Material & Grade", "recommendation": "Specify conductor material (EC-grade Copper or Aluminium) and purity standards.", "risk": "High"},
            {"parameter": "Voltage Rating", "recommendation": "Specify system operating voltage grade (e.g., 1.1 kV or 11 kV / 33 kV).", "risk": "High"},
            {"parameter": "Insulation & Sheathing", "recommendation": "Specify insulation compound (XLPE / PVC) and flame retardant low smoke (FRLS) property.", "risk": "High"},
            {"parameter": "Armouring & Mechanical Protection", "recommendation": "Specify galvanized steel wire/strip armouring for underground/industrial runs.", "risk": "Moderate"},
            {"parameter": "Testing & Conformance", "recommendation": "Routine and type testing as per IS 7098 / IS 1554 with ISI mark.", "risk": "High"}
        ],
        "cement": [
            {"parameter": "Cement Grade & Type", "recommendation": "Specify standard grade (e.g., OPC 43, OPC 53, or PPC) as per structural design.", "risk": "High"},
            {"parameter": "Compressive Strength Benchmarks", "recommendation": "Specify minimum 3-day, 7-day, and 28-day compressive strength limits.", "risk": "High"},
            {"parameter": "Setting Time", "recommendation": "Specify initial setting time (>= 30 mins) and final setting time (<= 600 mins).", "risk": "High"},
            {"parameter": "Soundness & Chemical Purity", "recommendation": "Specify autoclave expansion and Le-Chatelier soundness limits.", "risk": "Moderate"},
            {"parameter": "Packaging & ISI Certification", "recommendation": "Mandatory ISI mark on tamper-proof bags conforming to IS 269 / IS 1489.", "risk": "High"}
        ],
        "fire extinguisher": [
            {"parameter": "Extinguisher Agent & Type", "recommendation": "Specify agent type (ABC Dry Powder, CO2, Mechanical Foam, or Water-CO2).", "risk": "High"},
            {"parameter": "Nominal Charge Capacity", "recommendation": "Specify capacity (e.g., 2 kg, 4 kg, 6 kg, or 9 litres).", "risk": "High"},
            {"parameter": "Fire Rating Classification", "recommendation": "Specify fire rating suitability (e.g., 21A, 55B) as per hazard class.", "risk": "High"},
            {"parameter": "Operating Pressure & Discharge Time", "recommendation": "Specify working pressure, test pressure, and minimum effective discharge duration.", "risk": "Moderate"},
            {"parameter": "BIS Quality Control Order Mandate", "recommendation": "Mandatory conformity to IS 15683 with valid ISI Mark License.", "risk": "High"}
        ],
        "gold": [
            {"parameter": "Purity & Fineness (Carat / Millesimal)", "recommendation": "Specify gold fineness (e.g., 999.9, 999.0, 995.0 for bullion bars as per IS 17278, or 24K, 22K (916), 18K (750) as per IS 1417).", "risk": "High"},
            {"parameter": "Bar Form & Weight Denomination", "recommendation": "Specify weight denomination (e.g., 10g, 50g, 100g, 1000g / 1 kg bar) and serial numbering requirements.", "risk": "High"},
            {"parameter": "BIS Hallmarking & HUID", "recommendation": "Mandatory BIS Hallmarking with 6-digit Hallmark Unique Identification (HUID) and assay mark conforming to IS 1417.", "risk": "High"},
            {"parameter": "Assay & Testing Method", "recommendation": "Conformity to Cupellation (Fire Assay) method in accordance with IS 1418.", "risk": "Moderate"},
            {"parameter": "Certification & Tamper-Evident Packaging", "recommendation": "Certified tamper-evident packaging and assay certificate from BIS-recognized refinery/hallmarking center.", "risk": "High"}
        ]
    }

    CONVERSATIONAL_PATTERNS = [
        r"^(?:hello|hi|hey|greetings|howdy)\b",
        r"\bgood\s+(?:morning|afternoon|evening|night|day)\b",
        r"\bhow are you\b", r"\btell me a joke\b", r"\bjoke\b", r"\bweather\b",
        r"\bwhat is the weather\b", r"\bwho won\b", r"\bwho is\b", r"\bwho are you\b",
        r"\bwhat are you\b", r"\bcricket match\b", r"\bfootball match\b", r"\bi like\b",
        r"\bwhat do you think\b", r"\bwrite a poem\b", r"\bwho created you\b",
        r"\bhuman\s+error\b", r"\bsystem\s+error\b", r"^(?:error|mistake|blunder|bug)\b",
        r"\b(?:thank\s*you|thanks|thx)\b", r"\b(?:bye|goodbye|see you)\b",
        r"\bwhat('s| is) (?:up|this|that|your name|life|love)\b",
        r"^(?:test|testing|sample|check|asdf|qwerty)\b"
    ]

    @classmethod
    def classify_procurement_intent(cls, text: str) -> Dict[str, Any]:
        """
        Validates if user input represents a genuine technical or procurement requirement.
        Intelligently understands functional descriptions (e.g. 'machine used to wash clothes').
        Strictly rejects conversational phrases, non-procurement queries, greetings, and random input.
        """
        raw = text.strip()
        lower = raw.lower()

        if len(raw) < 3:
            return {"is_valid": False, "reason": "Input is too short to be a procurement requirement."}

        # Check for conversational / useless phrases
        for pat in cls.CONVERSATIONAL_PATTERNS:
            if re.search(pat, lower):
                return {"is_valid": False, "reason": "Non-procurement conversational or general query detected."}

        # Check for keyboard mash / gibberish (6 or more consecutive consonants)
        if re.search(r'[bcdfghjklmnpqrstvwxz]{6,}', lower):
            return {"is_valid": False, "reason": "Input appears to be random or unreadable characters."}

        words = re.findall(r'[a-zA-Z0-9]+', lower)
        if not words:
            return {"is_valid": False, "reason": "Input contains no meaningful textual terms."}

        # Check for technical / product / procurement signals
        procurement_verbs = ["need", "procure", "purchase", "supply", "require", "requirement", "tender", "install", "buy", "bid", "quote"]
        technical_units = ["gb", "ram", "ssd", "hdd", "nvme", "pcie", "tb", "inch", "watt", "wp", "kw", "mw", "volt", "kv", "amp", "hz", "mm", "cm", "kg", "ton", "litre", "bar", "mpa", "core", "ghz", "rpm"]

        # Functional indicators: any machine, appliance, tool, equipment, material, process, device
        functional_indicators = [
            "machine", "appliance", "device", "equipment", "tool", "instrument",
            "wash", "clean", "filter", "purif", "heat", "cool", "pump", "measure", "cut", "weld",
            "cloth", "clothes", "water", "air", "electric", "power", "solar", "steel",
            "cement", "cable", "wire", "pipe", "tube", "valve", "light", "panel", "tank",
            "motor", "engine", "fan", "iron", "cooler", "fridge", "purifier", "refrigerator",
            "textile", "extinguisher", "switchgear", "generator", "transformer"
        ]

        has_is_code = bool(re.search(r'\bis\s*[:\-]?\s*\d+', lower))
        has_unit = any(re.search(r'\b' + re.escape(u) + r'\b', lower) for u in technical_units)
        has_procure_verb = any(v in lower for v in procurement_verbs)
        has_functional_indicator = any(re.search(r'\b' + re.escape(ind) + r'\b', lower) for ind in functional_indicators)
        has_domain_word = any(
            any(re.search(r'\b' + re.escape(kw) + r'\b', lower) for kw in kws)
            for kws in cls.DOMAIN_MAPPINGS.values()
        )

        common_products = [
            "laptop", "computer", "pc", "server", "cable", "wire", "cement", "steel",
            "tray", "pipe", "tube", "inverter", "solar", "panel", "pump", "valve",
            "transformer", "extinguisher", "mask", "helmet", "shoe", "switchgear",
            "generator", "battery", "ups", "printer", "router", "camera", "sensor",
            "light", "luminaire", "meter", "biscuit", "food", "flour", "rebar", "concrete",
            "surgical", "instrument", "gold", "silver", "bullion", "hallmark", "gold bar",
            "gold biscuit", "jewellery", "jewelry", "washing machine", "refrigerator",
            "air conditioner", "water purifier", "fan", "iron", "heater"
        ]
        has_product = any(re.search(r'\b' + re.escape(p) + r'\b', lower) for p in common_products)

        # Allow query if it has IS code, known product, domain word, functional description, or procurement context
        if has_is_code or has_product or has_domain_word or has_functional_indicator or (has_procure_verb and (has_unit or len(words) >= 2)):
            return {"is_valid": True, "reason": "Valid procurement or technical specification."}

        # Otherwise, reject general non-procurement phrases
        return {"is_valid": False, "reason": "No technical product or procurement context identified."}


    @classmethod
    def extract_user_specifications(cls, text: str) -> Dict[str, str]:
        """
        Extracts explicit technical parameters provided by the user in the prompt.
        """
        specs = {}
        cleaned = text.strip()

        # Processor
        proc_match = re.search(r'(intel\s+core\s+[iI]\d+|amd\s+ryzen\s+\d+|core\s+[iI]\d+|[iI]\d+\s+processor|octa[- ]core|quad[- ]core|snapdragon\s+\d+)', cleaned, re.IGNORECASE)
        if proc_match:
            specs["Processor"] = proc_match.group(1).strip()

        # RAM
        ram_match = re.search(r'(\d+\s*GB\s*(?:DDR\d+)?\s*RAM|\d+\s*GB\s+memory)', cleaned, re.IGNORECASE)
        if ram_match:
            specs["RAM (Memory)"] = ram_match.group(1).strip()

        # Storage
        storage_match = re.search(r'(\d+\s*(?:GB|TB)\s*(?:SSD|HDD|NVMe|PCIe))', cleaned, re.IGNORECASE)
        if storage_match:
            specs["Storage"] = storage_match.group(1).strip()

        # Display
        disp_match = re.search(r'(\d+(?:\.\d+)?\s*[- ]?(?:inch|\")\s*(?:display|screen|FHD|UHD|OLED|LED)?)', cleaned, re.IGNORECASE)
        if disp_match:
            specs["Display"] = disp_match.group(1).strip()

        # Battery
        bat_match = re.search(r'(\d+(?:\.\d+)?\s*[- ]?(?:hour|hr|mAh|Wh)\s*(?:battery|backup)?)', cleaned, re.IGNORECASE)
        if bat_match:
            specs["Battery & Power"] = bat_match.group(1).strip()

        # Warranty
        war_match = re.search(r'(\d+\s*[- ]?(?:year|yr)\s*warranty)', cleaned, re.IGNORECASE)
        if war_match:
            specs["Warranty & AMC"] = war_match.group(1).strip()

        # Operating System
        os_match = re.search(r'(windows\s*1[01]|linux|ubuntu|macOS)', cleaned, re.IGNORECASE)
        if os_match:
            specs["Operating System"] = os_match.group(1).strip()

        # Dimensions / Gauge / Size
        dim_match = re.search(r'(\d+(?:\.\d+)?\s*(?:mm|cm|meters|m|inch)\s*(?:thick|thickness|diameter|dia|width|length)?)', cleaned, re.IGNORECASE)
        if dim_match and "Display" not in specs:
            specs["Dimensions & Sizing"] = dim_match.group(1).strip()

        # Material / Grade
        mat_match = re.search(r'(stainless\s+steel|ss\s*304|ss\s*316|galvanized\s+iron|fe\s*500[dD]?|fe\s*550|opc\s*43|opc\s*53|ppc|grade\s*\d+)', cleaned, re.IGNORECASE)
        if mat_match:
            specs["Material Grade"] = mat_match.group(1).strip()

        # Electrical / Power Rating
        elec_match = re.search(r'(\d+(?:\.\d+)?\s*(?:kw|kva|w|wp|mw|volt|v|kv|amp|ah))', cleaned, re.IGNORECASE)
        if elec_match and "RAM (Memory)" not in specs:
            specs["Electrical Power Rating"] = elec_match.group(1).strip()

        return specs

    @classmethod
    def detect_specification_gaps(
        cls,
        product_category: Optional[str],
        user_specs: Dict[str, str],
        domain: Optional[str] = None
    ) -> SpecificationGapAnalysis:
        """
        Compares user-provided specifications against the standard parameters
        for the identified product class, surfacing missing/recommended details.
        """
        prod_key = (product_category or "").lower()
        matched_catalog = None

        for k, params in cls.PRODUCT_STANDARD_PARAMETERS.items():
            if k in prod_key:
                matched_catalog = params
                break

        # Fallback general engineering parameters if product not in catalog
        if not matched_catalog:
            matched_catalog = [
                {"parameter": "Material Composition & Grade", "recommendation": "Specify raw material chemical purity and designated grade."},
                {"parameter": "Dimensional Tolerances & Sizing", "recommendation": "Specify nominal dimensions, wall thickness, and permissible tolerances."},
                {"parameter": "Operating Conditions & Environment", "recommendation": "Specify intended working temperature, pressure, and ambient exposure conditions."},
                {"parameter": "Sampling & Factory Acceptance Test", "recommendation": "Specify batch sampling plan and third-party inspection requirements."},
                {"parameter": "Mandatory BIS Certification / QCO", "recommendation": "Require valid Bureau of Indian Standards License and Standard Mark."}
            ]

        gap_items = []
        missing_count = 0
        provided_count = 0
        missing_list = []

        for item in matched_catalog:
            param_name = item["parameter"]
            risk_lvl = item.get("risk", "Moderate")
            # Check if user provided this param
            provided_val = None
            for u_k, u_v in user_specs.items():
                if u_k.lower() in param_name.lower() or param_name.lower() in u_k.lower():
                    provided_val = u_v
                    break

            if provided_val:
                gap_items.append(SpecificationGapItem(
                    parameter=param_name,
                    user_provided=provided_val,
                    status="PROVIDED",
                    recommendation="Parameter explicitly provided in procurement requirement.",
                    risk_level="Conformant"
                ))
                provided_count += 1
            else:
                gap_items.append(SpecificationGapItem(
                    parameter=param_name,
                    user_provided=None,
                    status="MISSING",
                    recommendation=item["recommendation"],
                    risk_level=risk_lvl
                ))
                missing_count += 1
                missing_list.append(param_name)

        is_complete = provided_count >= 5 or (len(matched_catalog) > 0 and missing_count <= 2)

        if not is_complete:
            summary = "Additional detailed specifications are recommended. Specifying the missing technical parameters will prevent vendor ambiguity and technical bid disputes."
        else:
            if missing_list:
                summary = "Your requirement contains several key technical specifications. Based on the applicable standard information available to StandIQ, the remaining details should also be considered."
            else:
                summary = "Your requirement contains the key specifications identified from the available applicable standard information."

        return SpecificationGapAnalysis(
            product_identified=product_category,
            is_complete=is_complete,
            completeness_summary=summary,
            user_specifications=user_specs,
            missing_specifications=missing_list,
            gap_matrix=gap_items
        )

    @classmethod
    def canonicalize_query(cls, text: str) -> str:
        if not text:
            return ""
        res = text.lower()
        for phrase, canonical in sorted(cls.SYNONYM_MAP.items(), key=lambda x: -len(x[0])):
            res = re.sub(r'\b' + re.escape(phrase) + r'\b', canonical, res)
        return res

    @classmethod
    def extract_entities(cls, text: str) -> ExtractedEntities:
        cleaned = text.strip()
        lower = cls.canonicalize_query(cleaned)

        # 1. Detect explicit IS numbers (e.g. IS 1011, IS 16221, IS:456, IS-269)
        detected_is = re.findall(r'IS\s*[:\-]?\s*(\d+(?:\s*(?:\(Part\s*\d+\)|Part\s*\d+))?)', cleaned, re.IGNORECASE)
        normalized_is = [f"IS {num.strip()}" for num in detected_is]

        # 2. Extract Quantity
        qty_match = re.search(r'(\d+(?:,\d+)?(?:\s*(?:nos|numbers|units|kg|tons|metric tons|litres|meters|km|kw|mw|wp|bags|packets))?)', cleaned, re.IGNORECASE)
        quantity = qty_match.group(1).strip() if qty_match else None

        # 3. Detect Domain with Polysemy & Semantic Disambiguation
        detected_domain = None
        domain_scores = {}
        for domain, keywords in cls.DOMAIN_MAPPINGS.items():
            score = sum(1 for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', lower))
            if score > 0:
                domain_scores[domain] = score

        # Explicit Polysemy Disambiguation:
        # If query mentions gold, silver, bullion, or hallmarking, it is NEVER Food and Agriculture
        is_precious = any(re.search(r'\b' + re.escape(w) + r'\b', lower) for w in ["gold", "silver", "bullion", "hallmark", "hallmarking", "carat", "karat", "fire assay", "jewellery", "jewelry"])
        if is_precious:
            domain_scores.pop("Food and Agriculture", None)
            domain_scores["Precious Metals and Hallmarking"] = domain_scores.get("Precious Metals and Hallmarking", 0) + 10

        if domain_scores:
            detected_domain = max(domain_scores, key=domain_scores.get)

        # 4. Extract Product Category
        product_category = None
        matched_kws = []
        target_domains = [detected_domain] if detected_domain and detected_domain in cls.DOMAIN_MAPPINGS else list(cls.DOMAIN_MAPPINGS.keys())
        for dom in target_domains:
            for kw in cls.DOMAIN_MAPPINGS[dom]:
                if re.search(r'\b' + re.escape(kw) + r'\b', lower):
                    matched_kws.append(kw)

        if matched_kws:
            product_category = max(matched_kws, key=len).title()
        else:
            tokens = [w for w in re.findall(r'[a-zA-Z]+', lower) if w not in cls.STOP_WORDS and len(w) > 2]
            if tokens:
                product_category = " ".join(tokens[:2]).title()

        safety_critical = any(w in lower for w in ["safety", "hazard", "fire", "shock", "safe", "protective", "hygiene", "toxic", "medical", "protection"])
        testing_required = any(w in lower for w in ["test", "testing", "sampling", "inspection", "acceptance", "quality check", "lab test", "certification", "conformance"])

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

