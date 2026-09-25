import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(1024), nullable=False)
    file_type = Column(String(50), nullable=False)
    raw_structure = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    projects = relationship("Project", back_populates="resume", cascade="all, delete-orphan")

class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    resume_id = Column(String(36), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    data_json = Column(JSON, nullable=False)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    resume = relationship("Resume", back_populates="projects")
    interview_session = relationship("InterviewSession", back_populates="project", uselist=False, cascade="all, delete-orphan")
    knowledge = relationship("ProjectKnowledgeRecord", back_populates="project", uselist=False, cascade="all, delete-orphan")
    case_study = relationship("CaseStudyRecord", back_populates="project", uselist=False, cascade="all, delete-orphan")

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

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True)
    title = Column(String(255), nullable=False)
    markdown_content = Column(Text, nullable=False)
    sections_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    project = relationship("Project", back_populates="case_study")
