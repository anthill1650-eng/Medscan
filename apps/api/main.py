from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Any, Dict, Optional
import shutil
import uuid
import os
import time

# In-memory job store (fine for MVP). On Render Free it can reset if the instance restarts.
JOBS: Dict[str, Dict[str, Any]] = {}

app = FastAPI(title="MedScan")


# ---------- Models ----------
class DocPage(BaseModel):
    id: str
    uri: str
    width: int = 0
    height: int = 0
    page: int = 0
    text: str = ""


class UploadRes(BaseModel):
    docId: str
    status: str
    pages: List[DocPage]


class JobStatusRes(BaseModel):
    docId: str
    status: str  # queued | processing | done | error
    result: Optional[UploadRes] = None
    error: Optional[str] = None


# ---------- Helpers ----------
def ensure_tmp_root() -> str:
    # Always store in project working directory so it works on Windows + Render
    base_tmp = os.path.join(os.getcwd(), "tmp_uploads")
    os.makedirs(base_tmp, exist_ok=True)
    return base_tmp


def save_upload_to_disk(doc_id: str, idx: int, file: UploadFile) -> str:
    filename = file.filename or f"page_{idx}.jpg"
    ext = filename.split(".")[-1] if "." in filename else "jpg"
    key = f"{doc_id}/page_{idx}.{ext}"

    base_tmp = ensure_tmp_root()
    path = os.path.join(base_tmp, key)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # We return a "uri key" (relative). You can later map it to a real URL if you add storage/CDN.
    return key


def run_processing_job(doc_id: str, saved_keys: List[str]) -> None:
    """
    Background job: simulate OCR / processing.
    Replace the placeholder section with your real OCR pipeline later.
    """
    try:
        if doc_id not in JOBS:
            return

        JOBS[doc_id]["status"] = "processing"
        JOBS[doc_id]["updated_at"] = time.time()

        # ---- Placeholder "processing" delay ----
        time.sleep(2)

        # IMPORTANT: Always keep result/pages structure stable.
        res = JOBS[doc_id].get("result") or {"docId": doc_id, "status": "done", "pages": []}
        pages = res.get("pages") or []

        # Fill texts (placeholder)
        for i in range(min(len(pages), len(saved_keys))):
            pages[i]["text"] = "processed (placeholder)"

        res["pages"] = pages
        res["status"] = "done"

        JOBS[doc_id]["result"] = res
        JOBS[doc_id]["status"] = "done"
        JOBS[doc_id]["updated_at"] = time.time()

    except Exception as e:
        if doc_id in JOBS:
            JOBS[doc_id]["status"] = "error"
            JOBS[doc_id]["error"] = str(e)
            JOBS[doc_id]["updated_at"] = time.time()


# ---------- Routes ----------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload", response_model=UploadRes)
async def upload(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    doc_id = str(uuid.uuid4())
    saved_keys: List[str] = []

    # Save files first
    for idx, file in enumerate(files):
        saved_keys.append(save_upload_to_disk(doc_id, idx, file))

    # Create stable placeholder result immediately (so client never sees missing pages)
    placeholder_pages = [
        {
            "id": f"page_{i}",
            "uri": saved_keys[i],
            "width": 0,
            "height": 0,
            "page": i,
            "text": "",
        }
        for i in range(len(saved_keys))
    ]

    JOBS[doc_id] = {
        "docId": doc_id,
        "status": "queued",
        "error": None,
        "created_at": time.time(),
        "updated_at": time.time(),
        "result": {
            "docId": doc_id,
            "status": "queued",
            "pages": placeholder_pages,
        },
    }

    # Kick off background processing
    background_tasks.add_task(run_processing_job, doc_id, saved_keys)

    # Return fast: docId + queued
    return UploadRes(
        docId=doc_id,
        status="queued",
        pages=[DocPage(**p) for p in placeholder_pages],
    )


@app.get("/status/{doc_id}", response_model=JobStatusRes)
def get_status(doc_id: str):
    job = JOBS.get(doc_id)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown docId")

    return JobStatusRes(
        docId=doc_id,
        status=job.get("status", "queued"),
        result=job.get("result"),
        error=job.get("error"),
    )
