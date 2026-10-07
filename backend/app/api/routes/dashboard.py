from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.entities import User
from app.api.dependencies import (
    get_project_repo,
    get_optional_current_user,
    ProjectRepository
)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("", summary="Get centralized dashboard overview including resumes, projects, interviews, and case studies")
async def get_dashboard(
    current_user: Optional[User] = Depends(get_optional_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo)
):
    user_id = current_user.id if current_user else None

    # Fetch projects with loaded relationships
    projects = await project_repo.get_dashboard_projects(user_id=user_id)
    resumes = await project_repo.get_all_resumes(user_id=user_id)

    formatted_projects = []
    case_study_archive = []
    completed_interviews_count = 0
    total_case_studies_count = 0

    for p in projects:
        interview = None
        if p.interview_session:
            cov = p.interview_session.coverage_json or {}
            sufficient_count = sum(1 for v in cov.values() if v == "SUFFICIENT")
            total_dims = len(cov) if cov else 8
            percent = int((sufficient_count / total_dims) * 100) if total_dims else 0
            if p.interview_session.status == "completed":
                completed_interviews_count += 1

            exchanges = [
                {
                    "id": ex.id,
                    "target_area": ex.target_area,
                    "question": ex.question,
                    "rationale": ex.rationale,
                    "answer": ex.answer,
                    "answered_at": ex.answered_at.isoformat() if ex.answered_at else None,
                    "created_at": ex.created_at.isoformat() if ex.created_at else None
                }
                for ex in (p.interview_session.exchanges or [])
            ]

            interview = {
                "id": p.interview_session.id,
                "status": p.interview_session.status,
                "round_count": p.interview_session.round_count,
                "stop_reason": p.interview_session.stop_reason,
                "coverage_percent": percent,
                "coverage": cov,
                "exchanges": exchanges,
                "created_at": p.interview_session.created_at.isoformat() if p.interview_session.created_at else None,
                "updated_at": p.interview_session.updated_at.isoformat() if p.interview_session.updated_at else None
            }

        cs_list = []
        for cs in (p.case_studies or []):
            total_case_studies_count += 1
            cs_data = {
                "id": cs.id,
                "project_id": p.id,
                "project_name": p.name,
                "variant_type": cs.variant_type,
                "title": cs.title,
                "sections": cs.sections_json,
                "markdown_content": cs.markdown_content,
                "created_at": cs.created_at.isoformat() if cs.created_at else None
            }
            cs_list.append(cs_data)
            case_study_archive.append(cs_data)

        techs = []
        if isinstance(p.data_json, dict):
            techs = p.data_json.get("technologies", [])

        formatted_projects.append({
            "id": p.id,
            "resume_id": p.resume_id,
            "resume_filename": p.resume.filename if p.resume else "Manual Entry",
            "name": p.name,
            "description": p.description,
            "technologies": techs,
            "confidence": p.confidence,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "interview": interview,
            "case_studies": cs_list
        })

    formatted_resumes = [
        {
            "id": r.id,
            "filename": r.filename,
            "file_type": r.file_type,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "projects_count": len(r.projects) if r.projects else 0
        }
        for r in resumes
    ]

    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name
        } if current_user else None,
        "stats": {
            "total_resumes": len(resumes),
            "total_projects": len(projects),
            "completed_interviews": completed_interviews_count,
            "total_case_studies": total_case_studies_count
        },
        "resumes": formatted_resumes,
        "projects": formatted_projects,
        "case_studies": case_study_archive
    }

@router.delete("/projects/{project_id}", summary="Delete a project from the user's portfolio")
async def delete_project(
    project_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo)
):
    user_id = current_user.id if current_user else None
    deleted = await project_repo.delete_project(project_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found or unauthorized.")
    return {"message": "Project deleted successfully."}

@router.delete("/resumes/{resume_id}", summary="Delete an uploaded resume document")
async def delete_resume(
    resume_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo)
):
    user_id = current_user.id if current_user else None
    deleted = await project_repo.delete_resume(resume_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Resume not found or unauthorized.")
    return {"message": "Resume deleted successfully."}
