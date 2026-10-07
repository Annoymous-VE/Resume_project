import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True, default="")
    created_at = Column(DateTime(timezone=True), default=utc_now)

    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(1024), nullable=False)
    file_type = Column(String(50), nullable=False)
    raw_structure = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    user = relationship("User", back_populates="resumes")
    projects = relationship("Project", back_populates="resume", cascade="all, delete-orphan")

class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    resume_id = Column(String(36), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    data_json = Column(JSON, nullable=False)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    user = relationship("User", back_populates="projects")
    resume = relationship("Resume", back_populates="projects")
    interview_session = relationship("InterviewSession", back_populates="project", uselist=False, cascade="all, delete-orphan")
    knowledge = relationship("ProjectKnowledgeRecord", back_populates="project", uselist=False, cascade="all, delete-orphan")
    case_studies = relationship("CaseStudyRecord", back_populates="project", lazy="selectin", cascade="all, delete-orphan", order_by="CaseStudyRecord.created_at")

    @property
    def case_study(self):
        """Convenience property returning the primary/technical case study for backward compatibility."""
        if not self.case_studies:
            return None
        for cs in self.case_studies:
            if getattr(cs, "variant_type", None) == "technical":
                return cs
        return self.case_studies[-1]

class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True)
    status = Column(String(50), default="in_progress") # in_progress, completed
    round_count = Column(Integer, default=0)
    coverage_json = Column(JSON, nullable=False)
    stop_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    project = relationship("Project", back_populates="interview_session")
    exchanges = relationship("InterviewExchange", back_populates="session", cascade="all, delete-orphan", order_by="InterviewExchange.created_at")

class InterviewExchange(Base):
    __tablename__ = "interview_exchanges"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(String(100), nullable=False)
    target_area = Column(String(100), nullable=False)
    question = Column(Text, nullable=False)
    rationale = Column(Text, nullable=True)
    answer = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    answered_at = Column(DateTime(timezone=True), nullable=True)

    session = relationship("InterviewSession", back_populates="exchanges")

class ProjectKnowledgeRecord(Base):
    __tablename__ = "project_knowledge_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True)
    knowledge_json = Column(JSON, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    project = relationship("Project", back_populates="knowledge")

class CaseStudyRecord(Base):
    __tablename__ = "case_study_records"
    __table_args__ = (
        UniqueConstraint("project_id", "variant_type", name="uq_project_case_study_variant"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    variant_type = Column(String(50), default="technical", nullable=False) # technical, client_brochure
    title = Column(String(255), nullable=False)
    markdown_content = Column(Text, nullable=False)
    sections_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    project = relationship("Project", back_populates="case_studies")
