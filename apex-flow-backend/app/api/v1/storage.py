import json
import mimetypes
import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from app.adapters.storage.policy import PayloadPolicyManager, get_storage_adapter
from app.api.deps import get_current_user_from_any_auth
from app.core.database import get_db

router = APIRouter(prefix="/storage", tags=["Storage"])


@router.post("/upload", response_model=Dict[str, Any])
async def upload_file(
    file: UploadFile = File(...),
    auth_user: uuid.UUID = Depends(get_current_user_from_any_auth),
):
    """Upload a file/payload artifact to durable storage and get an $apexflow_ref descriptor."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Cannot upload empty file.")

    ext = ""
    if file.filename and "." in file.filename:
        ext = "." + file.filename.rsplit(".", 1)[-1]
    
    unique_id = uuid.uuid4().hex[:12]
    key = f"payloads/{datetime.now(timezone.utc).strftime('%Y%m%d')}_{unique_id}{ext}"
    content_type = file.content_type or mimetypes.guess_type(file.filename or "")[0] or "application/octet-stream"

    adapter = get_storage_adapter()
    try:
        stored_key = await adapter.save(key, content, content_type=content_type)
    except ValueError as e:
        raise HTTPException(status_code=413, detail=str(e))

    is_encrypted = False
    key_hint = None
    if content_type == "application/json" or (file.filename and file.filename.endswith(".json")):
        try:
            parsed = json.loads(content.decode("utf-8"))
            if isinstance(parsed, dict) and parsed.get("$apexflow_encrypted") is True:
                is_encrypted = True
                key_hint = parsed.get("key_hint")
        except Exception:
            pass

    ref = PayloadPolicyManager.create_ref(
        storage_key=stored_key,
        size_bytes=len(content),
        content_type=content_type,
        filename=file.filename or "file",
        encrypted=is_encrypted,
        key_hint=key_hint,
    )
    return ref


@router.get("/download/{storage_key:path}")
async def download_file(
    storage_key: str,
    auth_user: uuid.UUID = Depends(get_current_user_from_any_auth),
):
    """Retrieve binary content or offloaded JSON for a given storage key."""
    adapter = get_storage_adapter()
    try:
        content = await adapter.get(storage_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Storage object '{storage_key}' not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    content_type = mimetypes.guess_type(storage_key)[0] or "application/octet-stream"
    if storage_key.endswith(".json"):
        content_type = "application/json"

    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'inline; filename="{storage_key.split("/")[-1]}"'},
    )
