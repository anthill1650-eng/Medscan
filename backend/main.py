from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel

from appconfig import APP_NAME, APP_VERSION
from summarizer import summarize_text

app = FastAPI(title=APP_NAME, version=APP_VERSION)


class SummarizeRequest(BaseModel):
    text: str


@app.get("/health")
def health():
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}


@app.post("/summarize")
def summarize(req: SummarizeRequest):
    """
    MVP endpoint: take raw text and return a plain-English summary response.
    """
    return summarize_text(req.text)


@app.post("/summarize-file")
async def summarize_file(file: UploadFile = File(...)):
    """
    MVP endpoint: accept a text file for now (no OCR yet).
    Later you'll support PDFs/images -> OCR -> text.
    """
    content = await file.read()
    text = content.decode("utf-8", errors="ignore")
    return summarize_text(text)
