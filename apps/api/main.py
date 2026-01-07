from fastapi import FastAPI, UploadFile, File
from typing import List
import shutil, uuid, os
from packages.shared.types import UploadRes, DocPage

app = FastAPI(title="MedScan")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/upload", response_model=UploadRes)
async def upload(files: List[UploadFile] = File(...)):
    doc_id = str(uuid.uuid4())
    pages: List[DocPage] = []
    for idx, file in enumerate(files):
        ext = file.filename.split(".")[-1]
        key = f"{doc_id}/page_{idx}.{ext}"
        path = f"/tmp/{key}"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        pages.append(DocPage(id=f"page_{idx}", uri=key, width=0, height=0))
    return UploadRes(docId=doc_id, pages=pages)
