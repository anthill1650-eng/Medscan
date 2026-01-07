from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

from appconfig import PROMPT_PATH, ALLOW_DIAGNOSIS, ALLOW_TREATMENT_ADVICE, SUMMARY_READING_LEVEL


def load_prompt(prompt_path: Path) -> str:
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8", errors="ignore").strip()


def summarize_text(text: str) -> Dict[str, Any]:
    """
    MVP summarizer (safe placeholder):
    - Loads your prompt rules (confirms path works)
    - Returns structured output
    - DOES NOT call external AI yet (no API keys needed)

    Later: replace mock_summary with an LLM call.
    """
    prompt = load_prompt(PROMPT_PATH)

    cleaned = (text or "").strip()
    if not cleaned:
        return {
            "ok": False,
            "error": "No text provided.",
            "summary": "",
            "meta": {
                "reading_level": SUMMARY_READING_LEVEL,
                "allow_diagnosis": ALLOW_DIAGNOSIS,
                "allow_treatment_advice": ALLOW_TREATMENT_ADVICE,
                "prompt_loaded": True,
            },
        }

    # Minimal placeholder summary so the endpoint works today:
    first_lines = [line.strip() for line in cleaned.splitlines() if line.strip()][:8]
    mock_summary = " ".join(first_lines)
    if len(mock_summary) > 700:
        mock_summary = mock_summary[:700].rstrip() + "..."

    return {
        "ok": True,
        "summary": mock_summary,
        "next_steps": [
            "Review your original document for accuracy.",
            "Write down any questions you want to ask your clinician.",
        ],
        "safety": {
            "diagnosis_allowed": ALLOW_DIAGNOSIS,
            "treatment_advice_allowed": ALLOW_TREATMENT_ADVICE,
            "note": "This app explains text from your document and does not provide medical advice.",
        },
        "meta": {
            "reading_level": SUMMARY_READING_LEVEL,
            "prompt_loaded": True,
            "prompt_path": str(PROMPT_PATH),
            "prompt_preview": prompt[:200],
        },
    }
