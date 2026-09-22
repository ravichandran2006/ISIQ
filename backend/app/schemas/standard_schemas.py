from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import datetime

class ReferenceSchema(BaseModel):
    referenced_standard_number: str
    referenced_title: Optional[str] = None
    referenced_year: Optional[int] = None
    reference_type: str = "normative"
    link: Optional[str] = None

class AmendmentSchema(BaseModel):
    amendment_number: str
    amendment_year: Optional[int] = None
    publication_date: Optional[str] = None
    committee_code: Optional[str] = None
    title: Optional[str] = None
    status: str = "Active"
    source_url: Optional[str] = None

class SafetyTestingSchema(BaseModel):
    is_safety_related: bool = False
    is_testing_related: bool = False
    is_sampling_related: bool = False
    is_quality_spec: bool = True
    safety_justification: Optional[str] = None
    testing_methods_summary: Optional[str] = None
    source_type: str = "rule_based"

class StandardBase(BaseModel):
    standard_number: str
    title: str
    publication_year: Optional[int] = None
    reaffirmed_year: Optional[int] = None # Reviewed in
    no_of_amendments: int = 0 # Number of amendments
    revision_count: int = 0 # Number of revisions
    revision_text: Optional[str] = "Original Publication"
    supersedes_is: Optional[str] = None # Superseding IS
    superseded_by_is: Optional[str] = None # Superseded by IS
    certification_scheme: Optional[str] = "Mandatory ISI Scheme-I"
    scope: Optional[str] = None
    ics_code: Optional[str] = None
    committee_code: Optional[str] = None
    domain: Optional[str] = None
    status: str = "Active"
    is_mandatory: bool = False
    source_url: Optional[str] = None
    preview_url: Optional[str] = None

class StandardCreate(StandardBase):
    references: List[ReferenceSchema] = []
    amendments: List[AmendmentSchema] = []
    safety_testing: Optional[SafetyTestingSchema] = None

class StandardOut(StandardBase):
    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    last_verified_at: datetime.datetime
    references: List[ReferenceSchema] = []
    amendments: List[AmendmentSchema] = []
    safety_testing: Optional[SafetyTestingSchema] = None

    class Config:
        from_attributes = True

# Search & Recommendation Models
class SearchQuery(BaseModel):
    query: str
    domain: Optional[str] = None
    status_filter: Optional[str] = None
    limit: int = 10
    offset: int = 0

class ProcurementRequirementRequest(BaseModel):
    requirement: str = Field(..., description="Natural language procurement specification or tender description")
    domain_hint: Optional[str] = None
    top_k: int = 5
    skip_live_crawl: bool = False

class ExtractedEntities(BaseModel):
    product_category: Optional[str] = None
    domain: Optional[str] = None
    application_context: Optional[str] = None
    safety_critical: bool = False
    testing_required: bool = False
    quantity: Optional[str] = None
    detected_is_numbers: List[str] = []

class RecommendationItem(BaseModel):
    standard_number: str
    title: str
    publication_year: Optional[int] = None
    reaffirmed_year: Optional[int] = None # Reviewed In
    no_of_amendments: int = 0
    revision_count: int = 0
    revision_text: Optional[str] = "Original Publication"
    supersedes_is: Optional[str] = None
    superseded_by_is: Optional[str] = None
    certification_scheme: Optional[str] = "Mandatory ISI Scheme-I"
    lifecycle_timeline: List[str] = []
    status: str
    domain: Optional[str] = None
    committee_code: Optional[str] = None
    ics_code: Optional[str] = None
    relevance_score: float
    relevance_tier: str
    why_relevant: str
    scope_snippet: Optional[str] = None
    safety_relevance: str
    testing_relevance: str
    is_mandatory: bool = False
    mandate_type: Optional[str] = "QCO"
    governing_order: Optional[str] = None
    mandate_reason: Optional[str] = None
    source_url: Optional[str] = None
    preview_url: Optional[str] = None
    normative_references: List[ReferenceSchema] = []
    amendments: List[AmendmentSchema] = []
    evidence_quote: Optional[str] = None
    evidence_source_type: str = "Official BIS Standard Preview & Scope"

class RecommendationResponse(BaseModel):
    query: str
    extracted_entities: ExtractedEntities
    primary_recommendations: List[RecommendationItem]
    allied_references: List[ReferenceSchema]
    safety_compliance_guidelines: List[str]
    processing_time_ms: float
    detected_language: Optional[str] = "en"
    translated_query: Optional[str] = None
    compliance_summary: Optional[Dict[str, Any]] = None
