import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from app.services.storage_service import SupabaseStorageService, LocalStorageService, create_storage_service

@pytest.mark.asyncio
async def test_local_storage_service(tmp_path):
    storage = LocalStorageService(upload_dir=tmp_path)
    content = b"Mock local storage file data"
    
    key, view_url = await storage.upload(content, "my_resume.pdf", "application/pdf")
    assert key.endswith("_my_resume.pdf")
    assert "/api/resumes/raw/" in view_url
    
    # Download
    downloaded_content, mime_type = await storage.download(key)
    assert downloaded_content == content
    assert mime_type == "application/pdf"

@pytest.mark.asyncio
async def test_supabase_storage_service():
    supabase_url = "https://mockproject.supabase.co"
    supabase_key = "mock-key-12345"
    bucket = "resumes"
    storage = SupabaseStorageService(supabase_url=supabase_url, supabase_key=supabase_key, bucket_name=bucket)
    
    content = b"Mock Supabase resume bytes"
    key = "test_uuid_jane_doe.pdf"

    # Mock upload
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        
        # 1. Test get_view_url (signed)
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"signedURL": f"/object/sign/{bucket}/{key}?token=mocktoken"}
        )
        view_url = await storage.get_view_url(key, expires_in=1800)
        assert f"/storage/v1/object/sign/{bucket}/{key}?token=mocktoken" in view_url

        # 2. Test download
        mock_get.return_value = MagicMock(
            status_code=200,
            content=content,
            headers={"content-type": "application/pdf"}
        )
        downloaded, content_type = await storage.download(key)
        assert downloaded == content
        assert content_type == "application/pdf"

def test_create_storage_service_fallback():
    with patch("app.services.storage_service.settings") as mock_settings:
        mock_settings.SUPABASE_URL = ""
        mock_settings.SUPABASE_KEY = ""
        svc = create_storage_service()
        assert isinstance(svc, LocalStorageService)

        mock_settings.SUPABASE_URL = "https://example.supabase.co"
        mock_settings.SUPABASE_KEY = "test-key"
        mock_settings.SUPABASE_BUCKET_NAME = "resumes"
        svc_supabase = create_storage_service()
        assert isinstance(svc_supabase, SupabaseStorageService)
