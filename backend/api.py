from typing import Any, Dict, List, Optional

from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel

from labs import find_labs, parse_range
from ocr import ocr_image_bytes

app = FastAPI(title="MediScan API")


class ParseRequest(BaseModel):
    text: str


def _fmt_range(r: Optional[str]) -> str:
    return r if r else "not provided"


def _lab_sentence(item: Dict[str, Any]) -> str:
    name = item.get("name", "Lab")
    value = item.get("value")
    units = item.get("units") or ""
    status = item.get("status") or "unknown"
    ref = _fmt_range(item.get("reference_range"))

    if status == "high":
        meaning = "is higher than expected"
    elif status == "low":
        meaning = "is lower than expected"
    elif status == "in_range":
        meaning = "is within the expected range"
    else:
        meaning = "could not be compared to a reference range"

    v = f"{value:g}" if isinstance(value, (int, float)) else str(value)
    u = f" {units}" if units else ""
    return f"{name} is {v}{u}, which {meaning} (ref: {ref})."


def _counts_summary(results: List[Dict[str, Any]]) -> str:
    if not results:
        return "No lab results were detected in the text."

    counts = {"high": 0, "low": 0, "in_range": 0, "unknown": 0}
    for r in results:
        s = r.get("status")
        if s in counts:
            counts[s] += 1
        else:
            counts["unknown"] += 1

    return (
        f"Summary: {counts['high']} high, "
        f"{counts['low']} low, "
        f"{counts['in_range']} in range, "
        f"{counts['unknown']} unknown."
    )


def _severity(item: Dict[str, Any]) -> str:
    status = item.get("status")
    if status not in ("high", "low"):
        return "none" if status == "in_range" else "unknown"

    value = item.get("value")
    if not isinstance(value, (int, float)):
        return "unknown"

    ref = item.get("reference_range")
    if not ref:
        return "unknown"

    rng = parse_range(ref)
    if not rng:
        return "unknown"

    lo, hi = rng
    if status == "high" and hi > 0:
        pct = (value - hi) / hi
    elif status == "low" and lo > 0:
        pct = (lo - value) / lo
    else:
        return "unknown"

    if pct <= 0.10:
        return "mild"
    if pct <= 0.25:
        return "moderate"
    return "severe"


def _canonical_name(name: str) -> str:
    return (name or "").strip().upper()


def _next_steps(item: Dict[str, Any]) -> List[str]:
    name = _canonical_name(item.get("name", ""))
    status = item.get("status") or "unknown"

    steps: List[str] = []

    # In-range guidance (2 short bullets)
    if status == "in_range":
        steps.append("This result is within the expected range based on the reference range shown.")
        steps.append("If you have symptoms or concerns, discuss them with a clinician even if labs look normal.")
        return steps[:4]

    # Unknown / no comparison
    if status not in ("high", "low"):
        steps.append("This result could not be compared to a reference range from the text provided.")
        steps.append("If you have the full report, compare it to the reference range listed there or review it with a clinician.")
        return steps[:4]

    # Generic out-of-range guidance
    steps.append("Review this result in context with your other labs, symptoms, and medical history.")
    steps.append("If you have a prior result, comparing trends over time can be more helpful than one number.")

    # GLUCOSE-specific
    if "GLUCOSE" in name:
        if status == "high":
            steps.insert(0, "If this was a fasting glucose, a repeat fasting test may help confirm the result.")
            steps.insert(1, "If this was not fasting, ask whether a fasting re-check is appropriate.")
        else:
            steps.insert(0, "If you felt shaky, sweaty, confused, or weak around the test time, note it and mention it to a clinician.")

    # A1C-specific (no fasting mention)
    if ("A1C" in name) or ("HEMOGLOBIN A1C" in name) or ("HBA1C" in name):
        if status == "high":
            steps.insert(0, "A1C reflects average blood sugar over ~2–3 months; it’s often reviewed together with glucose results.")
            steps.insert(1, "Ask about follow-up timing and what A1C target range applies to you personally.")

    # WBC-specific
    if name == "WBC" or "WHITE BLOOD" in name:
        steps.insert(0, "WBC can change with infection, inflammation, stress, or some medications—context matters.")
        steps.append("If you were sick recently or took steroids, mention that when reviewing the result.")

    # CREATININE-specific
    if "CREATININE" in name:
        steps.insert(0, "Creatinine can be influenced by hydration, muscle mass, and some medications; it’s often reviewed with other kidney markers.")
        steps.append("If your report includes eGFR or BUN, reviewing them together can give better kidney context.")

    return steps[:4]


from typing import Any, Dict, List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from labs import find_labs, parse_range
from ocr import ocr_image_bytes
from db import init_db, save_scan, list_scans, get_scan

app = FastAPI(title="MediScan API", version="0.2.0")

# CORS: allow your local frontend server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ParseRequest(BaseModel):
    text: str


@app.on_event("startup")
def _startup() -> None:
    init_db()


def _fmt_range(r: Optional[str]) -> str:
    return r if r else "not provided"


def _lab_sentence(item: Dict[str, Any]) -> str:
    name = item.get("name", "Lab")
    value = item.get("value")
    units = item.get("units") or ""
    status = item.get("status") or "unknown"
    ref = _fmt_range(item.get("reference_range"))

    if status == "high":
        meaning = "is higher than expected"
    elif status == "low":
        meaning = "is lower than expected"
    elif status == "in_range":
        meaning = "is within the expected range"
    else:
        meaning = "could not be compared to a reference range"

    v = f"{value:g}" if isinstance(value, (int, float)) else str(value)
    u = f" {units}" if units else ""
    return f"{name} is {v}{u}, which {meaning} (ref: {ref})."


