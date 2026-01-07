"""
Medical terms + abbreviations expansion will live here later.
"""
from __future__ import annotations

import re
from typing import Dict, List


# Expand this list over time
ABBREVIATIONS: Dict[str, str] = {
    "DX": "Diagnosis",
    "HTN": "Hypertension (high blood pressure)",
    "DM": "Diabetes mellitus (diabetes)",
    "HLD": "Hyperlipidemia (high cholesterol)",
    "BID": "Twice a day",
    "TID": "Three times a day",
    "QID": "Four times a day",
    "QD": "Once daily",
    "QHS": "Every night at bedtime",
    "PRN": "As needed",
    "PO": "By mouth",
    "IV": "Into a vein",
    "IM": "Into a muscle",
    "SOB": "Shortness of breath",
    "CP": "Chest pain",
    "WNL": "Within normal limits",
    "CBC": "Complete blood count (blood test)",
    "CMP": "Comprehensive metabolic panel (blood test)",
    "A1C": "Hemoglobin A1C (average blood sugar over ~3 months)",
}


def find_terms(text: str) -> List[str]:
    """
    Return a de-duplicated list of abbreviations found in the text.
    Uses word-boundary matching to reduce false positives.
    """
    if not text:
        return []

    upper = text.upper()
    found: List[str] = []

    for abbr in ABBREVIATIONS.keys():
        # Word boundary match, allows punctuation next to term (e.g., "HTN," "Dx:")
        pattern = rf"\b{re.escape(abbr)}\b"
        if re.search(pattern, upper):
            found.append(abbr)

    # Sort for stable output
    return sorted(set(found))


def explain_terms(terms: List[str]) -> Dict[str, str]:
    """
    Map found abbreviations to plain-English explanations.
    """
    return {t: ABBREVIATIONS.get(t, "Unknown term") for t in terms}
