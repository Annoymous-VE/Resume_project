from fastapi import APIRouter, Depends, HTTPException
from app.api.dependencies import (
    get_project_repo,
    get_case_study_repo,
    get_case_study_generator,
    ProjectRepository,
    CaseStudyRepository,
    CaseStudyGenerator
)
from app.ai.schemas.knowledge import ProjectKnowledge

router = APIRouter(prefix="/api/projects/{project_id}/case-study", tags=["Case Study"])

@router.post("/generate", summary="Generate a technical case study directly from structured project knowledge")
async def generate_case_study(
    project_id: str,
    project_repo: ProjectRepository = Depends(get_project_repo),
    case_study_repo: CaseStudyRepository = Depends(get_case_study_repo),
    generator: CaseStudyGenerator = Depends(get_case_study_generator)
):
    project = await project_repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    knowledge_record = await project_repo.get_knowledge(project_id)
    if not knowledge_record:
        raise HTTPException(status_code=404, detail="Knowledge record not found.")

    knowledge = ProjectKnowledge.model_validate(knowledge_record.knowledge_json)
    case_study_res = await generator.generate_case_study(knowledge)

    # Persist case study record
    record = await case_study_repo.save_case_study(
        project_id=project_id,
        title=case_study_res.title,
        markdown_content=case_study_res.markdown_content,
        sections_json=[s.model_dump() for s in case_study_res.sections]
    )

    return {
        "id": record.id,
        "project_id": project_id,
        "title": record.title,
        "executive_summary": case_study_res.executive_summary,
        "sections": record.sections_json,
        "markdown_content": record.markdown_content,
        "created_at": record.created_at.isoformat() if record.created_at else None
    }

@router.get("", summary="Retrieve the generated case study")
async def get_case_study(
    project_id: str,
    case_study_repo: CaseStudyRepository = Depends(get_case_study_repo)
):
    record = await case_study_repo.get_case_study(project_id)
    if not record:
        raise HTTPException(status_code=404, detail="Case study not found for this project.")

    return {
        "id": record.id,
        "project_id": project_id,
        "title": record.title,
        "sections": record.sections_json,
        "markdown_content": record.markdown_content,
        "created_at": record.created_at.isoformat() if record.created_at else None
    }
