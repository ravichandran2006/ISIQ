import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func

from backend.app.database.models import Standard, StandardReference, Amendment, SafetyTestingMetadata
from backend.app.retrieval.vector_store import SemanticVectorEngine
from backend.app.retrieval.reranker import StandardsReranker

class HybridSearchEngine:
    """
    Production hybrid search engine combining:
    - Exact regex and identifier matching
    - Full-text keyword token matching
    - Dense vector similarity
    - Soft domain boosting
    - Complete lifecycle and amendment serialization
    """

    def __init__(self, db: Session):
        self.db = db
        self.vector_engine = SemanticVectorEngine()
        self._refresh_vector_index()

    def _refresh_vector_index(self):
        standards = self.db.query(Standard).all()
        doc_list = []
        for s in standards:
            doc_list.append({
                "id": s.id,
                "standard_number": s.standard_number,
                "title": s.title,
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

        candidates_map: Dict[int, Dict[str, Any]] = {}
        query_words = [w.lower() for w in re.findall(r'[a-zA-Z0-9]+', query_clean) if len(w) > 2]

        # 1. Exact IS number search
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
                candidates_map[m.id] = self._serialize_standard(m, base_score=1.5, match_type="exact_identifier")

        # 2. Keyword & Token SQL Search
        keywords = [w for w in query_words if w not in ["need", "procure", "tender", "supply", "purchase", "the", "for", "with", "and", "under", "nos", "units", "government", "hospital", "project"]]
        if keywords:
            for kw in keywords[:8]:
                kw_matches = self.db.query(Standard).filter(
                    or_(
                        Standard.title.ilike(f"%{kw}%"),
                        Standard.scope.ilike(f"%{kw}%"),
                        Standard.standard_number.ilike(f"%{kw}%")
                    )
                ).limit(20).all()
                for km in kw_matches:
                    t_lower = (km.title + " " + (km.scope or "")).lower()
                    overlap = sum(1 for k in keywords if k in t_lower)
                    score = 0.5 + 0.15 * overlap
                    if km.id not in candidates_map:
                        candidates_map[km.id] = self._serialize_standard(km, base_score=score, match_type="keyword_fts")
                    else:
                        candidates_map[km.id]["search_score"] = max(candidates_map[km.id]["search_score"], score)

        # 3. Vector Semantic Search
        vector_results = self.vector_engine.search(query_clean, top_k=top_k * 2)
        for doc_id, sim_score in vector_results:
            if doc_id not in candidates_map:
                std = self.db.query(Standard).filter(Standard.id == doc_id).first()
                if std:
                    candidates_map[doc_id] = self._serialize_standard(std, base_score=sim_score, match_type="semantic_vector")
            else:
                candidates_map[doc_id]["search_score"] = max(candidates_map[doc_id]["search_score"], sim_score)

        candidate_list = list(candidates_map.values())

        # 4. Apply Reranking
        ranked_results = StandardsReranker.rerank(
            candidates=candidate_list,
            query=query_clean,
            detected_domain=domain_filter,
            detected_is_numbers=is_numbers
        )

        # 5. Precision threshold filtering
        filtered_ranked = []
        for cand in ranked_results:
            cand_text = (cand.get("title", "") + " " + cand.get("scope", "") + " " + cand.get("standard_number", "")).lower()
            has_kw_match = any(kw in cand_text for kw in keywords) if keywords else True
            is_exact = cand.get("match_type") == "exact_identifier"
            if has_kw_match or is_exact or cand.get("final_score", 0) >= 0.7:
                filtered_ranked.append(cand)

        return filtered_ranked[:top_k]

    def _serialize_standard(self, std: Standard, base_score: float, match_type: str) -> Dict[str, Any]:
        # Synthesize Lifecycle Timeline
        timeline = []
        if std.publication_year:
            timeline.append(f"Published in {std.publication_year}")
        if std.revision_count and std.revision_count > 0:
            timeline.append(f"{std.revision_text} ({std.revision_count})")
        if std.reaffirmed_year:
            timeline.append(f"Reviewed & Reaffirmed in {std.reaffirmed_year}")
        
        amd_list = []
        for a in std.amendments:
            amd_str = f"{a.amendment_number} ({a.amendment_year})" if a.amendment_year else a.amendment_number
            timeline.append(f"Amendment: {amd_str}")
            amd_list.append({
                "amendment_number": a.amendment_number,
                "amendment_year": a.amendment_year,
                "title": a.title,
                "status": a.status,
                "source_url": a.source_url
            })

        timeline.append(f"Current Status: {std.status}")

        return {
            "id": std.id,
            "standard_number": std.standard_number,
            "title": std.title,
            "publication_year": std.publication_year,
            "reaffirmed_year": std.reaffirmed_year,
            "no_of_amendments": std.no_of_amendments or len(amd_list),
            "revision_count": std.revision_count or 0,
            "revision_text": std.revision_text or "Original Publication",
            "supersedes_is": std.supersedes_is,
            "superseded_by_is": std.superseded_by_is,
            "certification_scheme": std.certification_scheme or "Mandatory ISI Scheme-I",
            "lifecycle_timeline": timeline,
            "status": std.status,
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
