import mimetypes
import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, File, HTTPException, Response, UploadFile
from app.adapters.storage.policy import PayloadPolicyManager, get_storage_adapter

router = APIRouter(prefix="/storage", tags=["Storage"])


@router.post("/upload", response_model=Dict[str, Any])
async def upload_file(file: UploadFile = File(...)):
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
    stored_key = await adapter.save(key, content, content_type=content_type)
    
    ref = PayloadPolicyManager.create_ref(
        storage_key=stored_key,
        size_bytes=len(content),
        content_type=content_type,
        filename=file.filename or "file",
    )
    return ref


@router.get("/download/{storage_key:path}")
async def download_file(storage_key: str):
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
