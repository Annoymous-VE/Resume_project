from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from app.config import UPLOADS_DIR
from app.models.entities import User
from app.api.dependencies import (
    get_project_repo,
    get_resume_parser,
    get_project_extractor,
    get_knowledge_manager,
    get_current_user,
    get_optional_current_user,
    get_storage_manager,
    ProjectRepository,
    ResumeParser,
    ProjectExtractor,
    KnowledgeManager,
    StorageManager
)

router = APIRouter(prefix="/api/resumes", tags=["Resumes"])

@router.post("", summary="Upload a resume and extract projects")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
    parser: ResumeParser = Depends(get_resume_parser),
    extractor: ProjectExtractor = Depends(get_project_extractor),
    knowledge_manager: KnowledgeManager = Depends(get_knowledge_manager),
    storage_mgr: StorageManager = Depends(get_storage_manager)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing.")

    user_id = current_user.id
    file_ext = Path(file.filename).suffix.lower()

    # Read binary content
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Upload to Supabase Storage: Resumes/<user_id>/<filename> (with local caching)
    upload_info = await storage_mgr.upload_resume(
        user_id=user_id,
        filename=file.filename,
        content=content,
        content_type=file.content_type or "application/octet-stream"
    )
    dest_path = Path(upload_info["local_path"])

    # Parse layout-aware document representation
    doc_rep = parser.parse(dest_path, file.filename)

    # Persist Resume record with tenant user_id and storage path
    resume = await project_repo.create_resume(
        filename=file.filename,
        file_path=upload_info["storage_path"],
        file_type=file_ext.replace(".", ""),
        raw_structure=doc_rep.model_dump(),
        user_id=user_id
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
            confidence=ep.confidence,
            user_id=user_id
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


@router.get("", summary="List resumes belonging to the authenticated user")
async def list_resumes(
    current_user: Optional[User] = Depends(get_optional_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo)
):
    user_id = current_user.id if current_user else None
    resumes = await project_repo.get_all_resumes(user_id=user_id)
    return [
        {
            "id": r.id,
            "filename": r.filename,
            "file_type": r.file_type,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "projects_count": len(r.projects) if r.projects else 0
        }
        for r in resumes
    ]


@router.get("/{resume_id}", summary="Get resume details by ID")
async def get_resume(
    resume_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo)
):
    resume = await project_repo.get_resume(resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    if resume.user_id and current_user and resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: this resume belongs to another account."
        )

    projects = await project_repo.get_projects_by_resume(resume.id)
    return {
        "id": resume.id,
        "filename": resume.filename,
        "file_type": resume.file_type,
        "created_at": resume.created_at.isoformat() if resume.created_at else None,
        "projects": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "confidence": p.confidence
            }
            for p in projects
        ]
    }


@router.post("/{resume_id}/re-extract", summary="Re-extract technical projects from an existing resume")
async def re_extract_resume(
    resume_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
    parser: ResumeParser = Depends(get_resume_parser),
    extractor: ProjectExtractor = Depends(get_project_extractor),
    knowledge_manager: KnowledgeManager = Depends(get_knowledge_manager),
    storage_mgr: StorageManager = Depends(get_storage_manager)
):
    from app.services.resume_parser import DocumentRepresentation
    resume = await project_repo.get_resume(resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    if resume.user_id and current_user and resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: this resume belongs to another account."
        )

    user_id = current_user.id if current_user else resume.user_id

    doc_rep = None
    if resume.file_path and Path(resume.file_path).exists():
        doc_rep = parser.parse(Path(resume.file_path), resume.filename)
    elif resume.file_path:
        file_bytes = await storage_mgr.get_resume_bytes(resume.file_path)
        if file_bytes:
            local_dest = UPLOADS_DIR / resume.filename
            local_dest.write_bytes(file_bytes)
            doc_rep = parser.parse(local_dest, resume.filename)

    if not doc_rep and resume.raw_structure:
        doc_rep = DocumentRepresentation.model_validate(resume.raw_structure)

    if not doc_rep:
        raise HTTPException(status_code=400, detail="Document data unavailable for re-extraction.")

    extracted_projects = await extractor.extract_projects(doc_rep)

    persisted = []
    for ep in extracted_projects:
        proj = await project_repo.create_project(
            resume_id=resume.id,
            name=ep.name,
            description=ep.description,
            data_json=ep.model_dump(),
            confidence=ep.confidence,
            user_id=user_id
        )
        init_knowledge = knowledge_manager.initialize_knowledge(ep)
        await project_repo.save_knowledge(proj.id, init_knowledge.model_dump())
        persisted.append({
            "id": proj.id,
            "name": proj.name,
            "description": proj.description,
            "technologies": ep.technologies,
            "confidence": proj.confidence
        })

    return {
        "resume_id": resume.id,
        "message": f"Successfully re-extracted {len(persisted)} projects.",
        "projects": persisted
    }

