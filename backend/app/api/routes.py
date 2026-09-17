import time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.database.models import Standard, StandardReference, Amendment, IngestionLog
from backend.app.schemas.standard_schemas import (
    StandardOut,
    SearchQuery,
    ProcurementRequirementRequest,
    RecommendationResponse,
    ReferenceSchema,
    AmendmentSchema
)
from backend.app.retrieval.search_engine import HybridSearchEngine
from backend.app.recommendation.engine import ProcurementRecommendationEngine
from backend.app.ingestion.crawler import BISCrawler
from backend.app.ingestion.pipeline import IngestionPipeline

router = APIRouter()

@router.get("/health", tags=["System"])
def health_check(db: Session = Depends(get_db)):
    std_count = db.query(Standard).count()
    return {
        "status": "healthy",
        "service": "AI-Powered Indian Standards Recommendation Engine (SIH26108)",
        "total_standards_indexed": std_count,
        "database_connected": True,
        "timestamp": time.time()
    }

@router.get("/standards", response_model=List[StandardOut], tags=["Standards"])
def list_standards(
    skip: int = 0,
    limit: int = 50,
    domain: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Standard)
    if domain:
        query = query.filter(Standard.domain == domain)
    return query.offset(skip).limit(limit).all()

@router.get("/standards/{standard_number}", response_model=StandardOut, tags=["Standards"])
def get_standard(standard_number: str, db: Session = Depends(get_db)):
    std = db.query(Standard).filter(Standard.standard_number.ilike(standard_number.strip())).first()
    if not std:
        raise HTTPException(status_code=404, detail=f"Standard '{standard_number}' not found in database.")
    return std

@router.get("/standards/{standard_number}/references", response_model=List[ReferenceSchema], tags=["Standards"])
def get_standard_references(standard_number: str, db: Session = Depends(get_db)):
    std = db.query(Standard).filter(Standard.standard_number.ilike(standard_number.strip())).first()
    if not std:
        raise HTTPException(status_code=404, detail=f"Standard '{standard_number}' not found.")
    return std.references

@router.get("/standards/{standard_number}/amendments", response_model=List[AmendmentSchema], tags=["Standards"])
def get_standard_amendments(
    standard_number: str,
    live_fetch: bool = Query(False, description="Whether to query live BIS Free Amendments portal"),
    db: Session = Depends(get_db)
):
    std = db.query(Standard).filter(Standard.standard_number.ilike(standard_number.strip())).first()
    if not std and not live_fetch:
        raise HTTPException(status_code=404, detail=f"Standard '{standard_number}' not found.")
    
    # If live_fetch is True or standard has no amendments recorded, attempt live fetch
    if live_fetch or (std and not std.amendments):
        crawler = BISCrawler()
        live_amds = crawler.fetch_free_amendments(standard_number.strip())
        if live_amds and std:
            for amd in live_amds:
                existing_amd = db.query(Amendment).filter(
                    Amendment.standard_id == std.id,
                    Amendment.amendment_number == amd["amendment_number"]
                ).first()
                if not existing_amd:
                    db.add(Amendment(
                        standard_id=std.id,
                        amendment_number=amd["amendment_number"],
                        amendment_year=amd.get("amendment_year"),
                        publication_date=amd.get("publication_date"),
                        committee_code=amd.get("committee_code"),
                        title=amd.get("title"),
                        status=amd.get("status", "Active"),
                        source_url=amd.get("source_url")
                    ))
                else:
                    existing_amd.publication_date = amd.get("publication_date") or existing_amd.publication_date
                    existing_amd.committee_code = amd.get("committee_code") or existing_amd.committee_code
            std.no_of_amendments = len(live_amds)
            db.commit()
            db.refresh(std)

    if std:
        return std.amendments
    elif live_amds:
        return [
            AmendmentSchema(
                amendment_number=a["amendment_number"],
                amendment_year=a.get("amendment_year"),
                publication_date=a.get("publication_date"),
                committee_code=a.get("committee_code"),
                title=a.get("title"),
                status=a.get("status", "Active"),
                source_url=a.get("source_url")
            ) for a in live_amds
        ]
    return []


@router.get("/classifications", tags=["Classifications"])
def list_classifications(db: Session = Depends(get_db)):
    # Group standards by domain
    domains = db.query(Standard.domain).distinct().all()
    committees = db.query(Standard.committee_code).distinct().all()
    return {
        "domains": [d[0] for d in domains if d[0]],
        "technical_committees": [c[0] for c in committees if c[0]]
    }

@router.post("/search", tags=["Retrieval"])
def search_standards(body: SearchQuery, db: Session = Depends(get_db)):
    search_engine = HybridSearchEngine(db)
    results = search_engine.search(
        query=body.query,
        domain_filter=body.domain,
        top_k=body.limit
    )
    return {
        "query": body.query,
        "total_results": len(results),
        "results": results
    }

@router.post("/recommend", response_model=RecommendationResponse, tags=["Recommendation"])
def recommend_standards(body: ProcurementRequirementRequest, db: Session = Depends(get_db)):
    engine = ProcurementRecommendationEngine(db)
    return engine.recommend(body)

@router.post("/ingestion/crawl-and-ingest", tags=["Ingestion"])
def run_ingestion_crawl(keyword: str = Query(..., description="Keyword to search on BIS portal"), db: Session = Depends(get_db)):
    crawler = BISCrawler()
    pipeline = IngestionPipeline(db)
    records = crawler.search_keyword(keyword)
    ingested = []
    for r in records:
        std = pipeline.ingest_standard_record(r)
        ingested.append(std.standard_number)
    return {
        "status": "success",
        "keyword": keyword,
        "discovered_records": len(records),
        "ingested_standards": ingested
    }

@router.get("/evaluation/benchmark", tags=["Evaluation"])
def run_evaluation_benchmark(db: Session = Depends(get_db)):
    from backend.app.evaluation.benchmark import BenchmarkEvaluator
    evaluator = BenchmarkEvaluator(db)
    return evaluator.run_benchmark()

