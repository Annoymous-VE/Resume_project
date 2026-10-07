import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.repositories.database import init_db

@pytest.mark.asyncio
async def test_dashboard_api_flow():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register a user
        email = f"dash_{uuid.uuid4().hex[:6]}@example.com"
        reg_res = await client.post("/api/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "Dash User"
        })
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Get initial dashboard
        dash_res = await client.get("/api/dashboard", headers=headers)
        assert dash_res.status_code == 200
        dash_data = dash_res.json()
        assert "stats" in dash_data
        assert "projects" in dash_data
        assert "resumes" in dash_data
        assert "case_studies" in dash_data
        assert dash_data["stats"]["total_projects"] == 0

        # 3. Create a project
        proj_res = await client.post("/api/projects", json={
            "name": "Cloud Native Orchestrator",
            "description": "Kubernetes operator written in Go and Rust",
            "technologies": ["Kubernetes", "Go", "Rust"]
        }, headers=headers)
        assert proj_res.status_code == 200
        proj_id = proj_res.json()["id"]

        # 4. Verify dashboard now reflects the project
        dash_after_proj = await client.get("/api/dashboard", headers=headers)
        assert dash_after_proj.status_code == 200
        dash_data2 = dash_after_proj.json()
        assert dash_data2["stats"]["total_projects"] == 1
        assert len(dash_data2["projects"]) == 1
        assert dash_data2["projects"][0]["name"] == "Cloud Native Orchestrator"
        assert "Kubernetes" in dash_data2["projects"][0]["technologies"]

        # 5. Delete project
        del_res = await client.delete(f"/api/dashboard/projects/{proj_id}", headers=headers)
        assert del_res.status_code == 200

        # 6. Verify dashboard is clean again
        dash_final = await client.get("/api/dashboard", headers=headers)
        assert dash_final.status_code == 200
        assert dash_final.json()["stats"]["total_projects"] == 0
