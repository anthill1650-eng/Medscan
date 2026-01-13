from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Any, Dict, Optional
import os, uuid, shutil, time

# -----------------------
# In-memory job store
# -----------------------
JOBS: Dict[str, Dict[str, Any]] = {}

app = FastAPI(title="MedScan")

# -----------------------
# Models
# -----------------------
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
    status: str
    result: Optional[UploadRes] = None
    error: Optional[str] = None

# -----------------------
# Helpers
# -----------------------
def save_uploads(doc_id: str, files: List[UploadFile]) -> List[DocPage]:
    pages: List[DocPage] = []

    # Use a local folder that exists on Render too
    base_tmp = os.path.join(os.getcwd(), "tmp_uploads")
    os.makedirs(base_tmp, exist_ok=True)

    for idx, file in enumerate(files):
        filename = file.filename or f"page_{idx}.jpg"
        ext = filename.split(".")[-1].lower() if "." in filename else "jpg"
        key = f"{doc_id}/page_{idx}.{ext}"

        path = os.path.join(base_tmp, key)
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        pages.append(
            DocPage(
                id=f"page_{idx}",
                uri=key,
                width=0,
                height=0,
                page=idx,
                text=""
            )
        )

    return pages

def process_job(doc_id: str):
    """
    Placeholder background work.
    Replace this with real OCR later.
    """
    try:
        JOBS[doc_id]["status"] = "processing"
        time.sleep(2)  # simulate work

        # Put "processed" text into each page
        result: UploadRes = JOBS[doc_id]["result"]
        for p in result.pages:
            p.text = "processed (placeholder)"

        JOBS[doc_id]["status"] = "done"
        JOBS[doc_id]["result"] = result
        JOBS[doc_id]["error"] = None

    except Exception as e:
        JOBS[doc_id]["status"] = "error"
        JOBS[doc_id]["error"] = str(e)

# -----------------------
# Routes
# -----------------------
@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/upload", response_model=UploadRes)
async def upload(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    doc_id = str(uuid.uuid4())

    # 1) Save files
    pages = save_uploads(doc_id, files)

    # 2) IMPORTANT: Create the job RIGHT NOW so /status can find it
    placeholder = UploadRes(docId=doc_id, status="queued", pages=pages)
    JOBS[doc_id] = {
        "status": "queued",
        "result": placeholder,
        "error": None,
    }

    # 3) Start background processing using SAME doc_id
    background_tasks.add_task(process_job, doc_id)

    # 4) Return immediately
    return placeholder

@app.get("/status/{doc_id}", response_model=JobStatusRes)
def get_status(doc_id: str):
    job = JOBS.get(doc_id)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown docId")

    return JobStatusRes(
        docId=doc_id,
        status=job["status"],
        result=job.get("result"),
        error=job.get("error"),
    )
