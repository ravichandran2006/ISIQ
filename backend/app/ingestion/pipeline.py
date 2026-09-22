import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from backend.app.database.models import Standard, StandardReference, Amendment, SafetyTestingMetadata, IngestionLog
from backend.app.ingestion.crawler import BISCrawler
from backend.app.recommendation.certification_engine import CertificationRequirementEngine

class IngestionPipeline:
    """
    Coordinates ingestion of parsed BIS standard documents, amendment records,
    and lifecycle metadata into the relational database.
    """

    def __init__(self, db: Session):
        self.db = db
        self.crawler = BISCrawler()

    def ingest_standard_record(self, record: Dict[str, Any]) -> Standard:
        std_num = record["standard_number"]
        
        # Determine dynamic certification scheme and mandatory status if not explicitly in record
        cert_info = CertificationRequirementEngine.evaluate_standard(
            standard_number=std_num,
            title=record.get("title", ""),
            scope=record.get("scope", ""),
            domain=record.get("domain", "")
        )
        scheme = record.get("certification_scheme") or cert_info["certification_scheme"]
        is_mandatory = record.get("is_mandatory", cert_info["is_mandatory"])

        # Check if already exists
        existing = self.db.query(Standard).filter(Standard.standard_number == std_num).first()
        if existing:
            existing.title = record.get("title", existing.title)
            existing.publication_year = record.get("publication_year", existing.publication_year)
            existing.reaffirmed_year = record.get("reaffirmed_year", existing.reaffirmed_year)
            existing.no_of_amendments = record.get("no_of_amendments", len(record.get("amendments", [])))
            existing.revision_count = record.get("revision_count", existing.revision_count)
            existing.revision_text = record.get("revision_text", existing.revision_text)
            existing.supersedes_is = record.get("supersedes_is", existing.supersedes_is)
            existing.superseded_by_is = record.get("superseded_by_is", existing.superseded_by_is)
            existing.certification_scheme = scheme
            existing.is_mandatory = is_mandatory
            existing.scope = record.get("scope", existing.scope)
            existing.ics_code = record.get("ics_code", existing.ics_code)
            existing.committee_code = record.get("committee_code", existing.committee_code)
            existing.domain = record.get("domain", existing.domain)
            existing.status = record.get("status", existing.status)
            existing.preview_url = record.get("preview_url", existing.preview_url)
            existing.source_url = record.get("source_url", existing.source_url)
            existing.last_verified_at = datetime.datetime.utcnow()
            std_obj = existing
        else:
            std_obj = Standard(
                standard_number=std_num,
                title=record.get("title", ""),
                publication_year=record.get("publication_year"),
                reaffirmed_year=record.get("reaffirmed_year"),
                no_of_amendments=record.get("no_of_amendments", len(record.get("amendments", []))),
                revision_count=record.get("revision_count", 0),
                revision_text=record.get("revision_text", "Original Publication"),
                supersedes_is=record.get("supersedes_is"),
                superseded_by_is=record.get("superseded_by_is"),
                certification_scheme=scheme,
                is_mandatory=is_mandatory,
                scope=record.get("scope"),
                ics_code=record.get("ics_code"),
                committee_code=record.get("committee_code"),
                domain=record.get("domain"),
                status=record.get("status", "Active"),
                preview_url=record.get("preview_url"),
                source_url=record.get("source_url"),
                last_verified_at=datetime.datetime.utcnow()
            )
            self.db.add(std_obj)
            self.db.flush()

        # Ingest References
        for ref in record.get("references", []):
            ref_num = ref.get("standard_number")
            if ref_num:
                existing_ref = self.db.query(StandardReference).filter(
                    StandardReference.standard_id == std_obj.id,
                    StandardReference.referenced_standard_number == ref_num
                ).first()
                if not existing_ref:
                    ref_obj = StandardReference(
                        standard_id=std_obj.id,
                        referenced_standard_number=ref_num,
                        referenced_title=ref.get("title"),
                        referenced_year=ref.get("year"),
                        reference_type=ref.get("reference_type", "normative"),
                        link=ref.get("link")
                    )
                    self.db.add(ref_obj)

        # Ingest Amendments
        for amd in record.get("amendments", []):
            amd_num = amd.get("amendment_number")
            if amd_num:
                existing_amd = self.db.query(Amendment).filter(
                    Amendment.standard_id == std_obj.id,
                    Amendment.amendment_number == amd_num
                ).first()
                if not existing_amd:
                    amd_obj = Amendment(
                        standard_id=std_obj.id,
                        amendment_number=amd_num,
                        amendment_year=amd.get("amendment_year"),
                        publication_date=amd.get("publication_date"),
                        committee_code=amd.get("committee_code"),
                        title=amd.get("title"),
                        status=amd.get("status", "Active"),
                        source_url=amd.get("source_url")
                    )
                    self.db.add(amd_obj)
                else:
                    existing_amd.amendment_year = amd.get("amendment_year") or existing_amd.amendment_year
                    existing_amd.publication_date = amd.get("publication_date") or existing_amd.publication_date
                    existing_amd.committee_code = amd.get("committee_code") or existing_amd.committee_code
                    existing_amd.title = amd.get("title") or existing_amd.title
                    existing_amd.status = amd.get("status") or existing_amd.status

        # Ingest Safety & Testing Metadata
        st_data = record.get("safety_testing", {})
        if st_data:
            existing_st = self.db.query(SafetyTestingMetadata).filter(SafetyTestingMetadata.standard_id == std_obj.id).first()
            if not existing_st:
                st_obj = SafetyTestingMetadata(
                    standard_id=std_obj.id,
                    is_safety_related=st_data.get("is_safety_related", False),
                    is_testing_related=st_data.get("is_testing_related", False),
                    is_sampling_related=st_data.get("is_sampling_related", False),
                    is_quality_spec=st_data.get("is_quality_spec", True),
                    safety_justification=st_data.get("safety_justification"),
                    testing_methods_summary=st_data.get("testing_methods_summary"),
                    source_type=st_data.get("source_type", "rule_based")
                )
                self.db.add(st_obj)

        # Log ingestion
        log = IngestionLog(
            standard_number=std_num,
            action="INGEST",
            status="SUCCESS",
            message=f"Successfully ingested {std_num} with {len(record.get('references', []))} references and {len(record.get('amendments', []))} amendments."
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(std_obj)
        return std_obj
