from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from typing import List
import shutil, uuid, os

app = FastAPI(title="MedScan")

# --- Pydantic models (Python-side) ---
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

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/upload", response_model=UploadRes)
async def upload(files: List[UploadFile] = File(...)):
    doc_id = str(uuid.uuid4())
    pages: List[DocPage] = []

    for idx, file in enumerate(files):
        filename = file.filename or f"page_{idx}.jpg"
        ext = filename.split(".")[-1] if "." in filename else "jpg"

        key = f"{doc_id}/page_{idx}.{ext}"

        # Windows-safe temp path (NOT /tmp)
        base_tmp = os.path.join(os.getcwd(), "tmp_uploads")
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
                text="",
            )
        )

    return UploadRes(docId=doc_id, pages=pages)

