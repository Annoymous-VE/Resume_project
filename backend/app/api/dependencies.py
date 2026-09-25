from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.database import get_db
from app.repositories.project_repository import ProjectRepository
from app.repositories.interview_repository import InterviewRepository
from app.repositories.case_study_repository import CaseStudyRepository
from app.ai.llm import get_llm_client, BaseLLMClient
from app.services.resume_parser import ResumeParser
from app.services.project_extractor import ProjectExtractor
from app.services.knowledge_manager import KnowledgeManager
from app.services.interview_engine import InterviewEngine
from app.services.case_study_generator import CaseStudyGenerator

def get_project_repo(db: AsyncSession = Depends(get_db)) -> ProjectRepository:
    return ProjectRepository(db)

def get_interview_repo(db: AsyncSession = Depends(get_db)) -> InterviewRepository:
    return InterviewRepository(db)

def get_case_study_repo(db: AsyncSession = Depends(get_db)) -> CaseStudyRepository:
    return CaseStudyRepository(db)

def get_llm() -> BaseLLMClient:
    return get_llm_client()

def get_resume_parser() -> ResumeParser:
    return ResumeParser()

def get_project_extractor(llm: BaseLLMClient = Depends(get_llm)) -> ProjectExtractor:
    return ProjectExtractor(llm)

def get_knowledge_manager(llm: BaseLLMClient = Depends(get_llm)) -> KnowledgeManager:
    return KnowledgeManager(llm)

def get_interview_engine(llm: BaseLLMClient = Depends(get_llm)) -> InterviewEngine:
    return InterviewEngine(llm)

def get_case_study_generator(llm: BaseLLMClient = Depends(get_llm)) -> CaseStudyGenerator:
    return CaseStudyGenerator(llm)
