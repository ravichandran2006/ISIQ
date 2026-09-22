import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Ensure .env is loaded from project root or backend folder
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(ROOT_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env")
load_dotenv()  # Fallback to CWD

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI-Powered Indian Standards Discovery & Recommendation Engine"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/bis_standards.db")
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    CACHE_DIR: str = "./data/cache"
    REQUEST_DELAY_SECONDS: float = 1.0

    # LLM & AI Recommendation Settings
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    DEFAULT_LLM_PROVIDER: str = os.getenv("DEFAULT_LLM_PROVIDER", "groq")

    class Config:
        case_sensitive = True
        extra = "allow"

settings = Settings()
