import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.repositories.database import init_db

@pytest.mark.asyncio
async def test_multi_tenancy_and_data_isolation():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register User A
        email_a = f"tenant_a_{uuid.uuid4().hex[:6]}@example.com"
        res_a = await client.post("/api/auth/register", json={
            "email": email_a,
            "password": "Password123!",
            "full_name": "Alice Tenant"
        })
        assert res_a.status_code == 201
        token_a = res_a.json()["access_token"]
        user_a_id = res_a.json()["user"]["id"]

        # 2. Register User B
        email_b = f"tenant_b_{uuid.uuid4().hex[:6]}@example.com"
        res_b = await client.post("/api/auth/register", json={
            "email": email_b,
            "password": "Password123!",
            "full_name": "Bob Tenant"
        })
        assert res_b.status_code == 201
        token_b = res_b.json()["access_token"]
        user_b_id = res_b.json()["user"]["id"]

        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # 3. User A creates a project
        proj_a_res = await client.post("/api/projects", json={
            "name": "Alice Secret Project",
            "description": "High security data pipeline for Alice",
            "technologies": ["Python", "FastAPI"]
        }, headers=headers_a)
        assert proj_a_res.status_code == 200
        proj_a_id = proj_a_res.json()["id"]

        # 4. User B creates a project
        proj_b_res = await client.post("/api/projects", json={
            "name": "Bob Private Project",
            "description": "Bob's private blockchain ledger",
            "technologies": ["Rust", "Solana"]
        }, headers=headers_b)
        assert proj_b_res.status_code == 200
        proj_b_id = proj_b_res.json()["id"]

        # 5. User A lists projects: should only see Alice's project
        list_a = await client.get("/api/projects", headers=headers_a)
        assert list_a.status_code == 200
        projs_a = list_a.json()
        ids_a = [p["id"] for p in projs_a]
        assert proj_a_id in ids_a
        assert proj_b_id not in ids_a

        # 6. User B lists projects: should only see Bob's project
        list_b = await client.get("/api/projects", headers=headers_b)
        assert list_b.status_code == 200
        projs_b = list_b.json()
        ids_b = [p["id"] for p in projs_b]
        assert proj_b_id in ids_b
        assert proj_a_id not in ids_b

        # 7. Cross-tenant access isolation: Bob attempts to view Alice's project
        cross_proj = await client.get(f"/api/projects/{proj_a_id}", headers=headers_b)
        assert cross_proj.status_code == 403
        assert "Access denied" in cross_proj.json()["detail"]

        # 8. Cross-tenant knowledge access: Bob attempts to view Alice's knowledge object
        cross_know = await client.get(f"/api/projects/{proj_a_id}/knowledge", headers=headers_b)
        assert cross_know.status_code == 403

        # 9. Cross-tenant interview access: Bob attempts to start interview on Alice's project
        cross_int = await client.post(f"/api/projects/{proj_a_id}/interview/start", headers=headers_b)
        assert cross_int.status_code == 403

        # 10. Cross-tenant case study access: Bob attempts to generate case study on Alice's project
        cross_cs = await client.post(f"/api/projects/{proj_a_id}/case-study/generate", headers=headers_b)
        assert cross_cs.status_code == 403

        # 11. Alice CAN access her own project and knowledge
        alice_proj = await client.get(f"/api/projects/{proj_a_id}", headers=headers_a)
        assert alice_proj.status_code == 200
        assert alice_proj.json()["name"] == "Alice Secret Project"

        alice_know = await client.get(f"/api/projects/{proj_a_id}/knowledge", headers=headers_a)
        assert alice_know.status_code == 200
