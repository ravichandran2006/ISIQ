import sys
import os
import csv
import re

# Ensure backend can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database.connection import SessionLocal
from backend.app.database.models import Standard
from backend.app.retrieval.search_engine import HybridSearchEngine

REVISION_WORDS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10
}

def parse_revision(title: str):
    m = re.search(r'\((first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|\d+)(?:st|nd|rd|th)?\s+revision\b', title, re.IGNORECASE)
    if m:
        rev_str = m.group(1).lower()
        rev_count = REVISION_WORDS.get(rev_str, int(rev_str) if rev_str.isdigit() else 1)
        return f"{m.group(1).capitalize()} Revision", rev_count
    return "Original Publication", 0

def infer_domain(num: str, title: str):
    t = (num + " " + title).lower()
    if any(k in t for k in ["cement", "concrete", "aggregate", "masonry", "bitumen", "building", "structural", "rebar", "earthquake", "bamboo", "lintels", "glass in buildings", "prestressed", "pozzolana", "fly ash", "damp-proof"]):
        return "Civil Engineering"
    if any(k in t for k in ["grease", "nipple", "bolt", "screw", "crane", "hoist", "welding", "ship loader", "bulk handling", "bush", "collar", "fastener", "storage tank", "duct"]):
        return "Mechanical Engineering"
    if any(k in t for k in ["fan", "wire", "cable", "motor", "inverter", "solar", "pedestal"]):
        return "Electrotechnical"
    if any(k in t for k in ["copper", "steel", "tensile"]):
        return "Mechanical Engineering"
    return "General Standard"

def is_mandatory_standard(num: str, title: str):
    t = (num + " " + title).lower()
    if any(k in t for k in ["cement", "rebar", "steel bar", "structural steel", "deformed steel", "wire rope hoist", "crane"]):
        return True
    return False

def ingest():
    db = SessionLocal()
    csv_path = "data/bis_is_sample_official.csv"
    
    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        count_added = 0
        count_updated = 0
        
        for row in reader:
            raw_num = row["is_number"].strip()
            title = row["is_title"].strip()
            reviewed_in_raw = row["reviewed_in"].strip()
            source_url = row.get("source_url", "").strip() or "https://standards.bis.gov.in"
            
            # Extract standard number and publication year
            # e.g., "IS 269:2015" -> "IS 269", pub_year = 2015
            # e.g., "IS 432 (Part 1):2026" -> "IS 432 (Part 1)", pub_year = 2026
            pub_year = None
            if ":" in raw_num:
                parts = raw_num.split(":")
                std_number = parts[0].strip()
                try:
                    pub_year = int(parts[1].strip())
                except ValueError:
                    pub_year = None
            else:
                std_number = raw_num
                
            reaffirmed_year = None
            if reviewed_in_raw:
                try:
                    reaffirmed_year = int(float(reviewed_in_raw))
                except ValueError:
                    reaffirmed_year = None
                    
            rev_text, rev_count = parse_revision(title)
            domain = infer_domain(std_number, title)
            is_mand = is_mandatory_standard(std_number, title)
            
            status = f"Reaffirmed ({reaffirmed_year})" if reaffirmed_year else "Active"
            cert_scheme = "Mandatory ISI Scheme-I" if is_mand else "Voluntary Standard"
            
            # Check existing standard by standard_number (case-insensitive or partial)
            existing = db.query(Standard).filter(Standard.standard_number.ilike(std_number)).first()
            if not existing and ":" in raw_num:
                existing = db.query(Standard).filter(Standard.standard_number.ilike(raw_num)).first()
                
            scope_text = f"Indian Standard {std_number} prescribes comprehensive technical specifications, quality criteria, performance tolerances, sampling protocols, and compliance test methods for {title}."
            
            if existing:
                existing.title = title
                if pub_year:
                    existing.publication_year = pub_year
                if reaffirmed_year:
                    existing.reaffirmed_year = reaffirmed_year
                existing.revision_text = rev_text
                existing.revision_count = rev_count
                existing.domain = domain
                existing.status = status
                existing.is_mandatory = is_mand
                existing.certification_scheme = cert_scheme
                existing.source_url = source_url
                if not existing.scope or len(existing.scope) < 30:
                    existing.scope = scope_text
                count_updated += 1
            else:
                new_std = Standard(
                    standard_number=std_number,
                    title=title,
                    publication_year=pub_year,
                    reaffirmed_year=reaffirmed_year,
                    revision_text=rev_text,
                    revision_count=rev_count,
                    domain=domain,
                    status=status,
                    is_mandatory=is_mand,
                    certification_scheme=cert_scheme,
                    source_url=source_url,
                    scope=scope_text
                )
                db.add(new_std)
                count_added += 1
                
        db.commit()
        print(f"Ingestion completed: {count_added} standards added, {count_updated} standards updated.")
        
    # Rebuild dense BGE vector embeddings to include new standards
    print("Rebuilding dense BGE vector embeddings for newly ingested standards...")
    search_engine = HybridSearchEngine(db)
    search_engine.vector_engine.is_fitted = False
    doc_list = []
    for s in db.query(Standard).all():
        clean_title = (s.title or "").strip()
        if not s.standard_number or len(clean_title) < 3 or clean_title == ")":
            continue
        doc_list.append({
            "id": s.id,
            "standard_number": s.standard_number,
            "title": clean_title,
            "domain": s.domain or "",
            "committee_code": s.committee_code or "",
            "scope": s.scope or ""
        })
    search_engine.vector_engine.build_index(doc_list, force_refresh=True)
    db.close()
    print(f"Dense BGE Vector Search index successfully updated. Total indexed vectors: {len(doc_list)}")

if __name__ == "__main__":
    ingest()
