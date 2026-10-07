import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import httpx
from app.config import settings, UPLOADS_DIR

logger = logging.getLogger("app.storage")

class StorageManager:
    """
    Manages persistence of uploaded resume documents.
    Supports uploading to Supabase Storage under `<user_id>/<filename>`
    with automatic local caching and seamless offline fallback.
    """

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        bucket_name: Optional[str] = None
    ):
        self.supabase_url = (supabase_url or settings.SUPABASE_URL or "").rstrip("/")
        self.supabase_key = supabase_key or settings.SUPABASE_SERVICE_ROLE_KEY or ""
        self.bucket = bucket_name or settings.SUPABASE_STORAGE_BUCKET or "Resumes"

    @property
    def is_supabase_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)

    async def upload_resume(
        self,
        user_id: str,
        filename: str,
        content: bytes,
        content_type: str = "application/octet-stream"
    ) -> Dict[str, Any]:
        """
        Uploads resume binary to Supabase Storage:
        Path format: <user_id>/<filename>
        Also caches to local UPLOADS_DIR for instant layout parsing.
        """
        # 1. Always save a local copy for immediate parsing
        local_dest = UPLOADS_DIR / filename
        try:
            with open(local_dest, "wb") as f:
                f.write(content)
        except Exception as e:
            logger.warning(f"Could not write local cache file: {e}")

        storage_path = f"{user_id}/{filename}"
        public_url = None

        # 2. Upload to Supabase Storage if configured
        if self.is_supabase_enabled:
            endpoint = f"{self.supabase_url}/storage/v1/object/{self.bucket}/{storage_path}"
            headers = {
                "Authorization": f"Bearer {self.supabase_key}",
                "apikey": self.supabase_key,
                "x-upsert": "true",
                "Content-Type": content_type or "application/octet-stream"
            }
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(endpoint, headers=headers, content=content)
                    if resp.status_code in (200, 201):
                        logger.info(f"Successfully uploaded {storage_path} to Supabase bucket '{self.bucket}'.")
                        public_url = f"{self.supabase_url}/storage/v1/object/authenticated/{self.bucket}/{storage_path}"
                    else:
                        logger.error(f"Supabase upload failed ({resp.status_code}): {resp.text}")
            except Exception as e:
                logger.error(f"Error uploading to Supabase Storage: {e}")

        return {
            "storage_path": storage_path,
            "local_path": str(local_dest),
            "bucket": self.bucket if self.is_supabase_enabled else "local",
            "remote_url": public_url
        }

    async def get_resume_bytes(self, storage_path: str) -> Optional[bytes]:
        """
        Retrieves resume bytes from local cache or fetches from Supabase Storage.
        """
        filename = Path(storage_path).name
        local_dest = UPLOADS_DIR / filename
        if local_dest.exists():
            try:
                return local_dest.read_bytes()
            except Exception as e:
                logger.warning(f"Failed reading local resume file: {e}")

        if self.is_supabase_enabled:
            endpoint = f"{self.supabase_url}/storage/v1/object/{self.bucket}/{storage_path}"
            headers = {
                "Authorization": f"Bearer {self.supabase_key}",
                "apikey": self.supabase_key
            }
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(endpoint, headers=headers)
                    if resp.status_code == 200:
                        # Write back to local cache
                        with open(local_dest, "wb") as f:
                            f.write(resp.content)
                        return resp.content
            except Exception as e:
                logger.error(f"Error downloading from Supabase Storage: {e}")

        return None
