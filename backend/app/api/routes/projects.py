from typing import List
from fastapi import APIRouter, Depends, HTTPException
from app.api.dependencies import (
    get_project_repo,
    get_knowledge_manager,
    ProjectRepository,
    KnowledgeManager
)
from app.ai.schemas.knowledge import ProjectKnowledge

router = APIRouter(prefix="/api/projects", tags=["Projects"])

@router.get("", summary="List all extracted projects")
async def list_projects(project_repo: ProjectRepository = Depends(get_project_repo)):
    projects = await project_repo.get_all_projects()
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
async def get_project(project_id: str, project_repo: ProjectRepository = Depends(get_project_repo)):
    proj = await project_repo.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found.")
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
    project_repo: ProjectRepository = Depends(get_project_repo),
    knowledge_manager: KnowledgeManager = Depends(get_knowledge_manager)
):
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
