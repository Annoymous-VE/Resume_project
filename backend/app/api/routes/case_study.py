from typing import Optional
import io
import re
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from app.models.entities import User
from app.api.dependencies import (
    get_project_repo,
    get_case_study_repo,
    get_case_study_generator,
    get_optional_current_user,
    ProjectRepository,
    CaseStudyRepository,
    CaseStudyGenerator
)
from app.ai.schemas.knowledge import ProjectKnowledge
from app.services.case_study_exporter import CaseStudyExporter

router = APIRouter(prefix="/api/projects/{project_id}/case-study", tags=["Case Study"])

async def verify_project_ownership(
    project_id: str,
    project_repo: ProjectRepository,
    current_user: Optional[User]
):
    project = await project_repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    if project.user_id and current_user and project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: this project belongs to another account."
        )
    return project

@router.post("/generate", summary="Generate a technical or client brochure case study directly from structured project knowledge")
async def generate_case_study(
    project_id: str,
    variant_type: str = "technical",
    current_user: Optional[User] = Depends(get_optional_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
    case_study_repo: CaseStudyRepository = Depends(get_case_study_repo),
    generator: CaseStudyGenerator = Depends(get_case_study_generator)
):
    project = await verify_project_ownership(project_id, project_repo, current_user)

    knowledge_record = await project_repo.get_knowledge(project_id)
    if not knowledge_record:
        raise HTTPException(status_code=404, detail="Knowledge record not found.")

    knowledge = ProjectKnowledge.model_validate(knowledge_record.knowledge_json)
    case_study_res = await generator.generate_case_study(knowledge, variant_type=variant_type)

    # Persist case study record
    record = await case_study_repo.save_case_study(
        project_id=project_id,
        title=case_study_res.title,
        markdown_content=case_study_res.markdown_content,
        sections_json=[s.model_dump() for s in case_study_res.sections],
        variant_type=variant_type
    )

    return {
        "id": record.id,
        "project_id": project_id,
        "variant_type": record.variant_type,
        "title": record.title,
        "executive_summary": case_study_res.executive_summary,
        "sections": record.sections_json,
        "markdown_content": record.markdown_content,
        "created_at": record.created_at.isoformat() if record.created_at else None
    }

@router.get("", summary="Retrieve the generated case study")
async def get_case_study(
    project_id: str,
    variant_type: str = "technical",
    current_user: Optional[User] = Depends(get_optional_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
    case_study_repo: CaseStudyRepository = Depends(get_case_study_repo)
):
    await verify_project_ownership(project_id, project_repo, current_user)

    record = await case_study_repo.get_case_study(project_id, variant_type=variant_type)
    if not record:
        raise HTTPException(status_code=404, detail="Case study not found for this project.")

    return {
        "id": record.id,
        "project_id": project_id,
        "variant_type": record.variant_type,
        "title": record.title,
        "sections": record.sections_json,
        "markdown_content": record.markdown_content,
        "created_at": record.created_at.isoformat() if record.created_at else None
    }

@router.get("/all", summary="Retrieve all generated case study variants for this project")
async def get_all_case_studies(
    project_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
    case_study_repo: CaseStudyRepository = Depends(get_case_study_repo)
):
    await verify_project_ownership(project_id, project_repo, current_user)

    records = await case_study_repo.get_all_case_studies(project_id)
    return [
        {
            "id": r.id,
            "project_id": project_id,
            "variant_type": r.variant_type,
            "title": r.title,
            "sections": r.sections_json,
            "markdown_content": r.markdown_content,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in records
    ]

@router.get("/export/pdf", summary="Export the case study as a formatted PDF file")
async def export_case_study_pdf(
    project_id: str,
    variant_type: str = "technical",
    current_user: Optional[User] = Depends(get_optional_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
    case_study_repo: CaseStudyRepository = Depends(get_case_study_repo)
):
    await verify_project_ownership(project_id, project_repo, current_user)

    record = await case_study_repo.get_case_study(project_id, variant_type=variant_type)
    if not record or not record.markdown_content:
        raise HTTPException(status_code=404, detail="Case study not found for this project.")

    suffix = "_Brochure" if variant_type == "client_brochure" else ""
    pdf_buffer = CaseStudyExporter.export_to_pdf(record.title or "Case_Study", record.markdown_content, variant_type=variant_type)
    clean_name = re.sub(r"[^\w\-_]+", "_", (record.title or "Case_Study")).strip("_") + suffix

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{clean_name}.pdf"',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )

@router.get("/export/docx", summary="Export the case study as a formatted Word (.docx) file")
async def export_case_study_docx(
    project_id: str,
    variant_type: str = "technical",
    current_user: Optional[User] = Depends(get_optional_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
    case_study_repo: CaseStudyRepository = Depends(get_case_study_repo)
):
    await verify_project_ownership(project_id, project_repo, current_user)

    record = await case_study_repo.get_case_study(project_id, variant_type=variant_type)
    if not record or not record.markdown_content:
        raise HTTPException(status_code=404, detail="Case study not found for this project.")

    suffix = "_Brochure" if variant_type == "client_brochure" else ""
    docx_buffer = CaseStudyExporter.export_to_docx(record.title or "Case_Study", record.markdown_content, variant_type=variant_type)
    clean_name = re.sub(r"[^\w\-_]+", "_", (record.title or "Case_Study")).strip("_") + suffix

    return StreamingResponse(
        docx_buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{clean_name}.docx"',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )

@router.get("/export/md", summary="Export the raw Markdown case study")
async def export_case_study_markdown(
    project_id: str,
    variant_type: str = "technical",
    current_user: Optional[User] = Depends(get_optional_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
    case_study_repo: CaseStudyRepository = Depends(get_case_study_repo)
):
    await verify_project_ownership(project_id, project_repo, current_user)

    record = await case_study_repo.get_case_study(project_id, variant_type=variant_type)
    if not record or not record.markdown_content:
        raise HTTPException(status_code=404, detail="Case study not found for this project.")

    suffix = "_Brochure" if variant_type == "client_brochure" else ""
    md_buffer = io.BytesIO(record.markdown_content.encode("utf-8"))
    clean_name = re.sub(r"[^\w\-_]+", "_", (record.title or "Case_Study")).strip("_") + suffix

    return StreamingResponse(
        md_buffer,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{clean_name}.md"',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )
