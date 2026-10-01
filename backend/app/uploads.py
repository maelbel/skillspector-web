"""Skills uploaded from the browser: a .zip, or a .md file on its own, held only while it's scanned.

Self-hosted (the `local` store), the API receives the file and keeps it under data/uploads/<scan>.
Hosted (`blob`), function request bodies are limited to 4.5 MB, so the browser uploads straight to
the project's private Vercel Blob store under uploads/<user id>/ (server/api/scan/upload-token.post.ts
hands it a token for that), and the scan names the blob's pathname: its URL is always built from
this server's own token, never taken from the request.

A scan's target is `upload:<file name>`, and its `upload` column says where the file is: a local
path, or `blob:<pathname>`. The file is deleted when the scan ends, whatever its outcome; ones a
scan never got to are swept on startup (local) or with retention (blob).
"""

from __future__ import annotations

import io
import logging
import os
import re
import shutil
import tempfile
import time
import zipfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path, PurePosixPath
from typing import Literal

from app.core.config import Settings, get_settings
from app.core.mode import Mode

logger = logging.getLogger(__name__)

UploadStore = Literal["local", "blob"]

# The target a scan of an upload is recorded with: the file's name, after this prefix.
TARGET_PREFIX = "upload:"
BLOB_PREFIX = "blob:"
BLOB_FOLDER = "uploads"
# Compressed; skillspector's own limits then apply to what a zip unpacks to.
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
SUFFIXES = (".zip", ".md")
# A blob a scan never got to (its queueing failed, or the browser gave up) is swept after this long:
# longer than a queued scan may wait (app/jobs/vercel_queues.py).
STALE_BLOB_SECONDS = 7 * 3600

_SAFE_NAME = re.compile(r"[^\w.\- ()]+")


class UploadRejectedError(ValueError):
    """An upload that can't be scanned, with the reason to show."""


def store_kind(settings: Settings | None = None) -> UploadStore | None:
    """SKILLSPECTOR_WEB_UPLOAD_STORE when set, otherwise the mode's default; None when that's the
    Blob store and it isn't connected (no BLOB_READ_WRITE_TOKEN), so uploads are off."""
    settings = settings or get_settings()
    kind = settings.upload_store or ("blob" if settings.mode is Mode.HOSTED else "local")
    if kind == "blob" and not any(os.environ.get(name) for name in ("BLOB_READ_WRITE_TOKEN", "VERCEL_BLOB_READ_WRITE_TOKEN")):
        return None
    return kind


NOT_SET_UP = "Uploads aren't set up on this server: scan a link instead"


def target_for(name: str) -> str:
    return TARGET_PREFIX + name


def is_upload_target(target: str) -> bool:
    return target.startswith(TARGET_PREFIX)


def safe_name(name: str) -> str:
    """The uploaded file's own name, without folders or odd characters; refused unless .zip or .md."""
    base = PurePosixPath(name.replace("\\", "/")).name
    base = _SAFE_NAME.sub("_", base).strip(" .")[:100]
    if not base.lower().endswith(SUFFIXES):
        raise UploadRejectedError("Upload a .zip of the skill, or its SKILL.md")
    return base


