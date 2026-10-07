from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.database import get_db
from app.models.entities import User
from app.repositories.user_repository import UserRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.interview_repository import InterviewRepository
from app.repositories.case_study_repository import CaseStudyRepository
from app.services.auth_service import decode_token
from app.ai.llm import get_llm_client, BaseLLMClient
from app.services.resume_parser import ResumeParser
from app.services.project_extractor import ProjectExtractor
from app.services.knowledge_manager import KnowledgeManager
from app.services.interview_engine import InterviewEngine
from app.services.case_study_generator import CaseStudyGenerator
from app.services.storage_manager import StorageManager

security = HTTPBearer(auto_error=False)

def get_user_repo(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    user_repo: UserRepository = Depends(get_user_repo)
) -> User:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(credentials.credentials, expected_type="access")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    user_repo: UserRepository = Depends(get_user_repo)
) -> Optional[User]:
    if not credentials or not credentials.credentials:
        return None
    try:
        payload = decode_token(credentials.credentials, expected_type="access")
        user_id = payload.get("sub")
        if not user_id:
            return None
        return await user_repo.get_by_id(user_id)
    except Exception:
        return None

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

def get_storage_manager() -> StorageManager:
    return StorageManager()
