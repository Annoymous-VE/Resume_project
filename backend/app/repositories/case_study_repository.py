from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.entities import CaseStudyRecord

class CaseStudyRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_case_study(
        self,
        project_id: str,
        title: str,
        markdown_content: str,
        sections_json: list,
        variant_type: str = "technical"
    ) -> CaseStudyRecord:
        result = await self.db.execute(
            select(CaseStudyRecord).where(
                CaseStudyRecord.project_id == project_id,
                CaseStudyRecord.variant_type == variant_type
            )
        )
        record = result.scalars().first()
        if record:
            record.title = title
            record.markdown_content = markdown_content
            record.sections_json = sections_json
            record.variant_type = variant_type
        else:
            record = CaseStudyRecord(
                project_id=project_id,
                variant_type=variant_type,
                title=title,
                markdown_content=markdown_content,
                sections_json=sections_json
            )
            self.db.add(record)
        await self.db.flush()
        return record

    async def get_case_study(self, project_id: str, variant_type: str = "technical") -> Optional[CaseStudyRecord]:
        result = await self.db.execute(
            select(CaseStudyRecord).where(
                CaseStudyRecord.project_id == project_id,
                CaseStudyRecord.variant_type == variant_type
            )
        )
        return result.scalars().first()

    async def get_all_case_studies(self, project_id: str) -> List[CaseStudyRecord]:
        result = await self.db.execute(
            select(CaseStudyRecord).where(CaseStudyRecord.project_id == project_id).order_by(CaseStudyRecord.created_at)
        )
        return list(result.scalars().all())

