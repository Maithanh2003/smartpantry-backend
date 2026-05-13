from pathlib import Path
from uuid import uuid4

from app.core.media_urls import public_object_url
from app.core.object_storage import ObjectStorageClient


class PantryUploadService:
    def __init__(
        self,
        object_storage_client: ObjectStorageClient,
        *,
        max_size_bytes: int,
        allowed_mime_types: list[str],
        image_public_base_url: str | None = None,
    ) -> None:
        self.object_storage_client = object_storage_client
        self.max_size_bytes = max_size_bytes
        self.allowed_mime_types = allowed_mime_types
        self._image_public_base_url = image_public_base_url

    @staticmethod
    def _extension_from_mime(mime_type: str) -> str:
        mapping = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
        }
        return mapping.get(mime_type, "")

    def upload_pantry_image(
        self,
        *,
        user_id: int,
        filename: str | None,
        mime_type: str | None,
        content: bytes,
    ) -> dict:
        if not mime_type:
            raise ValueError("mime type is required")
        if mime_type not in self.allowed_mime_types:
            allowed = ", ".join(self.allowed_mime_types)
            raise ValueError(f"mime must be one of: {allowed}")
        if not content:
            raise ValueError("file is empty")
        if len(content) > self.max_size_bytes:
            raise ValueError(f"file too large, max {self.max_size_bytes} bytes")

        ext = self._extension_from_mime(mime_type)
        if not ext and filename:
            ext = Path(filename).suffix.lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise ValueError("file extension must be .jpg/.jpeg/.png/.webp")
        if ext == ".jpeg":
            ext = ".jpg"

        object_name = f"{uuid4().hex}{ext}"
        relative_path = f"pantry-items/{user_id}/{object_name}"

        self.object_storage_client.upload_bytes(
            path=relative_path,
            content=content,
            content_type=mime_type,
        )

        return {
            "path": relative_path,
            "image_url": public_object_url(self._image_public_base_url, relative_path),
            "mime_type": mime_type,
            "size_bytes": len(content),
        }
