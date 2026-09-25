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

        # 7. Test PDF export
        pdf_res = await client.get(f"/api/projects/{project_id}/case-study/export/pdf")
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert len(pdf_res.content) > 500

        # 8. Test DOCX export
        docx_res = await client.get(f"/api/projects/{project_id}/case-study/export/docx")
        assert docx_res.status_code == 200
        assert "officedocument.wordprocessingml" in docx_res.headers["content-type"]
        assert len(docx_res.content) > 1000

        # 9. Test Markdown export
        md_res = await client.get(f"/api/projects/{project_id}/case-study/export/md")
        assert md_res.status_code == 200
        assert "text/markdown" in md_res.headers["content-type"]
        assert len(md_res.content) > 50

@pytest.mark.asyncio
async def test_interview_stop_phrase_completion():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        sample_resume_content = b"""
        Jane Doe
        Cloud Architect
        
        EXPERIENCE
        Architect at ScaleCloud
        - Designed event streaming architecture with Kafka
        """
        files = {"file": ("jane_resume.txt", io.BytesIO(sample_resume_content), "text/plain")}
        upload_res = await client.post("/api/resumes", files=files)
        assert upload_res.status_code == 200
        project_id = upload_res.json()["projects"][0]["id"]

        # Start interview
        interview_res = await client.post(f"/api/projects/{project_id}/interview/start")
        assert interview_res.status_code == 200
        exchange_id = interview_res.json()["current_question"]["exchange_id"]

        # Answer with stop phrase
        ans_res = await client.post(
            f"/api/projects/{project_id}/interview/answer",
            json={"exchange_id": exchange_id, "answer": "I have nothing more to add."}
        )
        assert ans_res.status_code == 200
        ans_data = ans_res.json()
        assert ans_data["status"] == "completed"
        assert ans_data["current_question"] is None
        assert "I have nothing more to add" in ans_data["stop_reason"]

        # Proceed directly to generate case study
        cs_res = await client.post(f"/api/projects/{project_id}/case-study/generate")
        assert cs_res.status_code == 200
        assert "markdown_content" in cs_res.json()

@pytest.mark.asyncio
async def test_create_custom_project():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Validation test: missing technologies
        bad_res = await client.post("/api/projects", json={
            "name": "My Side Project",
            "description": "An automated testing tool.",
            "technologies": []
        })
        assert bad_res.status_code == 400

        # 2. Successfully create manual project
        payload = {
            "name": "Custom Microservices Gateway",
            "description": "An edge routing gateway with rate limiting and token bucket filtering.",
            "technologies": ["Go", "Redis", "Docker", "gRPC"],
            "contributions": ["Designed token bucket filter algorithm", "Built latency metrics exporter"],
            "outcomes": ["Reduced p99 proxy overhead to 0.4ms", "Handled 80,000 req/s"],
            "links": ["https://github.com/example/gateway"]
        }
        res = await client.post("/api/projects", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == payload["name"]
        assert "Go" in data["technologies"]
        assert len(data["contributions"]) == 2
        assert len(data["outcomes"]) == 2
        project_id = data["id"]

        # 3. Start interview on the manual project
        start_res = await client.post(f"/api/projects/{project_id}/interview/start")
        assert start_res.status_code == 200
        start_data = start_res.json()
        assert start_data["status"] == "in_progress"
        assert start_data["current_question"] is not None

