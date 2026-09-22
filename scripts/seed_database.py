import os
import sys
import datetime

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.database.connection import Base, engine, SessionLocal
from backend.app.database.models import Standard, StandardReference, Amendment, Classification, SafetyTestingMetadata, IngestionLog
from backend.app.ingestion.pipeline import IngestionPipeline

SEED_STANDARDS = [
    # --- FOOD & AGRICULTURE ---
    {
        "standard_number": "IS 1011",
        "title": "Biscuits - Specification",
        "publication_year": 2002,
        "reaffirmed_year": 2019,
        "ics_code": "67.060",
        "committee_code": "FAD 24",
        "domain": "Food and Agriculture",
        "status": "Reaffirmed (2019)",
        "is_mandatory": False,
        "certification_scheme": "Voluntary ISI Scheme-I",
        "scope": "This standard prescribes the requirements, methods of sampling and test for biscuits baked from dough containing essential ingredients with or without the addition of optional ingredients.",
        "preview_url": "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=1011_2002_reff2019",
        "source_url": "https://standardsbis.bsbedge.com/BIS_searchstandard.aspx?Standard_Number=IS+1011&id=1012",
        "references": [
            {"standard_number": "IS 253", "year": 1985, "title": "Edible common salt", "reference_type": "raw_material"},
            {"standard_number": "IS 498", "year": 1985, "title": "Grading for vacuum pan sugar (plantation white)", "reference_type": "raw_material"},
            {"standard_number": "IS 7463", "year": 1988, "title": "Wheat flour (MAIDA) for use by biscuit industry", "reference_type": "raw_material"},
            {"standard_number": "IS 10634", "year": 1986, "title": "Bakery shortening", "reference_type": "raw_material"},
            {"standard_number": "IS 1159", "year": 1981, "title": "Baking powder", "reference_type": "raw_material"},
            {"standard_number": "IS 12741", "year": 1989, "title": "Bakery products - Sampling", "reference_type": "sampling"},
            {"standard_number": "IS 5059", "year": 1969, "title": "Code for hygienic conditions for large scale biscuit manufacturing units and bakery units", "reference_type": "safety"}
        ],
        "amendments": [
            {"amendment_number": "Amd 1", "amendment_year": 2006, "title": "Amendment No. 1 to IS 1011", "status": "Active"},
            {"amendment_number": "Amd 2", "amendment_year": 2012, "title": "Amendment No. 2 to IS 1011 (Fortification requirements)", "status": "Active"}
        ],
        "safety_testing": {
            "is_safety_related": True,
            "is_testing_related": True,
            "is_sampling_related": True,
            "is_quality_spec": True,
            "safety_justification": "Prescribes limits on moisture, acid insoluble ash, acidity of extracted fat, and microbiological safety requirements.",
            "testing_methods_summary": "Includes determination of moisture, total ash, fat, acidity of extracted fat, and rancidity tests."
        }
    },
    {
        "standard_number": "IS 5059",
        "title": "Code for Hygienic Conditions for Large Scale Biscuit Manufacturing Units and Bakery Units",
        "publication_year": 1969,
        "reaffirmed_year": 2018,
        "ics_code": "67.020",
        "committee_code": "FAD 15",
        "domain": "Food and Agriculture",
        "status": "Reaffirmed (2018)",
        "is_mandatory": False,
        "certification_scheme": "Code of Practice / Design Standard",
        "scope": "This code prescribes the hygienic conditions required for establishing and maintaining large scale biscuit manufacturing and commercial bakery processing units.",
        "preview_url": "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=5059",
        "source_url": "https://standardsbis.bsbedge.com/BIS_searchstandard.aspx?keyword=5059&id=0",
        "references": [
            {"standard_number": "IS 4251", "year": 1967, "title": "Quality tolerances for water for processed food industry", "reference_type": "safety"}
        ],
        "safety_testing": {
            "is_safety_related": True,
            "is_testing_related": False,
            "is_sampling_related": False,
            "is_quality_spec": False,
            "safety_justification": "Mandatory hygiene, sanitation, pest control, and food handler medical clearance protocol.",
            "testing_methods_summary": "Plant inspection and hygienic audit protocols."
        }
    },
    {
        "standard_number": "IS 7463",
        "title": "Wheat Flour (MAIDA) for use by Biscuit Industry - Specification",
        "publication_year": 1988,
        "reaffirmed_year": 2020,
        "ics_code": "67.060",
        "committee_code": "FAD 24",
        "domain": "Food and Agriculture",
        "status": "Reaffirmed (2020)",
        "is_mandatory": False,
        "scope": "Prescribes requirements and methods of sampling and test for wheat flour (maida) specially suited for manufacture of biscuits.",
        "preview_url": "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=7463",
        "source_url": "https://standardsbis.bsbedge.com/BIS_searchstandard.aspx?keyword=7463&id=0",
        "references": [
            {"standard_number": "IS 1155", "year": 1968, "title": "Wheat ATTA", "reference_type": "normative"}
        ],
        "safety_testing": {
            "is_safety_related": False,
            "is_testing_related": True,
            "is_sampling_related": True,
            "is_quality_spec": True,
            "safety_justification": "Limits on moisture content and freedom from rodent contamination and insect infestation.",
            "testing_methods_summary": "Gluten content testing, sedimentation value, ash content determination."
        }
    },
    {
        "standard_number": "IS 1165",
        "title": "Milk Powder - Specification",
        "publication_year": 1992,
        "reaffirmed_year": 2019,
        "ics_code": "67.100.10",
        "committee_code": "FAD 19",
        "domain": "Food and Agriculture",
        "status": "Reaffirmed (2019)",
        "is_mandatory": True,
        "scope": "Prescribes requirements and methods of sampling and test for whole milk powder and skim milk powder.",
        "preview_url": "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=1165",
        "source_url": "https://standardsbis.bsbedge.com/BIS_searchstandard.aspx?keyword=1165&id=0",
        "references": [
            {"standard_number": "IS 1166", "year": 1986, "title": "Condensed milk, partly skimmed and skimmed condensed milk", "reference_type": "normative"}
        ],
        "safety_testing": {
            "is_safety_related": True,
            "is_testing_related": True,
            "is_sampling_related": True,
            "is_quality_spec": True,
            "safety_justification": "Microbiological safety limits for bacterial count, coliforms, and absence of pathogenic Salmonella/Listeria.",
            "testing_methods_summary": "Moisture, milk fat, milk protein, titratable acidity, and solubility index testing."
        }
    },

    # --- ELECTROTECHNICAL & SOLAR ENERGY ---
    {
        "standard_number": "IS 16221 (Part 1)",
        "title": "Safety of Power Converters for use in Photovoltaic Power Systems - Part 1: General Requirements",
        "publication_year": 2016,
        "reaffirmed_year": 2021,
        "ics_code": "27.160",
        "committee_code": "ETD 28",
        "domain": "Electrotechnical",
        "status": "Reaffirmed (2021)",
        "is_mandatory": True,
        "scope": "Applies to power conversion equipment (PCE) for use in Photovoltaic (PV) systems where a uniform technical level with respect to safety is necessary. Defines requirements for protection against electric shock, energy hazards, fire, and mechanical hazards.",
        "preview_url": "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=16221_1",
        "source_url": "https://standardsbis.bsbedge.com/BIS_searchstandard.aspx?keyword=16221&id=0",
        "references": [
            {"standard_number": "IS 16221 (Part 2)", "year": 2016, "title": "Safety of Power Converters for use in Photovoltaic Power Systems - Particular Requirements for Inverters", "reference_type": "safety"},
            {"standard_number": "IS 61683", "year": 2000, "title": "Photovoltaic Systems - Power Conditioners - Procedure for Measuring Efficiency", "reference_type": "testing"},
            {"standard_number": "IS 302 (Part 1)", "year": 2008, "title": "Safety of Household and Similar Electrical Appliances", "reference_type": "safety"}
        ],
        "safety_testing": {
            "is_safety_related": True,
            "is_testing_related": True,
            "is_sampling_related": False,
            "is_quality_spec": True,
            "safety_justification": "Mandatory solar inverter safety against electric shock, earth leakage fault protection, thermal runaway, and short circuit.",
            "testing_methods_summary": "Dielectric withstand test, impulse voltage test, fault condition testing, temperature rise test."
        }
    },
    {
        "standard_number": "IS 16221 (Part 2)",
        "title": "Safety of Power Converters for use in Photovoltaic Power Systems - Part 2: Particular Requirements for Inverters",
        "publication_year": 2016,
        "reaffirmed_year": 2021,
        "ics_code": "27.160",
        "committee_code": "ETD 28",
        "domain": "Electrotechnical",
        "status": "Reaffirmed (2021)",
        "is_mandatory": True,
        "scope": "Provides particular safety requirements for grid-connected and stand-alone utility-interactive inverters for grid support, anti-islanding protection, and fault isolation in solar photovoltaic installations.",
        "preview_url": "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=16221_2",
        "source_url": "https://standardsbis.bsbedge.com/BIS_searchstandard.aspx?keyword=16221&id=0",
        "references": [
            {"standard_number": "IS 16221 (Part 1)", "year": 2016, "title": "Safety of Power Converters for use in Photovoltaic Power Systems - Part 1", "reference_type": "safety"},
            {"standard_number": "IS 61727", "year": 2004, "title": "Photovoltaic (PV) systems - Characteristics of the utility interface", "reference_type": "normative"}
        ],
        "safety_testing": {
            "is_safety_related": True,
            "is_testing_related": True,
            "is_sampling_related": False,
            "is_quality_spec": True,
            "safety_justification": "Mandatory anti-islanding test protection, grid synchronization limits, DC injection prevention.",
            "testing_methods_summary": "Anti-islanding disconnection time verification, over-voltage/under-voltage tripping tests, total harmonic distortion (THD) limits."
        }
    },
    {
        "standard_number": "IS 16102 (Part 1)",
        "title": "Self-Ballasted LED Lamps for General Lighting Services - Part 1: Safety Requirements",
        "publication_year": 2012,
        "reaffirmed_year": 2022,
        "ics_code": "29.140.99",
        "committee_code": "ETD 23",
        "domain": "Electrotechnical",
        "status": "Reaffirmed (2022)",
        "is_mandatory": True,
        "scope": "Specifies the safety and interchangeability requirements, together with the test methods and conditions required to show compliance of LED lamps with integrated means for controlling supply.",
        "preview_url": "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=16102_1",
        "source_url": "https://standardsbis.bsbedge.com/BIS_searchstandard.aspx?keyword=16102&id=0",
        "references": [
            {"standard_number": "IS 16102 (Part 2)", "year": 2012, "title": "Self-Ballasted LED Lamps for General Lighting Services - Part 2: Performance Requirements", "reference_type": "normative"},
            {"standard_number": "IS 302 (Part 1)", "year": 2008, "title": "General Electrical Safety", "reference_type": "safety"}
        ],
        "safety_testing": {
            "is_safety_related": True,
            "is_testing_related": True,
            "is_sampling_related": False,
            "is_quality_spec": True,
            "safety_justification": "Protection against electric shock, insulation resistance, mechanical strength of lamp caps, resistance to heat and fire.",
            "testing_methods_summary": "Creepage distance measurement, glow wire test, torque resistance of lamp base."
        }
    },
    {
        "standard_number": "IS 694",
        "title": "Polyvinyl Chloride Insulated Unsheathed and Sheathed Cables/Cords with Rigid and Flexible Conductor for Rated Voltages Up to and Including 450/750 V",
        "publication_year": 2010,
        "reaffirmed_year": 2020,
        "ics_code": "29.060.20",
        "committee_code": "ETD 9",
        "domain": "Electrotechnical",
        "status": "Reaffirmed (2020)",
        "is_mandatory": True,
        "scope": "Covers the requirements of single core and multi core PVC insulated cables for electric power and lighting in domestic and industrial buildings.",
        "preview_url": "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=694",
        "source_url": "https://standardsbis.bsbedge.com/BIS_searchstandard.aspx?keyword=694&id=0",
        "references": [
            {"standard_number": "IS 8130", "year": 2013, "title": "Conductors for insulated electric cables and flexible cords", "reference_type": "raw_material"},
            {"standard_number": "IS 5831", "year": 1984, "title": "PVC insulation and sheath of electric cables", "reference_type": "raw_material"},
            {"standard_number": "IS 10810", "year": 1984, "title": "Methods of test for cables", "reference_type": "testing"}
        ],
        "safety_testing": {
            "is_safety_related": True,
            "is_testing_related": True,
            "is_sampling_related": True,
            "is_quality_spec": True,
            "safety_justification": "Fire retardant insulation, dielectric breakdown prevention, flame propagation resistance.",
            "testing_methods_summary": "High voltage water immersion test, conductor resistance test, spark testing, flammability test."
        }
    },
    {
        "standard_number": "IS 2026 (Part 1)",
        "title": "Power Transformers - Part 1: General",
        "publication_year": 2011,
        "reaffirmed_year": 2021,
        "ics_code": "29.180",
        "committee_code": "ETD 16",
        "domain": "Electrotechnical",
        "status": "Reaffirmed (2021)",
        "is_mandatory": True,
        "scope": "Applies to three-phase and single-phase power transformers (including auto-transformers). Specifies ratings, cooling methods, temperature rise limits, and insulation levels.",
        "preview_url": "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=2026_1",
        "source_url": "https://standardsbis.bsbedge.com/BIS_searchstandard.aspx?keyword=2026&id=0",
        "references": [
            {"standard_number": "IS 335", "year": 2018, "title": "New insulating oils - Specification", "reference_type": "raw_material"},
            {"standard_number": "IS 2026 (Part 2)", "year": 2010, "title": "Power Transformers - Temperature rise", "reference_type": "testing"}
        ],
        "safety_testing": {
            "is_safety_related": True,
            "is_testing_related": True,
            "is_sampling_related": False,
            "is_quality_spec": True,
            "safety_justification": "Overload protection, lightning impulse withstand, oil flash point safety, tank burst pressure limits.",
            "testing_methods_summary": "No-load loss and current measurement, short-circuit impedance test, routine and type dielectric tests."
        }
    },

    # --- CIVIL ENGINEERING & CONSTRUCTION ---
    {
        "standard_number": "IS 269",
        "title": "Ordinary Portland Cement - Specification",
        "publication_year": 2015,
        "reaffirmed_year": 2020,
        "ics_code": "91.100.10",
        "committee_code": "CED 2",
        "domain": "Civil Engineering",
        "status": "Reaffirmed (2020)",
        "is_mandatory": True,
        "scope": "Covers manufacture, chemical and physical requirements of 33 grade, 43 grade and 53 grade ordinary Portland cement.",
        "preview_url": "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=269_2015_reff2020",
        "source_url": "https://standardsbis.bsbedge.com/BIS_searchstandard.aspx?Standard_Number=IS+269&id=270",
        "references": [
            {"standard_number": "IS 4031", "year": 1988, "title": "Methods of physical tests for hydraulic cement", "reference_type": "testing"},
            {"standard_number": "IS 4032", "year": 1985, "title": "Method of chemical analysis of hydraulic cement", "reference_type": "testing"},
            {"standard_number": "IS 3535", "year": 1986, "title": "Methods of sampling hydraulic cements", "reference_type": "sampling"}
        ],
        "safety_testing": {
            "is_safety_related": False,
            "is_testing_related": True,
            "is_sampling_related": True,
            "is_quality_spec": True,
            "safety_justification": "Structural failure prevention by guaranteeing compressive strength and sound setting characteristics.",
            "testing_methods_summary": "Compressive strength at 3, 7, 28 days; initial and final setting time; Le-Chatelier soundness test; Blaine fineness."
        }
    },
    {
        "standard_number": "IS 456",
        "title": "Plain and Reinforced Concrete - Code of Practice",
        "publication_year": 2000,
        "reaffirmed_year": 2021,
        "ics_code": "91.100.30",
        "committee_code": "CED 2",
        "domain": "Civil Engineering",
        "status": "Reaffirmed (2021)",
        "is_mandatory": False,
        "certification_scheme": "Code of Practice / Design Standard",
        "scope": "Deals with general structural use of plain and reinforced concrete in buildings and civil engineering works. Covers materials, structural design, durability, workmanship and inspection.",
        "preview_url": "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=456",
        "source_url": "https://standardsbis.bsbedge.com/BIS_searchstandard.aspx?keyword=456&id=0",
        "references": [
            {"standard_number": "IS 269", "year": 2015, "title": "Ordinary Portland Cement", "reference_type": "normative"},
            {"standard_number": "IS 383", "year": 2016, "title": "Coarse and fine aggregate for concrete", "reference_type": "normative"},
            {"standard_number": "IS 1786", "year": 2008, "title": "High strength deformed steel bars and wires for concrete reinforcement", "reference_type": "normative"},
            {"standard_number": "IS 516", "year": 1959, "title": "Methods of tests for strength of concrete", "reference_type": "testing"}
        ],
        "safety_testing": {
            "is_safety_related": True,
            "is_testing_related": True,
            "is_sampling_related": True,
            "is_quality_spec": True,
            "safety_justification": "Prevents catastrophic structural collapses under dead, live, wind, and seismic loads.",
            "testing_methods_summary": "Concrete cube compressive strength testing, slump test for workability, flexural strength test."
        }
    },
    {
        "standard_number": "IS 1786",
        "title": "High Strength Deformed Steel Bars and Wires for Concrete Reinforcement - Specification (TMT Rebars)",
        "publication_year": 2008,
        "reaffirmed_year": 2018,
        "ics_code": "77.140.15",
        "committee_code": "CED 54",
        "domain": "Civil Engineering",
        "status": "Reaffirmed (2018)",
        "is_mandatory": True,
        "scope": "Covers requirements of high strength deformed steel bars and wires of grades Fe 415, Fe 500, Fe 550, and Fe 600 for use as reinforcement in concrete.",
        "preview_url": "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=1786",
        "source_url": "https://standardsbis.bsbedge.com/BIS_searchstandard.aspx?keyword=1786&id=0",
        "references": [
            {"standard_number": "IS 1608", "year": 2005, "title": "Metallic materials - Tensile testing at ambient temperature", "reference_type": "testing"},
            {"standard_number": "IS 1599", "year": 2012, "title": "Metallic materials - Bend test", "reference_type": "testing"}
        ],
        "safety_testing": {
            "is_safety_related": True,
            "is_testing_related": True,
            "is_sampling_related": True,
            "is_quality_spec": True,
            "safety_justification": "Earthquake resistance via minimum elongation percentage, yield stress guarantees, and high ductility (D-grades).",
            "testing_methods_summary": "0.2% proof stress / yield stress determination, tensile strength test, bend and rebend test."
        }
    },
    {
        "standard_number": "IS 4984",
        "title": "High Density Polyethylene (HDPE) Pipes for Water Supply - Specification",
        "publication_year": 2016,
        "reaffirmed_year": 2021,
        "ics_code": "23.040.20",
        "committee_code": "CED 50",
        "domain": "Civil Engineering",
        "status": "Reaffirmed (2021)",
        "is_mandatory": True,
        "scope": "Covers requirements for high density polyethylene (HDPE) pipes from 16 mm to 1000 mm diameter intended for potable water supply, drainage, and sewer lines.",
        "preview_url": "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=4984",
        "source_url": "https://standardsbis.bsbedge.com/BIS_searchstandard.aspx?keyword=4984&id=0",
        "references": [
            {"standard_number": "IS 2530", "year": 1963, "title": "Methods of test for polyethylene molding materials and polyethylene compounds", "reference_type": "testing"},
            {"standard_number": "IS 7328", "year": 1992, "title": "High density polyethylene materials for moulding and extrusion", "reference_type": "raw_material"}
        ],
        "safety_testing": {
            "is_safety_related": True,
            "is_testing_related": True,
            "is_sampling_related": True,
            "is_quality_spec": True,
            "safety_justification": "Ensures no toxic chemical leaching into municipal drinking water and prevents high-pressure bursting.",
            "testing_methods_summary": "Hydrostatic pressure test, carbon black content, melt flow rate (MFR), tensile strength and elongation at break."
        }
    },

    # --- FIRE SAFETY & PPE ---
    {
        "standard_number": "IS 15683",
        "title": "Portable Fire Extinguishers - Performance and Construction - Specification",
        "publication_year": 2018,
        "reaffirmed_year": 2023,
        "ics_code": "13.220.10",
        "committee_code": "CED 22",
        "domain": "Mechanical Engineering",
        "status": "Active",
        "is_mandatory": True,
        "scope": "Specifies requirements for design, construction, testing and performance of portable fire extinguishers of water, foam, dry powder, carbon dioxide and clean agent types.",
        "preview_url": "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=15683",
        "source_url": "https://standardsbis.bsbedge.com/BIS_searchstandard.aspx?keyword=15683&id=0",
        "references": [
            {"standard_number": "IS 2171", "year": 1985, "title": "Dry powder fire extinguishers", "reference_type": "normative"},
            {"standard_number": "IS 2878", "year": 2004, "title": "Carbon dioxide fire extinguishers", "reference_type": "normative"}
        ],
        "safety_testing": {
            "is_safety_related": True,
            "is_testing_related": True,
            "is_sampling_related": False,
            "is_quality_spec": True,
            "safety_justification": "Life safety against Class A, B, C, D, and electrical fires. Cylinder burst prevention.",
            "testing_methods_summary": "Fire rating extinguishing tests, hydrostatic burst pressure test, electrical conductivity of discharge."
        }
    },
    {
        "standard_number": "IS 9473",
        "title": "Respiratory Protective Devices - Filtering Half Masks to Protect Against Particles (N95 / FFP2 Equivalent)",
        "publication_year": 2002,
        "reaffirmed_year": 2019,
        "ics_code": "13.340.30",
        "committee_code": "CHD 8",
        "domain": "Personal Protective Equipment & Safety",
        "status": "Reaffirmed (2019)",
        "is_mandatory": True,
        "scope": "Specifies minimum requirements for filtering half masks as respiratory protective devices against particulates. Covers classes FFP1, FFP2, and FFP3.",
        "preview_url": "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=9473",
        "source_url": "https://standardsbis.bsbedge.com/BIS_searchstandard.aspx?keyword=9473&id=0",
        "references": [
            {"standard_number": "IS 9623", "year": 2008, "title": "Selection, use and maintenance of respiratory protective devices - Code of practice", "reference_type": "safety"}
        ],
        "safety_testing": {
            "is_safety_related": True,
            "is_testing_related": True,
            "is_sampling_related": True,
            "is_quality_spec": True,
            "safety_justification": "Protection of healthcare workers and miners against aerosol pathogens, silica dust, and toxic fumes.",
            "testing_methods_summary": "Sodium chloride aerosol penetration test, paraffin oil penetration test, breathing resistance test, total inward leakage (TIL)."
        }
    },
    {
        "standard_number": "IS 2925",
        "title": "Specification for Industrial Safety Helmets",
        "publication_year": 1984,
        "reaffirmed_year": 2019,
        "ics_code": "13.340.20",
        "committee_code": "CHD 8",
        "domain": "Personal Protective Equipment & Safety",
        "status": "Reaffirmed (2019)",
        "is_mandatory": True,
        "scope": "Covers requirements for industrial safety helmets intended to protect head against impact from falling objects and electrical shock in industrial workplaces.",
        "preview_url": "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=2925",
        "source_url": "https://standardsbis.bsbedge.com/BIS_searchstandard.aspx?keyword=2925&id=0",
        "references": [],
        "safety_testing": {
            "is_safety_related": True,
            "is_testing_related": True,
            "is_sampling_related": False,
            "is_quality_spec": True,
            "safety_justification": "Protection of construction and factory workers against skull fractures and electrical flash shocks.",
            "testing_methods_summary": "Shock absorption test, penetration resistance test, flammability test, electrical insulation withstand test."
        }
    },

    # --- ELECTRONICS & IT ---
    {
        "standard_number": "IS 13252 (Part 1)",
        "title": "Information Technology Equipment - Safety - Part 1: General Requirements",
        "publication_year": 2010,
        "reaffirmed_year": 2020,
        "ics_code": "35.020",
        "committee_code": "LITD 8",
        "domain": "Electronics and Information Technology",
        "status": "Reaffirmed (2020)",
        "is_mandatory": True,
        "scope": "Applies to mains-powered or battery-powered information technology equipment, including computer servers, laptops, printers, routers, and office equipment. Establishes requirements for reducing risk of fire, electric shock, and energy hazards.",
        "preview_url": "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=13252_1",
        "source_url": "https://standardsbis.bsbedge.com/BIS_searchstandard.aspx?keyword=13252&id=0",
        "references": [
            {"standard_number": "IS 616", "year": 2017, "title": "Audio, video and similar electronic apparatus - Safety requirements", "reference_type": "safety"},
            {"standard_number": "IS 16046 (Part 1)", "year": 2018, "title": "Secondary cells and batteries - Safety", "reference_type": "safety"}
        ],
        "safety_testing": {
            "is_safety_related": True,
            "is_testing_related": True,
            "is_sampling_related": False,
            "is_quality_spec": True,
            "safety_justification": "Mandatory CRS (Compulsory Registration Scheme) standard for all computers, laptops, and IT servers against fire and electric shock.",
            "testing_methods_summary": "Input power test, insulation resistance, electric strength test, fault condition simulation, temperature measurements."
        }
    },

    # --- CABLE TRAYS, CONDUITS & STRUCTURAL STEEL (STANDIQ PROCUREMENT SPEC) ---
    {
        "standard_number": "IS 1239:2018",
        "title": "Stainless Steel Wire and Wire Products - Specification",
        "publication_year": 2018,
        "reaffirmed_year": 2023,
        "ics_code": "77.140.65",
        "committee_code": "MTD 4",
        "domain": "Mechanical and Metallurgy",
        "status": "Active",
        "is_mandatory": True,
        "scope": "This standard specifies the requirements for stainless steel wire and wire products used in industrial cable trays, electrical cable support systems, wiring enclosures, and structural fittings under corrosive environments.",
        "preview_url": "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=1239_2018",
        "source_url": "https://standardsbis.bsbedge.com/BIS_searchstandard.aspx?keyword=1239&id=0",
        "references": [
            {"standard_number": "IS 8082:2021", "year": 2021, "title": "Electroplated Coatings of Zinc on Iron & Steel", "reference_type": "normative"},
            {"standard_number": "IS 2629:1985", "year": 1985, "title": "Recommended Practice for Hot Dip Galvanizing", "reference_type": "normative"},
            {"standard_number": "IS 1448:2018", "year": 2018, "title": "General Requirements for Cable Management Systems", "reference_type": "normative"},
            {"standard_number": "IS 15669:2008", "year": 2008, "title": "Cable Trays, Cable Ladders and Accessories", "reference_type": "normative"},
            {"standard_number": "IS 2102:1999", "year": 1999, "title": "Safety of Machinery - General Principles", "reference_type": "allied"},
            {"standard_number": "IS 732:1993", "year": 1993, "title": "Code of Practice for Electrical Wiring Installations", "reference_type": "allied"},
            {"standard_number": "IS 12894:2002", "year": 2002, "title": "Methods of Test for Coatings on Iron & Steel", "reference_type": "allied"},
            {"standard_number": "IS 4687:2000", "year": 2000, "title": "Hot Dip Galvanized (Zinc) Coated Steel Wires", "reference_type": "allied"}
        ],
        "amendments": [
            {"amendment_number": "Amendment No. 1", "amendment_year": 2022, "publication_date": "15 Aug 2022", "title": "Amendment No. 1 to IS 1239 (Corrosion Resistance Limits)", "status": "Active"},
            {"amendment_number": "Amendment No. 2", "amendment_year": 2024, "publication_date": "10 Jan 2024", "title": "Amendment No. 2 to IS 1239 (Tolerance Specification)", "status": "Active"}
        ],
        "safety_testing": {
            "is_safety_related": True,
            "is_testing_related": True,
            "is_sampling_related": True,
            "is_quality_spec": True,
            "safety_justification": "Prescribes tensile strength, proof stress, corrosion resistance in saline/acidic atmosphere, and earthing continuity for cable management trays.",
            "testing_methods_summary": "Tensile testing, bend test, intergranular corrosion resistance test (IGC test), coating thickness measurement."
        }
    },
    {
        "standard_number": "IS 1248:2021",
        "title": "Stainless Steel Sheets, Plates and Strips for Engineering Applications",
        "publication_year": 2021,
        "reaffirmed_year": 2024,
        "ics_code": "77.140.20",
        "committee_code": "MTD 22",
        "domain": "Mechanical and Metallurgy",
        "status": "Active",
        "is_mandatory": True,
        "scope": "Prescribes requirements for hot-rolled and cold-rolled stainless steel sheets, plates, and strip intended for fabrication of perforated cable trays, industrial enclosures, and electrical raceways.",
        "preview_url": "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=1248_2021",
        "source_url": "https://standardsbis.bsbedge.com/BIS_searchstandard.aspx?keyword=1248&id=0",
        "references": [
            {"standard_number": "IS 2102:1999", "year": 1999, "title": "General tolerances for dimensions", "reference_type": "normative"},
            {"standard_number": "IS 732:1993", "year": 1993, "title": "Code of Practice for Electrical Wiring Installations", "reference_type": "normative"}
        ],
        "safety_testing": {
            "is_safety_related": True,
            "is_testing_related": True,
            "is_sampling_related": True,
            "is_quality_spec": True,
            "safety_justification": "Ensures material grade compliance (AISI 304 / 316), minimum yield strength, and flame/fire resistance.",
            "testing_methods_summary": "Chemical composition analysis, Rockwell/Brinell hardness, elongation test, surface roughness."
        }
    },
    {
        "standard_number": "IS 4759:2016",
        "title": "Perforated Cable Trays and Cable Ladders - Specification",
        "publication_year": 2016,
        "reaffirmed_year": 2022,
        "ics_code": "29.120.10",
        "committee_code": "ETD 14",
        "domain": "Electrical Engineering",
        "status": "Active",
        "is_mandatory": True,
        "scope": "Specifies design dimensions, perforation patterns, safe working load (SWL), deflection limits, and safety earthing requirements for metallic perforated cable trays and ladders.",
        "preview_url": "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=4759_2016",
        "source_url": "https://standardsbis.bsbedge.com/BIS_searchstandard.aspx?keyword=4759&id=0",
        "references": [
            {"standard_number": "IS 15669:2008", "year": 2008, "title": "Cable Trays, Cable Ladders and Accessories", "reference_type": "normative"},
            {"standard_number": "IS 2629:1985", "year": 1985, "title": "Hot Dip Galvanizing Practice", "reference_type": "normative"}
        ],
        "safety_testing": {
            "is_safety_related": True,
            "is_testing_related": True,
            "is_sampling_related": True,
            "is_quality_spec": True,
            "safety_justification": "Prescribes structural load capacity, impact resistance, and continuous electrical bonding to prevent electric shock hazards in industrial cabling.",
            "testing_methods_summary": "Safe working load (SWL) deflection test, electrical continuity test, flame retardancy test."
        }
    },
    {
        "standard_number": "IS 2062:2011",
        "title": "Hot Rolled Medium and High Tensile Structural Steel",
        "publication_year": 2011,
        "reaffirmed_year": 2021,
        "ics_code": "77.140.01",
        "committee_code": "MTD 4",
        "domain": "Mechanical and Civil",
        "status": "Active",
        "is_mandatory": True,
        "scope": "Covers requirements of steel including micro-alloyed steel plates, shapes, sections, and flats for use in structural support fabrications, brackets, and heavy duty industrial cable tray supports.",
        "preview_url": "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=2062_2011",
        "source_url": "https://standardsbis.bsbedge.com/BIS_searchstandard.aspx?keyword=2062&id=0",
        "references": [
            {"standard_number": "IS 1608", "year": 2005, "title": "Metallic materials - Tensile testing at ambient temperature", "reference_type": "normative"}
        ],
        "safety_testing": {
            "is_safety_related": True,
            "is_testing_related": True,
            "is_sampling_related": True,
            "is_quality_spec": True,
            "safety_justification": "Guarantees yield strength, Charpy impact toughness, and weldability under structural load conditions.",
            "testing_methods_summary": "Tensile testing, Charpy V-notch impact test, bend test."
        }
    },
    {
        "standard_number": "IS 277:2003",
        "title": "Mild Steel and Medium Tensile Steel Bars and Sections / Galvanized Sheets",
        "publication_year": 2003,
        "reaffirmed_year": 2020,
        "ics_code": "77.140.50",
        "committee_code": "MTD 4",
        "domain": "Mechanical and Metallurgy",
        "status": "Active",
        "is_mandatory": True,
        "scope": "Specifies galvanized steel sheets, plain and corrugated, and mild steel structural sections used for tray covers, dividers, couplers, and corrosion-resistant cable management accessories.",
        "preview_url": "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=277_2003",
        "source_url": "https://standardsbis.bsbedge.com/BIS_searchstandard.aspx?keyword=277&id=0",
        "references": [
            {"standard_number": "IS 6745", "year": 1972, "title": "Methods for determination of mass of zinc coating", "reference_type": "normative"}
        ],
        "safety_testing": {
            "is_safety_related": True,
            "is_testing_related": True,
            "is_sampling_related": True,
            "is_quality_spec": True,
            "safety_justification": "Zinc coating adhesion and mass verification to ensure corrosion barrier and prevent degradation.",
            "testing_methods_summary": "Coating mass test, triple spot test, bend test."
        }
    },

    # --- PRECIOUS METALS & HALLMARKING (DoCA MANDATE) ---
    {
        "standard_number": "IS 1417:2016",
        "title": "Gold and Gold Alloys, Jewellery/Artefacts - Fineness and Marking - Specification",
        "publication_year": 2016,
        "reaffirmed_year": 2021,
        "ics_code": "39.060",
        "committee_code": "MTD 10",
        "domain": "Precious Metals and Hallmarking",
        "status": "Active & Reaffirmed (2021)",
        "is_mandatory": True,
        "certification_scheme": "Mandatory Hallmarking Scheme (DoCA)",
        "scope": "Specifies requirements for fineness of gold and gold alloys in jewellery and artefacts, and mandatory hallmarking requirements comprising the BIS logo, fineness purity mark (e.g., 22K916, 18K750, 14K585), and 6-digit alphanumeric Hallmark Unique Identification (HUID) under Central Government Orders.",
        "preview_url": "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=1417_2016",
        "source_url": "https://standardsbis.bsbedge.com/BIS_searchstandard.aspx?keyword=1417&id=0",
        "references": [
            {"standard_number": "IS 1418", "year": 2009, "title": "Assaying of Gold in Gold Bullion, Gold Alloys and Gold Jewellery/Artefacts", "reference_type": "testing"},
            {"standard_number": "IS 2790", "year": 1979, "title": "Guidelines for manufacture of 14, 18 and 22 carat gold alloys", "reference_type": "normative"}
        ],
        "amendments": [
            {"amendment_number": "Amd 1", "amendment_year": 2020, "title": "Mandatory 6-digit HUID Laser Marking Protocol", "status": "Active"}
        ],
        "safety_testing": {
            "is_safety_related": True,
            "is_testing_related": True,
            "is_sampling_related": True,
            "is_quality_spec": True,
            "safety_justification": "Consumer protection against under-caratage and fraudulent purity claims; ensures traceably verified precious metal purity.",
            "testing_methods_summary": "Fire assay cupellation testing, X-ray fluorescence (XRF) non-destructive gold assay."
        }
    },
    {
        "standard_number": "IS 2112:2014",
        "title": "Silver and Silver Alloys, Jewellery/Artefacts - Fineness and Marking - Specification",
        "publication_year": 2014,
        "reaffirmed_year": 2019,
        "ics_code": "39.060",
        "committee_code": "MTD 10",
        "domain": "Precious Metals and Hallmarking",
        "status": "Active & Reaffirmed (2019)",
        "is_mandatory": False,
        "certification_scheme": "Voluntary Hallmarking Scheme",
        "scope": "Specifies requirements for fineness of silver and silver alloys in jewellery and artefacts, hallmarking grades (999, 970, 925, 900, 835, 800), and assay marking protocols.",
        "preview_url": "https://standardsbis.bsbedge.com/BIS_Preview.aspx?id=2112_2014",
        "source_url": "https://standardsbis.bsbedge.com/BIS_searchstandard.aspx?keyword=2112&id=0",
        "references": [
            {"standard_number": "IS 2113", "year": 2014, "title": "Assaying of Silver in Silver Bullion, Silver Alloys and Silver Jewellery", "reference_type": "testing"}
        ],
        "safety_testing": {
            "is_safety_related": False,
            "is_testing_related": True,
            "is_sampling_related": True,
            "is_quality_spec": True,
            "safety_justification": "Third-party certification of silver fineness grades.",
            "testing_methods_summary": "Potentiometric titration method, gravimetric assay."
        }
    }
]

def seed_database():
    print("Recreating database tables with updated lifecycle and amendment schema...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    pipeline = IngestionPipeline(db)

    
    print(f"Seeding {len(SEED_STANDARDS)} verified multi-domain BIS standards...")
    for record in SEED_STANDARDS:
        std = pipeline.ingest_standard_record(record)
        print(f"  [+] Ingested {std.standard_number:20} | {std.title[:45]} ({len(std.references)} refs)")
        
    db.close()
    print("\nDatabase seeded successfully!")

if __name__ == "__main__":
    seed_database()
