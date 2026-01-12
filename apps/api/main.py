from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Any, Dict, Optional
import shutil
import uuid
import os
import time

app = FastAPI(title="MedScan")

# -------------------------
# Models
# -------------------------
class DocPage(BaseModel):
    id: str
    uri: str
    width: int = 0
    height: int = 0
    page: int = 0
    text: str = ""

class UploadRes(BaseModel):
    docId: str
    pages: List[DocPage]

# -------------------------
# In-memory job store
# (works for Render Free single instance)
# -------------------------
JOBS: Dict[str, Dict[str, Any]] = {}

# -------------------------
# Routes
# -------------------------
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/status/{doc_id}")
def get_status(doc_id: str):
    job = JOBS.get(doc_id)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown docId")
    return job

@app.post("/upload")
async def upload(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    """
    Upload returns FAST with docId + queued status.
    Background task does the slow processing.
    """
    doc_id = str(uuid.uuid4())

    # Use a local folder. On Render, /tmp is safest.
    # We'll use /tmp if available; otherwise fall back to repo tmp_uploads.
    base_tmp = "/tmp" if os.path.isdir("/tmp") else os.path.join(os.getcwd(), "tmp_uploads")
    os.makedirs(base_tmp, exist_ok=True)

    saved_paths: List[str] = []
    uris: List[str] = []

    for idx, file in enumerate(files):
        filename = file.filename or f"page_{idx}.jpg"
        ext = filename.split(".")[-1] if "." in filename else "jpg"
        key = f"{doc_id}/page_{idx}.{ext}"

        path = os.path.join(base_tmp, key)
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        saved_paths.append(path)
        uris.append(key)

    # Create job record
    JOBS[doc_id] = {
        "docId": doc_id,
        "status": "queued",     # queued -> processing -> done/error
        "created_at": time.time(),
        "result": None,
        "error": None,
    }

    # Kick off slow work
    background_tasks.add_task(run_processing_job, doc_id, saved_paths, uris)

    # Return FAST
    return {"docId": doc_id, "status": "queued"}

# -------------------------
# Background processing
# -------------------------
def run_processing_job(doc_id: str, saved_paths: List[str], uris: List[str]) -> None:
    """
    Put your real OCR/AI pipeline here.
    For now, it creates placeholder text so you can test polling end-to-end.
    """
    try:
        JOBS[doc_id]["status"] = "processing"
        JOBS[doc_id]["started_at"] = time.time()

        pages: List[Dict[str, Any]] = []

        # ---- PLACEHOLDER WORK (replace later) ----
        # Simulate "slow" work per page
        for i, _path in enumerate(saved_paths):
            # pretend OCR takes time
            time.sleep(1)
            pages.append(
                {
                    "id": f"page_{i}",
                    "uri": uris[i],
                    "width": 0,
                    "height": 0,
                    "page": i,
                    "text": "processed (placeholder)",
                }
            )
        # ------------------------------------------

        JOBS[doc_id]["status"] = "done"
        JOBS[doc_id]["result"] = {"docId": doc_id, "pages": pages}
        JOBS[doc_id]["finished_at"] = time.time()

    except Exception as e:
        JOBS[doc_id]["status"] = "error"
        JOBS[doc_id]["error"] = str(e)
        JOBS[doc_id]["finished_at"] = time.time()
