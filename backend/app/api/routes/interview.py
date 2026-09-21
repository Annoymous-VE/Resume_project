from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from app.api.dependencies import (
    get_project_repo,
    get_interview_repo,
    get_knowledge_manager,
    get_interview_engine,
    ProjectRepository,
    InterviewRepository,
    KnowledgeManager,
    InterviewEngine
)
from app.ai.schemas.project import ExtractedProject
from app.ai.schemas.knowledge import ProjectKnowledge

router = APIRouter(prefix="/api/projects/{project_id}/interview", tags=["Interview"])

class AnswerSubmission(BaseModel):
    exchange_id: str
    answer: str

@router.post("/start", summary="Start or resume an adaptive interview for a project")
async def start_interview(
    project_id: str,
    project_repo: ProjectRepository = Depends(get_project_repo),
    interview_repo: InterviewRepository = Depends(get_interview_repo),
    knowledge_manager: KnowledgeManager = Depends(get_knowledge_manager),
    interview_engine: InterviewEngine = Depends(get_interview_engine)
):
    project = await project_repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    knowledge_record = await project_repo.get_knowledge(project_id)
    if not knowledge_record:
        raise HTTPException(status_code=404, detail="Knowledge record not found.")

    knowledge = ProjectKnowledge.model_validate(knowledge_record.knowledge_json)
    coverage = knowledge_manager.compute_coverage(knowledge)

    # Check if session exists
    session = await interview_repo.get_session_by_project(project_id)
    if not session:
        session = await interview_repo.create_session(
            project_id=project_id,
            coverage_json=coverage.model_dump()
        )

        extracted_proj = ExtractedProject.model_validate(project.data_json)
        initial_questions = await interview_engine.generate_initial_questions(extracted_proj, coverage)

        # Store the first question as pending exchange
        if initial_questions:
            q0 = initial_questions[0]
            await interview_repo.add_exchange(
                session_id=session.id,
                question_id=q0.id,
                target_area=q0.target_area,
                question=q0.question,
                rationale=q0.rationale
            )
        # Reload with exchanges
        session = await interview_repo.get_session_by_project(project_id)

    pending_exchange = next((ex for ex in session.exchanges if ex.answer is None), None)

    return {
        "session_id": session.id,
        "project_id": project_id,
        "status": session.status,
        "round_count": session.round_count,
        "coverage": session.coverage_json,
        "current_question": {
            "exchange_id": pending_exchange.id,
            "target_area": pending_exchange.target_area,
            "question": pending_exchange.question,
            "rationale": pending_exchange.rationale
        } if pending_exchange else None,
        "stop_reason": session.stop_reason
    }

@router.post("/answer", summary="Submit an answer to the current interview question")
async def answer_question(
    project_id: str,
    submission: AnswerSubmission,
    project_repo: ProjectRepository = Depends(get_project_repo),
    interview_repo: InterviewRepository = Depends(get_interview_repo),
    knowledge_manager: KnowledgeManager = Depends(get_knowledge_manager),
    interview_engine: InterviewEngine = Depends(get_interview_engine)
):
    session = await interview_repo.get_session_by_project(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")

    if session.status == "completed":
        return {
            "session_id": session.id,
            "status": "completed",
            "message": "Interview is already complete.",
            "stop_reason": session.stop_reason
        }

    # Record answer
    exchange = await interview_repo.record_answer(submission.exchange_id, submission.answer)
    if not exchange:
        raise HTTPException(status_code=404, detail="Exchange not found.")

    # Update knowledge object with provenance
    knowledge_record = await project_repo.get_knowledge(project_id)
    knowledge = ProjectKnowledge.model_validate(knowledge_record.knowledge_json)
    knowledge = knowledge_manager.merge_answer(
        current_knowledge=knowledge,
        target_area=exchange.target_area,
        answer_text=submission.answer,
        exchange_id=exchange.id
    )
    await project_repo.save_knowledge(project_id, knowledge.model_dump())

    # Re-compute coverage
    new_coverage = knowledge_manager.compute_coverage(knowledge)

    # Prepare interview history
    history = [
        {"question": ex.question, "answer": ex.answer or ""}
        for ex in session.exchanges
        if ex.answer is not None
    ]

    # Select next question or trigger stop
    next_res = await interview_engine.select_next_question(
        knowledge=knowledge,
        coverage=new_coverage,
        current_round=session.round_count + 1,
        latest_question=exchange.question,
        latest_answer=submission.answer,
        history=history
    )

    if not next_res.has_next_question:
        session = await interview_repo.update_session_state(
            session_id=session.id,
            coverage_json=new_coverage.model_dump(),
            round_increment=True,
            status="completed",
            stop_reason=next_res.stop_reason or "Interview complete."
        )
        return {
            "session_id": session.id,
            "status": "completed",
            "round_count": session.round_count,
            "coverage": session.coverage_json,
            "current_question": None,
            "stop_reason": session.stop_reason
        }

    # Add next exchange
    next_q = next_res.question
    new_exchange = await interview_repo.add_exchange(
        session_id=session.id,
        question_id=next_q.id,
        target_area=next_q.target_area,
        question=next_q.question,
        rationale=next_q.rationale
    )

    session = await interview_repo.update_session_state(
        session_id=session.id,
        coverage_json=new_coverage.model_dump(),
        round_increment=True,
        status="in_progress"
    )

    return {
        "session_id": session.id,
        "status": "in_progress",
        "round_count": session.round_count,
        "coverage": session.coverage_json,
        "current_question": {
            "exchange_id": new_exchange.id,
            "target_area": new_exchange.target_area,
            "question": new_exchange.question,
            "rationale": new_exchange.rationale
        },
        "stop_reason": None
    }

@router.get("/status", summary="Get interview session status and Q&A history")
async def get_interview_status(
    project_id: str,
    interview_repo: InterviewRepository = Depends(get_interview_repo)
):
    session = await interview_repo.get_session_by_project(project_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")

    return {
        "session_id": session.id,
        "project_id": session.project_id,
        "status": session.status,
        "round_count": session.round_count,
        "coverage": session.coverage_json,
        "stop_reason": session.stop_reason,
        "exchanges": [
            {
                "id": ex.id,
                "question": ex.question,
                "target_area": ex.target_area,
                "rationale": ex.rationale,
                "answer": ex.answer,
                "created_at": ex.created_at.isoformat() if ex.created_at else None,
                "answered_at": ex.answered_at.isoformat() if ex.answered_at else None
            }
            for ex in session.exchanges
        ]
    }
