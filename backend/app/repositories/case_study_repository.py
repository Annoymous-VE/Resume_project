from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.entities import CaseStudyRecord

class CaseStudyRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_case_study(self, project_id: str, title: str, markdown_content: str, sections_json: list) -> CaseStudyRecord:
        result = await self.db.execute(select(CaseStudyRecord).where(CaseStudyRecord.project_id == project_id))
        record = result.scalars().first()
        if record:
            record.title = title
            record.markdown_content = markdown_content
            record.sections_json = sections_json
        else:
            record = CaseStudyRecord(
                project_id=project_id,
                title=title,
                markdown_content=markdown_content,
                sections_json=sections_json
            )
            self.db.add(record)
        await self.db.flush()
        return record

    async def get_case_study(self, project_id: str) -> Optional[CaseStudyRecord]:
        result = await self.db.execute(select(CaseStudyRecord).where(CaseStudyRecord.project_id == project_id))
        return result.scalars().first()