def check_content(name: str, data: bytes) -> None:
    """Refuse an upload skillspector can't scan, with the reason, before it's queued.

    skillspector checks a zip again when it unpacks it (sizes, entry count, paths); this catches a
    broken or oversized one early, with a message, rather than as a failed scan.
    """
    from skillspector.input_handler import INGEST_MAX_BYTES, INGEST_MAX_ZIP_MEMBERS

    if not data:
        raise UploadRejectedError(f"{name} is empty")
    if len(data) > MAX_UPLOAD_BYTES:
        raise UploadRejectedError(f"{name} is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB")
    if not name.lower().endswith(".zip"):
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise UploadRejectedError(f"{name} isn't a text file") from exc
        return
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = archive.infolist()
    except (zipfile.BadZipFile, ValueError) as exc:
        raise UploadRejectedError(f"{name} isn't a valid zip archive") from exc
    if not any(not member.is_dir() for member in members):
        raise UploadRejectedError(f"{name} holds no files")
    if len(members) > INGEST_MAX_ZIP_MEMBERS:
        raise UploadRejectedError(f"{name} holds more than {INGEST_MAX_ZIP_MEMBERS} entries")
    if sum(member.file_size for member in members) > INGEST_MAX_BYTES:
        raise UploadRejectedError(f"{name} unpacks to more than {INGEST_MAX_BYTES // (1024 * 1024)} MB")
    for member in members:
        path = PurePosixPath(member.filename.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts:
            raise UploadRejectedError(f"{name} holds a file outside the archive: {member.filename}")


# Local store.


def _local_root() -> Path:
    return Path(get_settings().db_path).parent / "uploads"


def save_local(scan_id: str, name: str, data: bytes) -> str:
    """Keep an upload for its scan; the reference to store with the scan."""
    folder = _local_root() / scan_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_bytes(data)
    return str(path)


def clear_local() -> None:
    """Delete every local upload: on startup, when no scan can be running."""
    shutil.rmtree(_local_root(), ignore_errors=True)


# Blob store.


def blob_pathname_for(user_id: str | None, pathname: str) -> str:
    """The pathname, if it's an upload of this user's; refused otherwise.

    Tokens are only issued for uploads/<user id>/ (server/api/scan/upload-token.post.ts), so another
    user's upload, or any other blob in the store, can't be scanned by naming it.
    """
    path = PurePosixPath(pathname)
    if (
        not user_id
        or path.is_absolute()
        or ".." in path.parts
        or len(path.parts) != 3
        or path.parts[:2] != (BLOB_FOLDER, user_id)
    ):
        raise UploadRejectedError("That upload can't be scanned: upload the file again")
    return str(path)


async def read_blob(pathname: str) -> bytes:
    from vercel.blob import BlobNotFoundError, get_async

    try:
        result = await get_async(pathname, access="private", use_cache=False)
    except BlobNotFoundError as exc:
        raise UploadRejectedError("The uploaded file is gone: upload it again") from exc
    return result.content


async def sweep_stale_blobs(*, now: float | None = None) -> int:
    """Delete uploads older than STALE_BLOB_SECONDS, which no scan will read any more."""
    from vercel.blob import delete_async, iter_objects_async

    cutoff = (now or time.time()) - STALE_BLOB_SECONDS
    stale = [item.pathname async for item in iter_objects_async(prefix=f"{BLOB_FOLDER}/") if item.uploaded_at.timestamp() < cutoff]
    if stale:
        await delete_async(stale)
    return len(stale)


# Either store.


async def read(ref: str) -> bytes:
    if ref.startswith(BLOB_PREFIX):
        return await read_blob(ref.removeprefix(BLOB_PREFIX))
    return Path(ref).read_bytes()


@asynccontextmanager
async def local_copy(ref: str, name: str) -> AsyncIterator[str]:
    """A path on this machine holding the upload, under its own name (skillspector goes by the suffix)."""
    if not ref.startswith(BLOB_PREFIX):
        yield ref
        return
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / name
        path.write_bytes(await read(ref))
        yield str(path)


async def delete(ref: str | None) -> None:
    """Delete a scan's upload. Never raises: the scan's outcome matters more than a leftover file."""
    if not ref:
        return
    try:
        if ref.startswith(BLOB_PREFIX):
            from vercel.blob import delete_async

            await delete_async(ref.removeprefix(BLOB_PREFIX))
        else:
            folder = Path(ref).resolve().parent
            # Only ever a scan's own folder of uploads.
            if folder.parent == _local_root().resolve():
                shutil.rmtree(folder, ignore_errors=True)
    except Exception:
        logger.warning("Couldn't delete the upload %s; the retention sweep will", ref, exc_info=True)
