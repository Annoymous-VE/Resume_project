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
        storage_key: Optional[str] = None,
        mime_type: Optional[str] = None,
        file_url: Optional[str] = None
    ) -> Resume:
        resume = Resume(
            filename=filename,
            file_path=file_path,
            file_type=file_type,
            raw_structure=raw_structure,
            storage_key=storage_key,
            mime_type=mime_type or "application/pdf",
            file_url=file_url
        )
        self.db.add(resume)
        await self.db.flush()
        return resume

    async def get_resume(self, resume_id: str) -> Optional[Resume]:
        result = await self.db.execute(select(Resume).where(Resume.id == resume_id))
        return result.scalars().first()

    async def get_latest_resume(self) -> Optional[Resume]:
        result = await self.db.execute(select(Resume).order_by(Resume.created_at.desc()))
        return result.scalars().first()

    async def create_project(
        self,
        resume_id: Optional[str],
        name: str,
        description: Optional[str],
        data_json: dict,
        confidence: float = 1.0,
        id: Optional[str] = None
    ) -> Project:
        params = {
            "resume_id": resume_id,
            "name": name,
            "description": description,
            "data_json": data_json,
            "confidence": confidence
        }
        if id:
            params["id"] = id
        project = Project(**params)
        self.db.add(project)
        await self.db.flush()
        return project

    async def get_projects_by_resume(self, resume_id: str) -> List[Project]:
        result = await self.db.execute(select(Project).where(Project.resume_id == resume_id))
        return list(result.scalars().all())

    async def get_all_projects(self) -> List[Project]:
        result = await self.db.execute(select(Project).order_by(Project.created_at.desc()))
        return list(result.scalars().all())

    async def get_project(self, project_id: str) -> Optional[Project]:
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        return result.scalars().first()

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
