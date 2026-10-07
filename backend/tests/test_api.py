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
        import uuid
        email = f"resume_flow_{uuid.uuid4().hex[:6]}@example.com"
        reg_res = await client.post("/api/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "John Tester"
        })
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        sample_resume_content = b"""
        John Smith
        Distributed Systems Engineer
        
        EXPERIENCE
        Lead Engineer at CloudScale
        - Built asynchronous distributed queue with Redis and Python
        - Handled 50k events per minute
        """

        # 1. Unauthenticated upload should be rejected with 401
        files_unauth = {"file": ("test_resume.txt", io.BytesIO(sample_resume_content), "text/plain")}
        unauth_res = await client.post("/api/resumes", files=files_unauth)
        assert unauth_res.status_code == 401

        # 2. Authenticated upload succeeds
        files = {"file": ("test_resume.txt", io.BytesIO(sample_resume_content), "text/plain")}
        upload_res = await client.post("/api/resumes", files=files, headers=headers)
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
        import uuid
        email = f"stop_phrase_{uuid.uuid4().hex[:6]}@example.com"
        reg_res = await client.post("/api/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "Jane Architect"
        })
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        files = {"file": ("jane_resume.txt", io.BytesIO(sample_resume_content), "text/plain")}
        upload_res = await client.post("/api/resumes", files=files, headers=headers)
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

@pytest.mark.asyncio
async def test_dual_variant_api_flow():
    """Verify that both Technical Case Study and Client Brochure can be independently generated,
    stored, retrieved via /all and ?variant_type=..., and exported to PDF/DOCX for the same project."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create a project
        payload = {
            "name": "Global Inventory Distributed Ledger",
            "description": "Enterprise multi-region ledger for synchronizing inventory states across 12 warehouses.",
            "technologies": ["Python", "FastAPI", "PostgreSQL", "Kafka", "Docker"],
            "contributions": ["Architected distributed transaction coordinator", "Implemented CQRS read projection"],
            "outcomes": ["Reduced inventory sync skew from 45s to 200ms", "Supported $50M in peak Black Friday GMV"],
            "links": ["https://github.com/example/inventory-ledger"]
        }
        create_res = await client.post("/api/projects", json=payload)
        assert create_res.status_code == 200
        project_id = create_res.json()["id"]

        # 2. Start interview and add an answer
        start_res = await client.post(f"/api/projects/{project_id}/interview/start")
        assert start_res.status_code == 200
        exchange_id = start_res.json()["current_question"]["exchange_id"]

        ans_res = await client.post(
            f"/api/projects/{project_id}/interview/answer",
            json={
                "exchange_id": exchange_id,
                "answer": "We adopted two-phase commit with Kafka event sourcing to guarantee zero duplicate reservations."
            }
        )
        assert ans_res.status_code == 200

        # 3. Generate technical case study variant
        tech_gen_res = await client.post(f"/api/projects/{project_id}/case-study/generate?variant_type=technical")
        assert tech_gen_res.status_code == 200
        tech_data = tech_gen_res.json()
        assert tech_data["project_id"] == project_id
        assert tech_data.get("variant_type", "technical") == "technical"
        assert "Global Inventory Distributed Ledger" in tech_data["markdown_content"]

        # 4. Generate client brochure variant
        brochure_gen_res = await client.post(f"/api/projects/{project_id}/case-study/generate?variant_type=client_brochure")
        assert brochure_gen_res.status_code == 200
        brochure_data = brochure_gen_res.json()
        assert brochure_data["project_id"] == project_id
        assert brochure_data.get("variant_type") == "client_brochure"
        assert len(brochure_data["markdown_content"]) > 100

        # 5. Verify /case-study/all returns BOTH variants without collisions
        all_res = await client.get(f"/api/projects/{project_id}/case-study/all")
        assert all_res.status_code == 200
        all_items = all_res.json()
        assert len(all_items) == 2
        variants = {item["variant_type"] for item in all_items}
        assert variants == {"technical", "client_brochure"}

        # 6. Verify GET /case-study with query params fetches each variant specifically
        get_tech_res = await client.get(f"/api/projects/{project_id}/case-study?variant_type=technical")
        assert get_tech_res.status_code == 200
        assert get_tech_res.json()["variant_type"] == "technical"

        get_brochure_res = await client.get(f"/api/projects/{project_id}/case-study?variant_type=client_brochure")
        assert get_brochure_res.status_code == 200
        assert get_brochure_res.json()["variant_type"] == "client_brochure"

        # 7. Verify exports for technical
        tech_pdf = await client.get(f"/api/projects/{project_id}/case-study/export/pdf?variant_type=technical")
        assert tech_pdf.status_code == 200
        assert tech_pdf.headers["content-type"] == "application/pdf"
        assert ".pdf" in tech_pdf.headers.get("content-disposition", "")

        # 8. Verify exports for client brochure
        brochure_pdf = await client.get(f"/api/projects/{project_id}/case-study/export/pdf?variant_type=client_brochure")
        assert brochure_pdf.status_code == 200
        assert brochure_pdf.headers["content-type"] == "application/pdf"
        assert "_Brochure.pdf" in brochure_pdf.headers.get("content-disposition", "")

        brochure_docx = await client.get(f"/api/projects/{project_id}/case-study/export/docx?variant_type=client_brochure")
        assert brochure_docx.status_code == 200
        assert "_Brochure.docx" in brochure_docx.headers.get("content-disposition", "")

@pytest.mark.asyncio
async def test_superficial_obstacle_reply_escalation_api():
    """Verify that submitting a superficial reply to an obstacle inquiry triggers category escalation."""
    await init_db()
    from app.repositories.database import async_session_factory
    from app.repositories.interview_repository import InterviewRepository

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create project
        create_res = await client.post("/api/projects", json={
            "name": "Payment Gateway Aggregator",
            "description": "High throughput payment router handling multi-acquirer settlement",
            "technologies": ["Go", "PostgreSQL", "Kafka"]
        })
        assert create_res.status_code == 200
        project_id = create_res.json()["id"]

        # 2. Start interview
        start_res = await client.post(f"/api/projects/{project_id}/interview/start")
        assert start_res.status_code == 200
        session_id = start_res.json()["session_id"]

        # 3. Add an exchange targeting challenges
        async with async_session_factory() as db:
            interview_repo = InterviewRepository(db)
            exchange = await interview_repo.add_exchange(
                session_id=session_id,
                question_id="q_chal_friction_test",
                target_area="challenges",
                question="In real-world engineering, virtually no system is built without friction. What were the key obstacles or failure modes you encountered?",
                rationale="Testing obstacle inquiry"
            )
            await db.commit()

        # 4. Submit superficial answer: "everything went smoothly"
        ans_res = await client.post(
            f"/api/projects/{project_id}/interview/answer",
            json={
                "exchange_id": exchange.id,
                "answer": "everything went smoothly"
            }
        )
        assert ans_res.status_code == 200
        ans_data = ans_res.json()

        # Interview should NOT be completed; it must escalate with the category prompt
        assert ans_data["status"] == "in_progress"
        assert ans_data["current_question"] is not None
        assert ans_data["current_question"]["target_area"] == "challenges"
        expected_escalation = (
            "Even well-designed architectures face constraints like API rate limits, "
            "database locks, slow queries, or third-party integration bugs. Which of these did you experience?"
        )
        assert expected_escalation in ans_data["current_question"]["question"]



