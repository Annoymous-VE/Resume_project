from pathlib import Path
import os
from pydantic import BaseModel
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
STORAGE_DIR = PROJECT_ROOT / "storage"
UPLOADS_DIR = STORAGE_DIR / "uploads"
GENERATED_DIR = STORAGE_DIR / "generated"

# Load backend/.env explicitly
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(PROJECT_ROOT / ".env")

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

def _get_cors_origins() -> list[str]:
    origins = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "https://resume-project-sooty-eta.vercel.app",
        "https://resume-project-osw9.onrender.com",
    ]
    custom = os.getenv("CORS_ORIGINS", "")
    if custom:
        for item in custom.split(","):
            cleaned = item.strip()
            if cleaned and cleaned not in origins:
                origins.append(cleaned)
    return origins

class Settings(BaseModel):
    PROJECT_NAME: str = "Resume-to-Technical-Case-Study System"
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{STORAGE_DIR / 'app.db'}")
    
    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "mock").strip()  # "gemini", "openai", or "mock"
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "").strip()
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "").strip()
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-3.5-flash-lite").strip()

    # Interview defaults (7 rounds max guarantees high efficiency without infinite loops)
    MAX_INTERVIEW_ROUNDS: int = int(os.getenv("MAX_INTERVIEW_ROUNDS", "7"))

    # CORS settings
    CORS_ORIGINS: list[str] = _get_cors_origins()

settings = Settings()

