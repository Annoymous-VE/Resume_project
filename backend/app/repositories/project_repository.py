from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.entities import Resume, Project, ProjectKnowledgeRecord

class ProjectRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_resume(
        self,
        filename: str,
        file_path: str,
        file_type: str,
        raw_structure: dict,
        user_id: Optional[str] = None
    ) -> Resume:
        resume = Resume(
            filename=filename,
            file_path=file_path,
            file_type=file_type,
            raw_structure=raw_structure,
            user_id=user_id
        )
        self.db.add(resume)
        await self.db.flush()
        return resume

    async def get_resume(self, resume_id: str, user_id: Optional[str] = None) -> Optional[Resume]:
        query = select(Resume).where(Resume.id == resume_id)
        if user_id:
            query = query.where(Resume.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_all_resumes(self, user_id: Optional[str] = None) -> List[Resume]:
        from sqlalchemy.orm import selectinload
        query = select(Resume).options(selectinload(Resume.projects)).order_by(Resume.created_at.desc())
        if user_id:
            query = query.where(Resume.user_id == user_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_latest_resume(self, user_id: Optional[str] = None) -> Optional[Resume]:
        query = select(Resume).order_by(Resume.created_at.desc())
        if user_id:
            query = query.where(Resume.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def create_project(
        self,
        resume_id: Optional[str],
        name: str,
        description: Optional[str],
        data_json: dict,
        confidence: float = 1.0,
        id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Project:
        params = {
            "resume_id": resume_id,
            "name": name,
            "description": description,
            "data_json": data_json,
            "confidence": confidence,
            "user_id": user_id
        }
        if id:
            params["id"] = id
        project = Project(**params)
        self.db.add(project)
        await self.db.flush()
        return project

    async def get_projects_by_resume(self, resume_id: str, user_id: Optional[str] = None) -> List[Project]:
        query = select(Project).where(Project.resume_id == resume_id)
        if user_id:
            query = query.where(Project.user_id == user_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_all_projects(self, user_id: Optional[str] = None) -> List[Project]:
        query = select(Project).order_by(Project.created_at.desc())
        if user_id:
            query = query.where(Project.user_id == user_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_project(self, project_id: str, user_id: Optional[str] = None) -> Optional[Project]:
        query = select(Project).where(Project.id == project_id)
        if user_id:
            query = query.where(Project.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_dashboard_projects(self, user_id: Optional[str] = None) -> List[Project]:
        from sqlalchemy.orm import selectinload
        from app.models.entities import InterviewSession
        query = (
            select(Project)
            .options(
                selectinload(Project.resume),
                selectinload(Project.interview_session).selectinload(InterviewSession.exchanges),
                selectinload(Project.case_studies)
            )
            .order_by(Project.created_at.desc())
        )
        if user_id:
            query = query.where(Project.user_id == user_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def delete_resume(self, resume_id: str, user_id: Optional[str] = None) -> bool:
        query = select(Resume).where(Resume.id == resume_id)
        if user_id:
            query = query.where(Resume.user_id == user_id)
        result = await self.db.execute(query)
        resume = result.scalars().first()
        if resume:
            await self.db.delete(resume)
            await self.db.flush()
            return True
        return False

    async def delete_project(self, project_id: str, user_id: Optional[str] = None) -> bool:
        query = select(Project).where(Project.id == project_id)
        if user_id:
            query = query.where(Project.user_id == user_id)
        result = await self.db.execute(query)
        project = result.scalars().first()
        if project:
            await self.db.delete(project)
            await self.db.flush()
            return True
        return False

    async def save_knowledge(self, project_id: str, knowledge_json: dict) -> ProjectKnowledgeRecord:
        result = await self.db.execute(select(ProjectKnowledgeRecord).where(ProjectKnowledgeRecord.project_id == project_id))
        record = result.scalars().first()
        if record:
            record.knowledge_json = knowledge_json
        else:
            record = ProjectKnowledgeRecord(project_id=project_id, knowledge_json=knowledge_json)
            self.db.add(record)
        await self.db.flush()
        return record

    async def get_knowledge(self, project_id: str) -> Optional[ProjectKnowledgeRecord]:
        result = await self.db.execute(select(ProjectKnowledgeRecord).where(ProjectKnowledgeRecord.project_id == project_id))
        return result.scalars().first()
