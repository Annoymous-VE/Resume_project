import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple
import httpx
from app.config import settings, UPLOADS_DIR

class BaseStorageService(ABC):
    @abstractmethod
    async def upload(self, file_bytes: bytes, filename: str, mime_type: str) -> Tuple[str, Optional[str]]:
        """Upload file bytes and return (storage_key, public_or_view_url)."""
        pass

    @abstractmethod
    async def get_view_url(self, storage_key: str, expires_in: int = 3600) -> str:
        """Generate a view URL (signed or public) to view/embed the document."""
        pass

    @abstractmethod
    async def download(self, storage_key: str) -> Tuple[bytes, str]:
        """Download raw file bytes and mime_type."""
        pass


class SupabaseStorageService(BaseStorageService):
    """Storage adapter using Supabase Storage REST API."""

    def __init__(self, supabase_url: str, supabase_key: str, bucket_name: str = "resumes"):
        self.base_url = supabase_url.rstrip("/")
        self.api_key = supabase_key
        self.bucket = bucket_name
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "apikey": self.api_key
        }

    async def _ensure_bucket(self, client: httpx.AsyncClient) -> None:
        """Create the storage bucket if it does not already exist."""
        try:
            url = f"{self.base_url}/storage/v1/bucket"
            res = await client.get(url, headers=self.headers, timeout=10.0)
            if res.status_code == 200:
                existing_buckets = [b.get("id") or b.get("name") for b in res.json()]
                if self.bucket not in existing_buckets:
                    # Create bucket with public=false by default for candidate security
                    await client.post(
                        f"{self.base_url}/storage/v1/bucket",
                        headers=self.headers,
                        json={"id": self.bucket, "name": self.bucket, "public": False},
                        timeout=10.0
                    )
        except Exception:
            # Continue even if bucket check fails (permissions or preexisting bucket)
            pass

    async def upload(self, file_bytes: bytes, filename: str, mime_type: str) -> Tuple[str, Optional[str]]:
        storage_key = f"{uuid.uuid4()}_{filename}"
        upload_url = f"{self.base_url}/storage/v1/object/{self.bucket}/{storage_key}"

        headers = {
            **self.headers,
            "Content-Type": mime_type,
            "x-upsert": "true"
        }

        async with httpx.AsyncClient() as client:
            await self._ensure_bucket(client)
            res = await client.post(upload_url, headers=headers, content=file_bytes, timeout=30.0)
            if res.status_code not in (200, 201):
                # If Supabase storage fails, fallback to local file system
                raise RuntimeError(f"Failed to upload to Supabase Storage: {res.status_code} - {res.text}")

        # Generate a signed view URL
        view_url = await self.get_view_url(storage_key)
        return storage_key, view_url

    async def get_view_url(self, storage_key: str, expires_in: int = 3600) -> str:
        sign_url = f"{self.base_url}/storage/v1/object/sign/{self.bucket}/{storage_key}"
        async with httpx.AsyncClient() as client:
            res = await client.post(
                sign_url,
                headers=self.headers,
                json={"expiresIn": expires_in},
                timeout=15.0
            )
            if res.status_code == 200:
                data = res.json()
                signed_path = data.get("signedURL", "")
                if signed_path.startswith("http"):
                    return signed_path
                return f"{self.base_url}/storage/v1{signed_path}"

        # Fallback to public object URL
        return f"{self.base_url}/storage/v1/object/public/{self.bucket}/{storage_key}"

    async def download(self, storage_key: str) -> Tuple[bytes, str]:
        download_url = f"{self.base_url}/storage/v1/object/{self.bucket}/{storage_key}"
        async with httpx.AsyncClient() as client:
            res = await client.get(download_url, headers=self.headers, timeout=30.0)
            if res.status_code == 200:
                content_type = res.headers.get("content-type", "application/pdf")
                return res.content, content_type

            # Try downloading via signed URL
            signed_url = await self.get_view_url(storage_key)
            signed_res = await client.get(signed_url, timeout=30.0)
            if signed_res.status_code == 200:
                content_type = signed_res.headers.get("content-type", "application/pdf")
                return signed_res.content, content_type

        raise FileNotFoundError(f"Document {storage_key} not found in Supabase storage.")


class LocalStorageService(BaseStorageService):
    """Local filesystem storage service for development and testing environments."""

    def __init__(self, upload_dir: Path = UPLOADS_DIR):
        self.upload_dir = upload_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def upload(self, file_bytes: bytes, filename: str, mime_type: str) -> Tuple[str, Optional[str]]:
        storage_key = f"{uuid.uuid4()}_{filename}"
        target_path = self.upload_dir / storage_key
        with open(target_path, "wb") as f:
            f.write(file_bytes)
        
        # In local mode, return the relative view endpoint
        view_url = f"/api/resumes/raw/{storage_key}"
        return storage_key, view_url

    async def get_view_url(self, storage_key: str, expires_in: int = 3600) -> str:
        return f"/api/resumes/raw/{storage_key}"

    async def download(self, storage_key: str) -> Tuple[bytes, str]:
        target_path = self.upload_dir / storage_key
        if not target_path.exists():
            # Check if stored as original filename
            alt_path = self.upload_dir / storage_key.split("_", 1)[-1]
            if alt_path.exists():
                target_path = alt_path
            else:
                raise FileNotFoundError(f"File {storage_key} not found on local disk.")

        with open(target_path, "rb") as f:
            content = f.read()

        ext = target_path.suffix.lower()
        mime_map = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".txt": "text/plain"
        }
        return content, mime_map.get(ext, "application/octet-stream")


def create_storage_service() -> BaseStorageService:
    """Factory to instantiate the appropriate storage service based on configuration."""
    if settings.SUPABASE_URL and settings.SUPABASE_KEY:
        return SupabaseStorageService(
            supabase_url=settings.SUPABASE_URL,
            supabase_key=settings.SUPABASE_KEY,
            bucket_name=settings.SUPABASE_BUCKET_NAME
        )
    return LocalStorageService()
