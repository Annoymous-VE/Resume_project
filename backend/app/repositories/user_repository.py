from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.entities import User

class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: str) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email.strip().lower())
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create(self, email: str, hashed_password: str, full_name: Optional[str] = "") -> User:
        user = User(
            email=email.strip().lower(),
            hashed_password=hashed_password,
            full_name=(full_name or "").strip()
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def list_all(self) -> List[User]:
        stmt = select(User).order_by(User.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
