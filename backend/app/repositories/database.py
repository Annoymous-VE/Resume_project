from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings
from app.models.base import Base
# Ensure all entities are imported before create_all
import app.models.entities # noqa

engine_kwargs = {
    "echo": False,
    "future": True,
}

if "postgresql" in settings.DATABASE_URL:
    engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    })

engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Auto-migrate SQLite schema for newly added columns if table previously existed
        try:
            if "sqlite" in settings.DATABASE_URL:
                from sqlalchemy import text
                res = await conn.execute(text("PRAGMA table_info(resumes)"))
                existing_cols = {row[1] for row in res.fetchall()}
                if "storage_key" not in existing_cols:
                    await conn.execute(text("ALTER TABLE resumes ADD COLUMN storage_key VARCHAR(1024)"))
                if "mime_type" not in existing_cols:
                    await conn.execute(text("ALTER TABLE resumes ADD COLUMN mime_type VARCHAR(100) DEFAULT 'application/pdf'"))
                if "file_url" not in existing_cols:
                    await conn.execute(text("ALTER TABLE resumes ADD COLUMN file_url VARCHAR(2048)"))
        except Exception:
            pass

async def get_db():
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
