from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.entities import InterviewSession, InterviewExchange

class InterviewRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(self, project_id: str, coverage_json: dict) -> InterviewSession:
        session = InterviewSession(
            project_id=project_id,
            status="in_progress",
            round_count=0,
            coverage_json=coverage_json
        )
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_session_by_project(self, project_id: str) -> Optional[InterviewSession]:
        result = await self.db.execute(
            select(InterviewSession)
            .where(InterviewSession.project_id == project_id)
            .options(selectinload(InterviewSession.exchanges))
        )
        return result.scalars().first()

    async def add_exchange(self, session_id: str, question_id: str, target_area: str, question: str, rationale: str) -> InterviewExchange:
        exchange = InterviewExchange(
            session_id=session_id,
            question_id=question_id,
            target_area=target_area,
            question=question,
            rationale=rationale
        )
        self.db.add(exchange)
        await self.db.flush()
        return exchange

    async def record_answer(self, exchange_id: str, answer: str) -> Optional[InterviewExchange]:
        result = await self.db.execute(select(InterviewExchange).where(InterviewExchange.id == exchange_id))
        exchange = result.scalars().first()
        if exchange:
            exchange.answer = answer
            exchange.answered_at = datetime.now(timezone.utc)
            await self.db.flush()
        return exchange

    async def update_session_state(self, session_id: str, coverage_json: dict, round_increment: bool = True, status: Optional[str] = None, stop_reason: Optional[str] = None) -> InterviewSession:
        result = await self.db.execute(select(InterviewSession).where(InterviewSession.id == session_id))
        session = result.scalars().first()
        if session:
            session.coverage_json = coverage_json
            if round_increment:
                session.round_count += 1
            if status:
                session.status = status
            if stop_reason:
                session.stop_reason = stop_reason
            await self.db.flush()
        return session
