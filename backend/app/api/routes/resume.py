import shutil
from pathlib import Path
from typing import List
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from app.config import UPLOADS_DIR
from app.api.dependencies import (
    get_project_repo,
    get_resume_parser,
    get_project_extractor,
    get_knowledge_manager,
    ProjectRepository,
    ResumeParser,
    ProjectExtractor,
    KnowledgeManager
)

router = APIRouter(prefix="/api/resumes", tags=["Resumes"])

@router.post("", summary="Upload a resume and extract projects")
async def upload_resume(
    file: UploadFile = File(...),
    project_repo: ProjectRepository = Depends(get_project_repo),
    parser: ResumeParser = Depends(get_resume_parser),
    extractor: ProjectExtractor = Depends(get_project_extractor),
    knowledge_manager: KnowledgeManager = Depends(get_knowledge_manager)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing.")

    # Save uploaded file
    file_ext = Path(file.filename).suffix.lower()
    dest_path = UPLOADS_DIR / file.filename
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Parse layout-aware document representation
    doc_rep = parser.parse(dest_path, file.filename)

    # Persist Resume record
    resume = await project_repo.create_resume(
        filename=file.filename,
        file_path=str(dest_path),
        file_type=file_ext.replace(".", ""),
        raw_structure=doc_rep.model_dump()
    )

    # Extract technical projects
    extracted_projects = await extractor.extract_projects(doc_rep)

    persisted_projects = []
    for ep in extracted_projects:
        proj = await project_repo.create_project(
            resume_id=resume.id,
            name=ep.name,
            description=ep.description,
            data_json=ep.model_dump(),
            confidence=ep.confidence
        )
        # Initialize structured knowledge object
        init_knowledge = knowledge_manager.initialize_knowledge(ep)
        await project_repo.save_knowledge(proj.id, init_knowledge.model_dump())

        persisted_projects.append({
            "id": proj.id,
            "name": proj.name,
            "description": proj.description,
            "technologies": ep.technologies,
            "contributions": ep.contributions,
            "outcomes": ep.outcomes,
            "confidence": proj.confidence
        })

    return {
        "resume_id": resume.id,
        "filename": resume.filename,
        "total_blocks": len(doc_rep.blocks),
        "projects_count": len(persisted_projects),
        "projects": persisted_projects
    }
