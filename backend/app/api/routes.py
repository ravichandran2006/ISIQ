from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
import os
import io
import time
import pypdf

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
from backend.app.recommendation.llm_explainer import LLMStandardsExplainer, ExplainStandardRequest, ExplainStandardResponse
from backend.app.ingestion.crawler import BISCrawler
from backend.app.ingestion.pipeline import IngestionPipeline
from backend.app.nlp.indic_translator import IndicTranslator
from pydantic import BaseModel

class TranslationRequest(BaseModel):
    text: str
    target_language: str
    source_language: Optional[str] = "en"

class TranslationResponse(BaseModel):
    original_text: str
    translated_text: str
    source_language: str
    target_language: str

router = APIRouter()

@router.get("/health", tags=["System"])
def health_check(db: Session = Depends(get_db)):
    std_count = db.query(Standard).count()
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    return {
        "status": "healthy",
        "service": "AI-Powered Indian Standards Recommendation Engine (SIH26108)",
        "total_standards_indexed": std_count,
        "database_connected": True,
        "groq_configured": bool(groq_key and groq_key != "your_groq_api_key_here"),
        "default_llm_provider": os.getenv("DEFAULT_LLM_PROVIDER", "groq"),
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
    domains = db.query(Standard.domain).distinct().all()
    committees = db.query(Standard.committee_code).distinct().all()
    return {
        "domains": [d[0] for d in domains if d[0]],
        "technical_committees": [c[0] for c in committees if c[0]]
    }

@router.post("/search", tags=["Retrieval"])
def search_standards(body: SearchQuery, db: Session = Depends(get_db)):
    search_engine = HybridSearchEngine(db)
    detected_lang = IndicTranslator.detect_language(body.query)
    search_query = body.query
    translated_query = None
    if detected_lang != "en":
        translated_query, _ = IndicTranslator.translate_to_english(body.query, source_lang=detected_lang)
        search_query = translated_query

    results = search_engine.search(
        query=search_query,
        domain_filter=body.domain,
        top_k=body.limit
    )
    return {
        "query": body.query,
        "detected_language": detected_lang,
        "translated_query": translated_query,
        "total_results": len(results),
        "results": results
    }

@router.post("/recommend", response_model=RecommendationResponse, tags=["Recommendation"])
def recommend_standards(body: ProcurementRequirementRequest, db: Session = Depends(get_db)):
    detected_lang = IndicTranslator.detect_language(body.requirement)
    translated_query = None
    exec_requirement = body.requirement
    if detected_lang != "en":
        raw_translated, _ = IndicTranslator.translate_to_english(body.requirement, source_lang=detected_lang)
        from backend.app.recommendation.nlp_extractor import ProcurementNLPExtractor
        exec_requirement = ProcurementNLPExtractor.canonicalize_query(raw_translated)
        translated_query = exec_requirement

    internal_req = ProcurementRequirementRequest(
        requirement=exec_requirement,
        domain_hint=body.domain_hint,
        top_k=body.top_k,
        skip_live_crawl=body.skip_live_crawl
    )

    engine = ProcurementRecommendationEngine(db)
    res = engine.recommend(internal_req)
    # Restore original natural query in response metadata
    res.query = body.requirement
    res.detected_language = detected_lang
    res.translated_query = translated_query
    return res

@router.post("/translate", response_model=TranslationResponse, tags=["Multilingual"])
def translate_text(body: TranslationRequest):
    """
    Multilingual translation service supporting 16 Indian languages.
    Used by the frontend to translate explanations, summaries, and procurement requirements.
    """
    target = body.target_language.lower()
    source = (body.source_language or "en").lower()

    if target == source:
        return TranslationResponse(
            original_text=body.text,
            translated_text=body.text,
            source_language=source,
            target_language=target
        )

    if target == "en":
        trans, detected = IndicTranslator.translate_to_english(body.text, source_lang=source)
    else:
        # First ensure English base if text is in another Indian language
        en_base = body.text
        if source != "en":
            en_base, _ = IndicTranslator.translate_to_english(body.text, source_lang=source)
        trans = IndicTranslator.translate_from_english(en_base, target_lang=target)
        detected = source

    return TranslationResponse(
        original_text=body.text,
        translated_text=trans,
        source_language=source,
        target_language=target
    )

@router.post("/explain-standard", response_model=ExplainStandardResponse, tags=["AI Explanation"])
async def explain_standard_recommendation(
    body: ExplainStandardRequest,
    db: Session = Depends(get_db)
):
    """
    AI-powered grounded explanation service.
    Explains exactly why an Indian Standard is recommended for a technical procurement specification.
    Supports Google Gemini, Groq, OpenAI, and StandIQ Grounded Intelligence.
    """
    return await LLMStandardsExplainer.explain(body)

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

@router.post("/upload-document", tags=["Ingestion"])
async def upload_document(file: UploadFile = File(...)):
    filename = file.filename or "uploaded_document"
    contents = await file.read()
    text = ""
    page_count = 1
    
    if filename.lower().endswith(".pdf"):
        try:
            reader = pypdf.PdfReader(io.BytesIO(contents))
            page_count = len(reader.pages)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        except Exception as e:
            text = f"Error reading PDF: {str(e)}"
    else:
        try:
            text = contents.decode("utf-8", errors="ignore")
        except Exception as e:
            text = str(contents)
            
    clean_text = text.strip()
    detected_lang = IndicTranslator.detect_language(clean_text)
    translated_summary = ""
    if detected_lang != "en" and clean_text:
        translated_summary, _ = IndicTranslator.translate_to_english(clean_text[:2000], source_lang=detected_lang)

    return {
        "filename": filename,
        "size_bytes": len(contents),
        "page_count": page_count,
        "extracted_text": clean_text,
        "detected_language": detected_lang,
        "language_name": IndicTranslator.LANGUAGE_NAMES.get(detected_lang, "English"),
        "translated_summary": translated_summary
    }