def _counts_summary(results: List[Dict[str, Any]]) -> str:
    if not results:
        return "No lab results were detected in the text."

    counts = {"high": 0, "low": 0, "in_range": 0, "unknown": 0}
    for r in results:
        s = r.get("status")
        if s in counts:
            counts[s] += 1
        else:
            counts["unknown"] += 1

    return (
        f"Summary: {counts['high']} high, "
        f"{counts['low']} low, "
        f"{counts['in_range']} in range, "
        f"{counts['unknown']} unknown."
    )


def _severity(item: Dict[str, Any]) -> str:
    status = item.get("status")
    if status not in ("high", "low"):
        return "none" if status == "in_range" else "unknown"

    value = item.get("value")
    if not isinstance(value, (int, float)):
        return "unknown"

    ref = item.get("reference_range")
    if not ref:
        return "unknown"

    rng = parse_range(ref)
    if not rng:
        return "unknown"

    lo, hi = rng
    if status == "high" and hi > 0:
        pct = (value - hi) / hi
    elif status == "low" and lo > 0:
        pct = (lo - value) / lo
    else:
        return "unknown"

    if pct <= 0.10:
        return "mild"
    if pct <= 0.25:
        return "moderate"
    return "severe"


def _canonical_name(name: str) -> str:
    return (name or "").strip().upper()


def _next_steps(item: Dict[str, Any]) -> List[str]:
    name = _canonical_name(item.get("name", ""))
    status = item.get("status") or "unknown"
    steps: List[str] = []

    if status == "in_range":
        steps.append("This result is within the expected range based on the reference range shown.")
        steps.append("If you have symptoms or concerns, discuss them with a clinician even if labs look normal.")
        return steps[:4]

    if status not in ("high", "low"):
        steps.append("This result could not be compared to a reference range from the text provided.")
        steps.append("If you have the full report, compare it to the reference range listed there or review it with a clinician.")
        return steps[:4]

    steps.append("Review this result in context with your other labs, symptoms, and medical history.")
    steps.append("If you have a prior result, comparing trends over time can be more helpful than one number.")

    if "GLUCOSE" in name:
        if status == "high":
            steps.insert(0, "If this was a fasting glucose, a repeat fasting test may help confirm the result.")
            steps.insert(1, "If this was not fasting, ask whether a fasting re-check is appropriate.")
        else:
            steps.insert(0, "If you felt shaky, sweaty, confused, or weak around the test time, note it and mention it to a clinician.")

    if ("A1C" in name) or ("HEMOGLOBIN A1C" in name) or ("HBA1C" in name):
        if status == "high":
            steps.insert(0, "A1C reflects average blood sugar over ~2–3 months; it’s often reviewed together with glucose results.")
            steps.insert(1, "Ask about follow-up timing and what A1C target range applies to you personally.")

    if name == "WBC" or "WHITE BLOOD" in name:
        steps.insert(0, "WBC can change with infection, inflammation, stress, or some medications—context matters.")
        steps.append("If you were sick recently or took steroids, mention that when reviewing the result.")

    if "CREATININE" in name:
        steps.insert(0, "Creatinine can be influenced by hydration, muscle mass, and some medications; it’s often reviewed with other kidney markers.")
        steps.append("If your report includes eGFR or BUN, reviewing them together can give better kidney context.")

    return steps[:4]


def _safety_note() -> str:
    return (
        "Note: This is informational only and not medical advice. "
        "If you have symptoms or concerns, or if a result is very high or low, contact a clinician."
    )


def _explain_from_text(text: str) -> Dict[str, Any]:
    results = find_labs(text)
    items_out = []
    for item in results:
        items_out.append(
            {
                "name": item.get("name"),
                "panel": item.get("panel"),
                "status": item.get("status"),
                "severity": _severity(item),
                "sentence": _lab_sentence(item),
                "what_it_is": item.get("explanation"),
                "next_steps": _next_steps(item),
            }
        )

    return {
        "count": len(results),
        "overall_summary": _counts_summary(results),
        "items": items_out,
        "note": _safety_note(),
    }


@app.get("/")
def health_check():
    return {"status": "MediScan running"}


@app.post("/parse-labs")
def parse_labs(req: ParseRequest):
    results = find_labs(req.text)
    return {"count": len(results), "results": results}


@app.post("/explain-labs")
def explain_labs(req: ParseRequest):
    return _explain_from_text(req.text)


@app.post("/scan-image")
async def scan_image(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail=f"Please upload an image file (received {file.content_type}).")

    image_bytes = await file.read()

    try:
        extracted_text = ocr_image_bytes(image_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"OCR failed. Make sure Tesseract-OCR is installed and configured. Details: {e}",
        )

    output = _explain_from_text(extracted_text)
    output["ocr_text_preview"] = extracted_text[:800]

    # Save scan to SQLite
    scan_id = save_scan(
        filename=file.filename,
        content_type=file.content_type,
        ocr_text=extracted_text,
        result=output,
    )

    output["scan_id"] = scan_id
    return output


# ---- History endpoints ----

@app.get("/scans")
def scans(limit: int = 50):
    return {"count": len(list_scans(limit=limit)), "results": list_scans(limit=limit)}


@app.get("/scans/{scan_id}")
def scan_detail(scan_id: int):
    data = get_scan(scan_id)
    if not data:
        raise HTTPException(status_code=404, detail="Scan not found.")
    return data
