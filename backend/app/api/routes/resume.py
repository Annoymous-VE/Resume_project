import shutil
import io
from pathlib import Path
from typing import List
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from app.config import UPLOADS_DIR
from app.api.dependencies import (
    get_project_repo,
    get_resume_parser,
    get_project_extractor,
    get_knowledge_manager,
    get_storage_service,
    ProjectRepository,
    ResumeParser,
    ProjectExtractor,
    KnowledgeManager,
    BaseStorageService
)

router = APIRouter(prefix="/api/resumes", tags=["Resumes"])

@router.post("", summary="Upload a resume, store in cloud storage, and extract projects")
async def upload_resume(
    file: UploadFile = File(...),
    project_repo: ProjectRepository = Depends(get_project_repo),
    parser: ResumeParser = Depends(get_resume_parser),
    extractor: ProjectExtractor = Depends(get_project_extractor),
    knowledge_manager: KnowledgeManager = Depends(get_knowledge_manager),
    storage: BaseStorageService = Depends(get_storage_service)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing.")

    file_bytes = await file.read()
    file_ext = Path(file.filename).suffix.lower()
    content_type = file.content_type or ("application/pdf" if file_ext == ".pdf" else "application/octet-stream")

    # 1. Save uploaded file to local workspace/temp path for layout parser
    dest_path = UPLOADS_DIR / file.filename
    with open(dest_path, "wb") as buffer:
        buffer.write(file_bytes)

    # 2. Upload to Cloud Object Storage (Supabase Storage or Local Storage)
    storage_key, file_url = await storage.upload(file_bytes, file.filename, content_type)

    # 3. Parse layout-aware document representation
    doc_rep = parser.parse(dest_path, file.filename)

    # 4. Persist Resume record with cloud storage metadata
    resume = await project_repo.create_resume(
        filename=file.filename,
        file_path=str(dest_path),
        file_type=file_ext.replace(".", ""),
        raw_structure=doc_rep.model_dump(),
        storage_key=storage_key,
        mime_type=content_type,
        file_url=file_url
    )

    # 5. Extract technical projects
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
        "view_url": file_url,
        "storage_key": storage_key,
        "total_blocks": len(doc_rep.blocks),
        "projects_count": len(persisted_projects),
        "projects": persisted_projects
    }

@router.get("/{id}/view", summary="Get a secure view URL to view the uploaded resume")
async def view_resume(
    id: str,
    project_repo: ProjectRepository = Depends(get_project_repo),
    storage: BaseStorageService = Depends(get_storage_service)
):
    resume = await project_repo.get_resume(id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    view_url = resume.file_url
    if resume.storage_key:
        try:
            view_url = await storage.get_view_url(resume.storage_key, expires_in=3600)
        except Exception:
            pass

    return {
        "resume_id": resume.id,
        "filename": resume.filename,
        "view_url": view_url,
        "file_type": resume.file_type,
        "mime_type": resume.mime_type
    }

@router.get("/{id}/download", summary="Download the original uploaded resume document")
async def download_resume(
    id: str,
    project_repo: ProjectRepository = Depends(get_project_repo),
    storage: BaseStorageService = Depends(get_storage_service)
):
    resume = await project_repo.get_resume(id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    try:
        if resume.storage_key:
            content, content_type = await storage.download(resume.storage_key)
        else:
            with open(resume.file_path, "rb") as f:
                content = f.read()
            content_type = resume.mime_type or "application/octet-stream"
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File could not be retrieved: {str(e)}")

    return StreamingResponse(
        io.BytesIO(content),
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{resume.filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )

@router.get("/raw/{storage_key}", summary="Stream raw file for inline viewing (local/fallback mode)")
async def raw_resume(
    storage_key: str,
    storage: BaseStorageService = Depends(get_storage_service)
):
    try:
        content, content_type = await storage.download(storage_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found in storage.")
    
    clean_filename = storage_key.split("_", 1)[-1] if "_" in storage_key else storage_key
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f'inline; filename="{clean_filename}"'
        }
    )
