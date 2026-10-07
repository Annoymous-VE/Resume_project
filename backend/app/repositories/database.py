from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings
from app.models.base import Base
# Ensure all entities are imported before create_all
import app.models.entities # noqa

engine_kwargs = {
    "echo": False,
    "future": True,
    "pool_pre_ping": True,
}
if "postgresql" in settings.DATABASE_URL:
    engine_kwargs["connect_args"] = {"statement_cache_size": 0}

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
        if "sqlite" in str(engine.url):
            from sqlalchemy import text
            try:
                res = await conn.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name='case_study_records'"))
                row = res.fetchone()
                if row and row[0]:
                    sql_def = row[0]
                    # If table contains legacy single-column UNIQUE (project_id), migrate to composite constraint
                    if "UNIQUE (project_id)" in sql_def or "unique (project_id)" in sql_def.lower():
                        await conn.execute(text("PRAGMA foreign_keys=OFF"))
                        await conn.execute(text("""
                            CREATE TABLE case_study_records_v2 (
                                id VARCHAR(36) NOT NULL,
                                project_id VARCHAR(36) NOT NULL,
                                variant_type VARCHAR(50) DEFAULT 'technical' NOT NULL,
                                title VARCHAR(255) NOT NULL,
                                markdown_content TEXT NOT NULL,
                                sections_json JSON NOT NULL,
                                created_at DATETIME,
                                PRIMARY KEY (id),
                                CONSTRAINT uq_project_variant UNIQUE (project_id, variant_type),
                                FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
                            )
                        """))
                        cols_res = await conn.execute(text("PRAGMA table_info(case_study_records)"))
                        cols = [c[1] for c in cols_res.fetchall()]
                        if "variant_type" in cols:
                            await conn.execute(text("""
                                INSERT OR REPLACE INTO case_study_records_v2 (id, project_id, variant_type, title, markdown_content, sections_json, created_at)
                                SELECT id, project_id, COALESCE(variant_type, 'technical'), title, markdown_content, sections_json, created_at
                                FROM case_study_records
                            """))
                        else:
                            await conn.execute(text("""
                                INSERT OR REPLACE INTO case_study_records_v2 (id, project_id, variant_type, title, markdown_content, sections_json, created_at)
                                SELECT id, project_id, 'technical', title, markdown_content, sections_json, created_at
                                FROM case_study_records
                            """))
                        await conn.execute(text("DROP TABLE case_study_records"))
                        await conn.execute(text("ALTER TABLE case_study_records_v2 RENAME TO case_study_records"))
                        await conn.execute(text("PRAGMA foreign_keys=ON"))
                    else:
                        cols_res = await conn.execute(text("PRAGMA table_info(case_study_records)"))
                        cols = [c[1] for c in cols_res.fetchall()]
                        if cols and "variant_type" not in cols:
                            await conn.execute(text("ALTER TABLE case_study_records ADD COLUMN variant_type VARCHAR(50) DEFAULT 'technical' NOT NULL"))

                # Check for user_id columns on resumes and projects
                res_resumes = await conn.execute(text("PRAGMA table_info(resumes)"))
                res_cols = [c[1] for c in res_resumes.fetchall()]
                if res_cols and "user_id" not in res_cols:
                    await conn.execute(text("ALTER TABLE resumes ADD COLUMN user_id VARCHAR(36) REFERENCES users(id)"))

                res_projs = await conn.execute(text("PRAGMA table_info(projects)"))
                proj_cols = [c[1] for c in res_projs.fetchall()]
                if proj_cols and "user_id" not in proj_cols:
                    await conn.execute(text("ALTER TABLE projects ADD COLUMN user_id VARCHAR(36) REFERENCES users(id)"))
            except Exception as e:
                import logging
                logging.getLogger("app.database").warning(f"SQLite migration check notice: {e}")


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
