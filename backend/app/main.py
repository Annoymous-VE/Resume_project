from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.repositories.database import init_db
from app.api.routes import resume, projects, interview, case_study, auth, dashboard

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    await init_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend-first system that parses arbitrary resumes, extracts technical projects, conducts an adaptive interview, and generates comprehensive technical case studies.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend communication (localhost + deployed Vercel and Render links)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$|^https://.*(\.vercel\.app|\.onrender\.com)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(resume.router)
app.include_router(projects.router)
app.include_router(interview.router)
app.include_router(case_study.router)

@app.get("/api/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "llm_provider": settings.LLM_PROVIDER
    }
