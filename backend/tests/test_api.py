import pytest
import io
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.repositories.database import init_db

@pytest.mark.asyncio
async def test_api_health():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_full_resume_flow():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Upload sample resume
        sample_resume_content = b"""
        John Smith
        Distributed Systems Engineer
        
        EXPERIENCE
        Lead Engineer at CloudScale
        - Built asynchronous distributed queue with Redis and Python
        - Handled 50k events per minute
        """
        files = {"file": ("test_resume.txt", io.BytesIO(sample_resume_content), "text/plain")}
        upload_res = await client.post("/api/resumes", files=files)
        assert upload_res.status_code == 200
        upload_data = upload_res.json()
        assert "projects" in upload_data
        assert len(upload_data["projects"]) > 0

        project_id = upload_data["projects"][0]["id"]

        # 2. Get project details
        proj_res = await client.get(f"/api/projects/{project_id}")
        assert proj_res.status_code == 200
        assert proj_res.json()["id"] == project_id

        # 3. Start adaptive interview
        interview_res = await client.post(f"/api/projects/{project_id}/interview/start")
        assert interview_res.status_code == 200
        interview_data = interview_res.json()
        assert interview_data["status"] == "in_progress"
        assert interview_data["current_question"] is not None

        exchange_id = interview_data["current_question"]["exchange_id"]

        # 4. Answer question
        ans_payload = {
            "exchange_id": exchange_id,
            "answer": "We adopted Redis pub/sub because of strict sub-millisecond dispatch constraints."
        }
        answer_res = await client.post(f"/api/projects/{project_id}/interview/answer", json=ans_payload)
        assert answer_res.status_code == 200
        answer_data = answer_res.json()
        assert "coverage" in answer_data

        # 5. Generate case study
        cs_res = await client.post(f"/api/projects/{project_id}/case-study/generate")
        assert cs_res.status_code == 200
        cs_data = cs_res.json()
        assert "markdown_content" in cs_data
        assert cs_data["project_id"] == project_id

        # 6. Retrieve case study
        get_cs_res = await client.get(f"/api/projects/{project_id}/case-study")
        assert get_cs_res.status_code == 200
        assert get_cs_res.json()["id"] == cs_data["id"]
