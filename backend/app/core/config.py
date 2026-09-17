import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI-Powered Indian Standards Discovery & Recommendation Engine"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/bis_standards.db")
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    CACHE_DIR: str = "./data/cache"
    REQUEST_DELAY_SECONDS: float = 1.0

    class Config:
        case_sensitive = True

settings = Settings()
