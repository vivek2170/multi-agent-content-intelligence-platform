from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    LLM_PROVIDER: str = "ollama"
    LLM_MODEL: str = "llama3.2:3b"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    SEARCH_PROVIDER: str = "mock"
    TAVILY_API_KEY: str = ""
    DATABASE_URL: str = "sqlite:///./data/contentforge.db"
    MAX_REVISIONS: int = 3
    LLM_TIMEOUT_SECONDS: int = 180
    SEARCH_TIMEOUT_SECONDS: int = 20
    WORKFLOW_TIMEOUT_SECONDS: int = 600
    LOG_LEVEL: str = "INFO"

settings = Settings()
