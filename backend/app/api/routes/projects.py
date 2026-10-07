import uuid
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.entities import User
from app.api.dependencies import (
    get_project_repo,
    get_knowledge_manager,
    get_optional_current_user,
    ProjectRepository,
    KnowledgeManager
)
from app.ai.schemas.knowledge import ProjectKnowledge
from app.ai.schemas.project import ExtractedProject

router = APIRouter(prefix="/api/projects", tags=["Projects"])

class ProjectCreateRequest(BaseModel):
    resume_id: Optional[str] = None
    name: str = Field(..., min_length=1, description="Project name")
    description: str = Field(..., min_length=1, description="Project description or summary")
    technologies: List[str] = Field(default_factory=list, description="List of technologies")
    contributions: Optional[List[str]] = Field(default_factory=list, description="Key contributions/tasks")
    outcomes: Optional[List[str]] = Field(default_factory=list, description="Measurable outcomes or metrics")
    links: Optional[List[str]] = Field(default_factory=list, description="Links or repository URLs")

@router.post("", summary="Add an unlisted or custom project manually")
async def create_custom_project(
    req: ProjectCreateRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
    knowledge_manager: KnowledgeManager = Depends(get_knowledge_manager)
):
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Project name cannot be empty.")
    
    desc = req.description.strip()
    if not desc:
        raise HTTPException(status_code=400, detail="Project description cannot be empty.")

    cleaned_techs = [t.strip() for t in req.technologies if t.strip()]
    if not cleaned_techs:
        raise HTTPException(status_code=400, detail="At least one technology must be specified.")

    cleaned_contribs = [c.strip() for c in (req.contributions or []) if c.strip()]
    cleaned_outcomes = [o.strip() for o in (req.outcomes or []) if o.strip()]
    cleaned_links = [l.strip() for l in (req.links or []) if l.strip()]

    user_id = current_user.id if current_user else None

    resume_id = req.resume_id
    if resume_id:
        existing_resume = await project_repo.get_resume(resume_id, user_id=user_id)
        if not existing_resume:
            resume_id = None
    
    if not resume_id:
        latest = await project_repo.get_latest_resume(user_id=user_id)
        if latest:
            resume_id = latest.id
        else:
            default_resume = await project_repo.create_resume(
                filename="Manual Projects",
                file_path="",
                file_type="manual",
                raw_structure={},
                user_id=user_id
            )
            resume_id = default_resume.id

    proj_id = str(uuid.uuid4())
    ep = ExtractedProject(
        id=proj_id,
        name=name,
        description=desc,
        technologies=cleaned_techs,
        contributions=cleaned_contribs,
        outcomes=cleaned_outcomes,
        links=cleaned_links,
        source_blocks=["manual_entry"],
        confidence=1.0
    )

    proj = await project_repo.create_project(
        resume_id=resume_id,
        name=ep.name,
        description=ep.description,
        data_json=ep.model_dump(),
        confidence=ep.confidence,
        id=proj_id,
        user_id=user_id
    )

    init_knowledge = knowledge_manager.initialize_knowledge(ep)
    await project_repo.save_knowledge(proj.id, init_knowledge.model_dump())

    return {
        "id": proj.id,
        "resume_id": proj.resume_id,
        "name": proj.name,
        "description": proj.description,
        "technologies": ep.technologies,
        "contributions": ep.contributions,
        "outcomes": ep.outcomes,
        "links": ep.links,
        "confidence": proj.confidence,
        "created_at": proj.created_at.isoformat() if proj.created_at else None
    }


@router.get("", summary="List all extracted projects")
async def list_projects(
    current_user: Optional[User] = Depends(get_optional_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo)
):
    user_id = current_user.id if current_user else None
    projects = await project_repo.get_all_projects(user_id=user_id)
    return [
        {
            "id": p.id,
            "resume_id": p.resume_id,
            "name": p.name,
            "description": p.description,
            "data": p.data_json,
            "confidence": p.confidence,
            "created_at": p.created_at.isoformat() if p.created_at else None
        }
        for p in projects
    ]

@router.get("/{project_id}", summary="Get project details")
async def get_project(
    project_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo)
):
    proj = await project_repo.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found.")
    
    if proj.user_id and current_user and proj.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: this project belongs to another account."
        )

    return {
        "id": proj.id,
        "resume_id": proj.resume_id,
        "name": proj.name,
        "description": proj.description,
        "data": proj.data_json,
        "confidence": proj.confidence,
        "created_at": proj.created_at.isoformat() if proj.created_at else None
    }

@router.get("/{project_id}/knowledge", summary="Get structured project knowledge object and coverage")
async def get_project_knowledge(
    project_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
    knowledge_manager: KnowledgeManager = Depends(get_knowledge_manager)
):
    proj = await project_repo.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found.")

    if proj.user_id and current_user and proj.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: this project belongs to another account."
        )

    record = await project_repo.get_knowledge(project_id)
    if not record:
        raise HTTPException(status_code=404, detail="Project knowledge not found.")

    knowledge_obj = ProjectKnowledge.model_validate(record.knowledge_json)
    coverage = knowledge_manager.compute_coverage(knowledge_obj)

    return {
        "project_id": project_id,
        "knowledge": knowledge_obj.model_dump(),
        "coverage": coverage.model_dump(),
        "updated_at": record.updated_at.isoformat() if record.updated_at else None
    }
