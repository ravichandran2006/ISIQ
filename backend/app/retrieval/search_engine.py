import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func

from backend.app.database.models import Standard, StandardReference, Amendment, SafetyTestingMetadata
from backend.app.retrieval.vector_store import get_semantic_vector_engine
from backend.app.retrieval.reranker import StandardsReranker

class HybridSearchEngine:
    """
    Production hybrid search engine combining:
    - Direct SQLite keyword and token matching
    - Dense BGE semantic vector similarity with on-disk caching
    - Exact IS citation resolution
    - Accurate year and revision parsing
    - Reranking with domain and lifecycle calibration
    """

    def __init__(self, db: Session):
        self.db = db
        self.vector_engine = get_semantic_vector_engine()
        self._ensure_vector_index()

    def _ensure_vector_index(self):
        standards = self.db.query(Standard).all()
        doc_list = []
        for s in standards:
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
        self.vector_engine.build_index(doc_list)

    def search(
        self,
        query: str,
        domain_filter: Optional[str] = None,
        top_k: int = 10,
        detected_is_numbers: List[str] = None
    ) -> List[Dict[str, Any]]:
        from backend.app.recommendation.nlp_extractor import ProcurementNLPExtractor

        query_clean = ProcurementNLPExtractor.canonicalize_query(query.strip())
        if not query_clean:
            return []

        # 1. Procurement / Technical Intent Check Gate
        intent = ProcurementNLPExtractor.classify_procurement_intent(query)
        if not intent.get("is_valid", True):
            return []

        candidates_map: Dict[int, Dict[str, Any]] = {}

        # 2. Exact Title / Key Phrase Match in SQLite (Ultra-fast direct database match)
        search_phrases = []
        for phrase in [query.strip(), query_clean]:
            words = [w for w in re.findall(r'[a-zA-Z0-9]+', phrase.lower()) if len(w) > 2 and w not in ProcurementNLPExtractor.STOP_WORDS]
            if len(words) >= 2:
                p2 = " ".join(words[:2])
                if p2 not in search_phrases:
                    search_phrases.append(p2)
                if len(words) >= 3:
                    p3 = " ".join(words[:3])
                    if p3 not in search_phrases:
                        search_phrases.append(p3)
            # Only match single words if explicitly in technical products list
            technical_products = [
                "laptop", "inverter", "transformer", "refrigerator", "purifier",
                "cement", "extinguisher", "switchgear", "generator", "cable",
                "steel", "rebar", "wire", "battery", "ups", "luminaire"
            ]
            for w in words:
                if w in technical_products and w not in search_phrases:
                    search_phrases.append(w)

        for sp in search_phrases[:3]:
            matching_stds = self.db.query(Standard).filter(
                or_(
                    Standard.title.ilike(f"%{sp}%"),
                    Standard.scope.ilike(f"%{sp}%"),
                    Standard.standard_number.ilike(f"%{sp}%")
                )
            ).limit(6).all()
            for std in matching_stds:
                clean_title = (std.title or "").strip()
                if len(clean_title) >= 3 and clean_title != ")":
                    score = 0.75 if sp in clean_title.lower() else 0.65
                    candidates_map[std.id] = self._serialize_standard(std, base_score=score, match_type="lexical_keyword")

        # 3. Dense Semantic Vector Search (Primary Hybrid Engine)
        vector_results = self.vector_engine.search(query_clean, top_k=top_k * 3, min_threshold=0.35)
        for doc_id, sim_score in vector_results:
            if doc_id not in candidates_map:
                std = self.db.query(Standard).filter(Standard.id == doc_id).first()
                if std:
                    clean_title = (std.title or "").strip()
                    if len(clean_title) >= 3 and clean_title != ")":
                        candidates_map[doc_id] = self._serialize_standard(std, base_score=sim_score, match_type="bge_dense_semantic")
            else:
                # Merge semantic score
                candidates_map[doc_id]["search_score"] = max(candidates_map[doc_id]["search_score"], sim_score)

        # 4. Explicit IS number detection (Auxiliary exact citation)
        is_numbers = detected_is_numbers or []
        extra_is = re.findall(r'IS\s*[:\-]?\s*(\d+(?:\s*(?:\(Part\s*\d+\)|Part\s*\d+))?)', query_clean, re.IGNORECASE)
        for num in extra_is:
            is_numbers.append(f"IS {num.strip()}")

        for is_num in is_numbers:
            exact_matches = self.db.query(Standard).filter(
                or_(
                    Standard.standard_number.ilike(f"%{is_num}%"),
                    Standard.standard_number == is_num
                )
            ).all()
            for m in exact_matches:
                if m.id not in candidates_map:
                    candidates_map[m.id] = self._serialize_standard(m, base_score=0.92, match_type="exact_identifier")
                else:
                    candidates_map[m.id]["match_type"] = "exact_identifier"
                    candidates_map[m.id]["search_score"] = max(candidates_map[m.id]["search_score"], 0.92)

        if not candidates_map:
            return []

        candidate_list = list(candidates_map.values())

        # 5. Dense Semantic Reranking with Domain & Lifecycle Calibration
        ranked_results = StandardsReranker.rerank(
            candidates=candidate_list,
            query=query_clean,
            detected_domain=domain_filter,
            detected_is_numbers=is_numbers
        )

        if not ranked_results:
            return []

        top_score = ranked_results[0].get("final_score", 0.0)
        has_exact_is = any(c.get("match_type") == "exact_identifier" for c in ranked_results)

        # Gate threshold: 0.45 for general semantic matches; only exact IS identifier can bypass
        if top_score < 0.45 and not has_exact_is:
            return []

        filtered_ranked = [
            c for c in ranked_results
            if c.get("final_score", 0.0) >= 0.45 or c.get("match_type") == "exact_identifier"
        ]
        return filtered_ranked[:top_k]

    def _serialize_standard(self, std: Standard, base_score: float, match_type: str) -> Dict[str, Any]:
        # Extract accurate publication year if missing or 0
        pub_year = std.publication_year
        if not pub_year or pub_year == 0:
            # Look for 4-digit year in title (e.g., ": 2024", "Sec 7 : 2024")
            year_match = re.search(r':\s*(19\d{2}|20\d{2})\b', std.title or "")
            if not year_match:
                year_match = re.search(r'\b(19\d{2}|20\d{2})\b', (std.title or "") + " " + (std.standard_number or ""))
            if year_match:
                try:
                    pub_year = int(year_match.group(1))
                except Exception:
                    pub_year = None

        reaffirmed = std.reaffirmed_year
        if not reaffirmed:
            reaff_match = re.search(r'(?:reff|reaffirmed|reaff|reviewed)\s*[:\-]?\s*(20\d{2}|19\d{2})', (std.title or "") + " " + (std.scope or ""), re.IGNORECASE)
            if reaff_match:
                try:
                    reaffirmed = int(reaff_match.group(1))
                except Exception:
                    reaffirmed = None

        amd_list = []
        for a in std.amendments:
            amd_list.append({
                "amendment_number": a.amendment_number,
                "amendment_year": a.amendment_year,
                "title": a.title,
                "status": a.status or "Active",
                "source_url": a.source_url
            })

        # Synthesize Lifecycle Timeline
        timeline = []
        if pub_year:
            timeline.append(f"Published in {pub_year}")
        if std.revision_count and std.revision_count > 0:
            timeline.append(f"{std.revision_text} ({std.revision_count})")
        if reaffirmed:
            timeline.append(f"Reviewed & Reaffirmed in {reaffirmed}")

        for a in amd_list:
            amd_str = f"{a['amendment_number']} ({a.get('amendment_year', '')})" if a.get('amendment_year') else a['amendment_number']
            timeline.append(f"Amendment: {amd_str}")

        timeline.append(f"Current Status: {std.status or 'Active'}")

        actual_amd_count = std.no_of_amendments if (std.no_of_amendments is not None and std.no_of_amendments > 0) else len(amd_list)

        return {
            "id": std.id,
            "standard_number": std.standard_number,
            "title": std.title,
            "publication_year": pub_year,
            "reaffirmed_year": reaffirmed,
            "no_of_amendments": actual_amd_count,
            "revision_count": std.revision_count or 0,
            "revision_text": std.revision_text or ("Original Publication" if not std.revision_count else f"Revision {std.revision_count}"),
            "supersedes_is": std.supersedes_is,
            "superseded_by_is": std.superseded_by_is,
            "certification_scheme": std.certification_scheme or "Mandatory ISI Scheme-I",
            "lifecycle_timeline": timeline,
            "status": std.status or "Active",
            "domain": std.domain,
            "ics_code": std.ics_code,
            "committee_code": std.committee_code,
            "scope": std.scope or "",
            "is_mandatory": std.is_mandatory,
            "source_url": std.source_url,
            "preview_url": std.preview_url,
            "search_score": base_score,
            "match_type": match_type,
            "safety_testing": {
                "is_safety_related": std.safety_testing.is_safety_related if std.safety_testing else False,
                "is_testing_related": std.safety_testing.is_testing_related if std.safety_testing else False,
                "safety_justification": std.safety_testing.safety_justification if std.safety_testing else "",
                "testing_methods_summary": std.safety_testing.testing_methods_summary if std.safety_testing else "",
                "source_type": std.safety_testing.source_type if std.safety_testing else "rule_based"
            } if std.safety_testing else {},
            "references": [
                {
                    "referenced_standard_number": r.referenced_standard_number,
                    "referenced_title": r.referenced_title,
                    "referenced_year": r.referenced_year,
                    "reference_type": r.reference_type,
                    "link": r.link
                } for r in std.references
            ],
            "amendments": amd_list
        }
