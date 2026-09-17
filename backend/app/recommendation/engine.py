import time
import re
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.app.recommendation.nlp_extractor import ProcurementNLPExtractor
from backend.app.retrieval.search_engine import HybridSearchEngine
from backend.app.ingestion.crawler import BISCrawler
from backend.app.ingestion.pipeline import IngestionPipeline
from backend.app.schemas.standard_schemas import (
    ProcurementRequirementRequest,
    RecommendationResponse,
    RecommendationItem,
    ReferenceSchema,
    AmendmentSchema,
    ExtractedEntities
)

class ProcurementRecommendationEngine:
    """
    Universal grounded recommendation engine for SIH26108.
    Extracts complete lifecycle, amendment records, revision history, and certification schemes.
    """

    def __init__(self, db: Session):
        self.db = db
        self.search_engine = HybridSearchEngine(db)
        self.crawler = BISCrawler()
        self.pipeline = IngestionPipeline(db)

    def recommend(self, req: ProcurementRequirementRequest) -> RecommendationResponse:
        start_time = time.time()

        # 1. NLP Understanding & Entity Extraction
        entities: ExtractedEntities = ProcurementNLPExtractor.extract_entities(req.requirement)
        domain = req.domain_hint or entities.domain

        # 2. Universal Live BIS Discovery for ANY Product Category
        if not req.skip_live_crawl:
            self._ensure_live_bis_discovery(req.requirement, entities)

        # 3. Hybrid Retrieval & Reranking from updated indexed store
        candidates = self.search_engine.search(
            query=req.requirement,
            domain_filter=domain,
            top_k=req.top_k,
            detected_is_numbers=entities.detected_is_numbers
        )

        primary_recommendations: List[RecommendationItem] = []
        allied_references_map: Dict[str, ReferenceSchema] = {}
        safety_guidelines: List[str] = []

        for cand in candidates:
            # 4. Grounded Explanation Generation based strictly on BIS Scope
            why_relevant, evidence_quote = self._generate_grounded_explanation(
                cand=cand,
                entities=entities,
                query=req.requirement
            )

            st_meta = cand.get("safety_testing", {})
            safety_rel = "Safety Critical (Clauses Identified)" if st_meta.get("is_safety_related") else "Quality & Dimension Specification"
            testing_rel = "Prescribes Sampling & Testing Methods" if st_meta.get("is_testing_related") else "Product Specification"

            if st_meta.get("safety_justification"):
                safety_guidelines.append(f"{cand['standard_number']}: {st_meta['safety_justification']}")

            cand_refs = []
            for r in cand.get("references", []):
                ref_obj = ReferenceSchema(
                    referenced_standard_number=r["referenced_standard_number"],
                    referenced_title=r.get("referenced_title"),
                    referenced_year=r.get("referenced_year"),
                    reference_type=r.get("reference_type", "normative"),
                    link=r.get("link")
                )
                cand_refs.append(ref_obj)
                allied_references_map[r["referenced_standard_number"]] = ref_obj

            cand_amds = [
                AmendmentSchema(
                    amendment_number=a["amendment_number"],
                    amendment_year=a.get("amendment_year"),
                    title=a.get("title"),
                    status=a.get("status", "Active"),
                    source_url=a.get("source_url")
                ) for a in cand.get("amendments", [])
            ]

            rec_item = RecommendationItem(
                standard_number=cand["standard_number"],
                title=cand["title"],
                publication_year=cand.get("publication_year"),
                reaffirmed_year=cand.get("reaffirmed_year"),
                no_of_amendments=cand.get("no_of_amendments", len(cand_amds)),
                revision_count=cand.get("revision_count", 0),
                revision_text=cand.get("revision_text", "Original Publication"),
                supersedes_is=cand.get("supersedes_is"),
                superseded_by_is=cand.get("superseded_by_is"),
                certification_scheme=cand.get("certification_scheme", "Mandatory ISI Scheme-I"),
                lifecycle_timeline=cand.get("lifecycle_timeline", []),
                status=cand.get("status", "Active"),
                domain=cand.get("domain"),
                committee_code=cand.get("committee_code"),
                ics_code=cand.get("ics_code"),
                relevance_score=cand.get("final_score", 0.8),
                relevance_tier=cand.get("relevance_tier", "Applicable Standard"),
                why_relevant=why_relevant,
                scope_snippet=cand.get("scope", "")[:300] + "..." if len(cand.get("scope", "")) > 300 else cand.get("scope", ""),
                safety_relevance=safety_rel,
                testing_relevance=testing_rel,
                is_mandatory=cand.get("is_mandatory", False),
                source_url=cand.get("source_url"),
                preview_url=cand.get("preview_url"),
                normative_references=cand_refs[:8],
                amendments=cand_amds,
                evidence_quote=evidence_quote,
                evidence_source_type="Official BIS Standard Preview & Scope"
            )
            primary_recommendations.append(rec_item)

        if not safety_guidelines:
            safety_guidelines.append("Verify mandatory ISI mark certification and conformity to latest Bureau of Indian Standards Quality Control Orders (QCO).")

        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        return RecommendationResponse(
            query=req.requirement,
            extracted_entities=entities,
            primary_recommendations=primary_recommendations,
            allied_references=list(allied_references_map.values())[:12],
            safety_compliance_guidelines=list(set(safety_guidelines))[:5],
            processing_time_ms=elapsed_ms
        )

    def _ensure_live_bis_discovery(self, query: str, entities: ExtractedEntities):
        search_terms = []

        # 1. Add detected IS numbers
        for is_num in entities.detected_is_numbers:
            search_terms.append(is_num)

        # 2. Add product category
        if entities.product_category:
            search_terms.append(entities.product_category)

        # 3. Extract core meaningful words
        words = re.findall(r'[a-zA-Z]+', query.lower())
        meaningful = [w for w in words if len(w) > 2 and w not in ProcurementNLPExtractor.STOP_WORDS]
        
        for w in meaningful:
            if w not in search_terms:
                search_terms.append(w)

        for i in range(len(meaningful) - 1):
            ngram = f"{meaningful[i]} {meaningful[i+1]}"
            if ngram not in search_terms:
                search_terms.append(ngram)

        newly_ingested = False
        seen = set()

        for term in search_terms[:6]:
            if term.lower() in seen:
                continue
            seen.add(term.lower())
            try:
                records = self.crawler.search_keyword(term, max_preview_fetch=3)
                for r in records:
                    self.pipeline.ingest_standard_record(r)
                    newly_ingested = True
            except Exception as e:
                print(f"[LIVE DISCOVERY WARNING] Error searching '{term}': {e}")

        if newly_ingested:
            self.search_engine._refresh_vector_index()

    def _generate_grounded_explanation(self, cand: Dict[str, Any], entities: ExtractedEntities, query: str) -> (str, str):
        std_num = cand.get("standard_number", "")
        title = cand.get("title", "")
        scope = cand.get("scope", "").strip()
        reaffirmed = cand.get("reaffirmed_year")
        rev_text = cand.get("revision_text", "")
        amds = cand.get("amendments", [])

        reasons = []
        if entities.product_category and entities.product_category.lower() in title.lower():
            reasons.append(f"Official product specification for '{entities.product_category}'.")
        else:
            reasons.append(f"Standard '{title}' directly governs this technical specification.")

        if rev_text and rev_text != "Original Publication":
            reasons.append(f"Current version incorporates {rev_text}.")

        if amds:
            amd_str = ", ".join(f"{a['amendment_number']} ({a.get('amendment_year', '')})" for a in amds[:2])
            reasons.append(f"Includes active amendments: {amd_str}.")

        if reaffirmed:
            reasons.append(f"Reviewed & reaffirmed by Technical Committee in {reaffirmed}.")

        if scope:
            reasons.append(f"Official BIS Scope defines: \"{scope[:150]}...\"")

        why_relevant = " ".join(reasons)
        evidence_quote = f"[{std_num}] Scope: {scope}" if scope else f"[{std_num}] Official Title: {title}"

        return why_relevant, evidence_quote
