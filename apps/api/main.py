from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Any, Dict, Optional
import shutil, uuid, os, json, time

app = FastAPI(title="MedScan")

# ----------------------------
# Models
# ----------------------------
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
    status: str               # queued | processing | done | error
    result: Optional[UploadRes] = None
    error: Optional[str] = None


# ----------------------------
# Storage helpers (durable jobs)
# ----------------------------
def uploads_root() -> str:
    # Works on Windows + Render Linux
    root = os.path.join(os.getcwd(), "tmp_uploads")
    os.makedirs(root, exist_ok=True)
    return root

def job_dir(doc_id: str) -> str:
    d = os.path.join(uploads_root(), doc_id)
    os.makedirs(d, exist_ok=True)
    return d

def job_file(doc_id: str) -> str:
    return os.path.join(job_dir(doc_id), "job.json")

def write_job(doc_id: str, payload: Dict[str, Any]) -> None:
    # Atomic-ish write
    path = job_file(doc_id)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)

def read_job(doc_id: str) -> Optional[Dict[str, Any]]:
    path = job_file(doc_id)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ----------------------------
# Background processing (placeholder OCR)
# ----------------------------
def do_processing(doc_id: str) -> None:
    """
    This runs in the background after upload.
    Replace the placeholder work with real OCR later.
    """
    try:
        job = read_job(doc_id)
        if not job:
            return

        job["status"] = "processing"
        job["error"] = None
        write_job(doc_id, job)

        # ---- Simulate work (replace with OCR later) ----
        time.sleep(2)

        # Put placeholder text into each page
        result = job.get("result") or {}
        pages = result.get("pages", [])
        for p in pages:
            if not p.get("text"):
                p["text"] = "processed (placeholder)"

        # IMPORTANT: set result status to done too
        result["status"] = "done"
        job["result"] = result
        job["status"] = "done"
        job["error"] = None
        write_job(doc_id, job)

    except Exception as e:
        # Persist the error so /status can return it
        job = read_job(doc_id) or {"docId": doc_id}
        job["status"] = "error"
        job["error"] = str(e)
        write_job(doc_id, job)


# ----------------------------
# Routes
# ----------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload", response_model=UploadRes)
async def upload(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    doc_id = str(uuid.uuid4())

    pages: List[Dict[str, Any]] = []

    # Save uploaded files
    for idx, file in enumerate(files):
        filename = file.filename or f"page_{idx}.jpg"
        ext = filename.split(".")[-1].lower() if "." in filename else "jpg"
        safe_ext = "png" if ext == "png" else "jpg"

        rel_uri = f"{doc_id}/page_{idx}.{safe_ext}"
        abs_path = os.path.join(uploads_root(), rel_uri)

        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        with open(abs_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        pages.append(
            {
                "id": f"page_{idx}",
                "uri": rel_uri,
                "width": 0,
                "height": 0,
                "page": idx,
                "text": "",
            }
        )

    # Immediate response (queued)
    result_payload = {
        "docId": doc_id,
        "status": "queued",
        "pages": pages,
    }

    # Durable job record (this is the big fix)
    job_payload = {
        "docId": doc_id,
        "status": "queued",
        "result": result_payload,
        "error": None,
        "createdAt": time.time(),
    }
    write_job(doc_id, job_payload)

    # Start background processing
    background_tasks.add_task(do_processing, doc_id)

    return result_payload


@app.get("/status/{doc_id}", response_model=JobStatusRes)
def get_status(doc_id: str):
    job = read_job(doc_id)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown docId")

    # Make sure shape always matches the response model
    return {
        "docId": job.get("docId", doc_id),
        "status": job.get("status", "queued"),
        "result": job.get("result"),
        "error": job.get("error"),
    }
