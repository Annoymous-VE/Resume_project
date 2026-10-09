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
        "https://resume-project-gye0.onrender.com",
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
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{STORAGE_DIR / 'app.db'}").strip().strip("'\"")
    
    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "mock").strip()  # "gemini", "openai", or "mock"
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "").strip()
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "").strip()
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-3.5-flash-lite").strip()

    # Interview defaults (7 rounds max guarantees high efficiency without infinite loops)
    MAX_INTERVIEW_ROUNDS: int = int(os.getenv("MAX_INTERVIEW_ROUNDS", "7"))

    # Auth & JWT Settings
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "resume-case-study-super-secret-jwt-signing-key-32bytes-min-2026")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # Supabase Storage settings
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "").strip()
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_SERVICE", "")).strip()
    SUPABASE_STORAGE_BUCKET: str = os.getenv("SUPABASE_STORAGE_BUCKET", "Resumes").strip()

    # CORS settings
    CORS_ORIGINS: list[str] = _get_cors_origins()

settings = Settings()

