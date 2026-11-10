"""Where uploaded photos live.

Locally they are written to the uploads folder and served from /uploads. On Vercel the filesystem is
read-only, so when BLOB_READ_WRITE_TOKEN is set (a connected Vercel Blob store) they go to Blob instead
and the photo row stores the absolute Blob URL.
"""
import os
import shutil

from app.config import uploads_path

BLOB_HOST = ".blob.vercel-storage.com/"


def blob_enabled() -> bool:
    return bool(os.environ.get("BLOB_READ_WRITE_TOKEN"))


def save_photo(property_id: int, name: str, data: bytes, content_type: str) -> str:
    """Store one photo and return the URL to save in the photo row."""
    if blob_enabled():
        from vercel.blob import sync

        result = sync.put_blob(f"properties/{property_id}/{name}", data, access="public",
                               content_type=content_type)
        return result.url
    folder = uploads_path() / "properties" / str(property_id)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_bytes(data)
    return f"/uploads/properties/{property_id}/{name}"


def remove_photo(url: str) -> None:
    """Delete an uploaded photo's file; seed photos and external URLs are left alone."""
    if BLOB_HOST in url:
        if blob_enabled():
            from vercel.blob import sync

            try:
                sync.delete_blob(url)
            except Exception:  # a missing blob must not fail the request
                pass
    elif url.startswith("/uploads/properties/"):
        (uploads_path() / url.removeprefix("/uploads/")).unlink(missing_ok=True)


def remove_property_photos(property_id: int, urls: list[str]) -> None:
    for url in urls:
        if BLOB_HOST in url:
            remove_photo(url)
    shutil.rmtree(uploads_path() / "properties" / str(property_id), ignore_errors=True)
