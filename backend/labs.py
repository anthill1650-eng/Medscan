from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


# Basic lab dictionary (expand over time)
LAB_INFO: Dict[str, str] = {
    "A1C": "Hemoglobin A1C: shows an estimate of your average blood sugar over about 2–3 months.",
    "HGB A1C": "Hemoglobin A1C: shows an estimate of your average blood sugar over about 2–3 months.",
    "GLUCOSE": "Glucose: the amount of sugar in your blood at the time of the test.",
    "WBC": "WBC (white blood cells): cells involved in fighting infection and inflammation.",
    "RBC": "RBC (red blood cells): cells that carry oxygen throughout the body.",
    "HGB": "Hemoglobin: oxygen-carrying protein in red blood cells.",
    "HCT": "Hematocrit: percentage of your blood made up of red blood cells.",
    "PLT": "Platelets: help your blood clot.",
    "NA": "Sodium: an electrolyte involved in fluid balance and nerve/muscle function.",
    "K": "Potassium: an electrolyte important for heart rhythm and muscle function.",
    "CL": "Chloride: an electrolyte involved in fluid balance and acid-base balance.",
    "CO2": "CO2/Bicarbonate: relates to acid-base balance in the blood.",
    "BUN": "BUN: a measure related to kidney function and protein metabolism.",
    "CREATININE": "Creatinine: a measure related to kidney function.",
    "EGFR": "eGFR: estimated kidney filtration rate (how well kidneys filter).",
    "ALT": "ALT: a liver enzyme that can rise with liver irritation/injury.",
    "AST": "AST: a liver enzyme that can rise with liver irritation/injury.",
    "ALK PHOS": "Alkaline phosphatase: an enzyme related to liver/bile ducts and bone.",
    "BILIRUBIN": "Bilirubin: a breakdown product processed by the liver.",
    "ALBUMIN": "Albumin: a protein made by the liver; relates to nutrition and fluid balance.",
    "TOTAL PROTEIN": "Total protein: includes albumin and other proteins in blood.",
    "LDL": "LDL cholesterol: often called 'bad' cholesterol.",
    "HDL": "HDL cholesterol: often called 'good' cholesterol.",
    "TRIGLYCERIDES": "Triglycerides: a type of fat in the blood.",
    "TOTAL CHOLESTEROL": "Total cholesterol: combined measure of cholesterol types.",
}


def _flag_to_status(flag: str) -> str:
    f = (flag or "").strip().upper()
    if f in {"H", "HIGH"}:
        return "high"
    if f in {"L", "LOW"}:
        return "low"
    if f in {"A", "ABN", "ABNORMAL"}:
        return "abnormal"
    if f in {"C", "CRITICAL"}:
        return "critical"
    return "unknown"


def _parse_value(token: str) -> Optional[float]:
    try:
        return float(token)
    except Exception:
        return None


def _parse_reference_range(rng: str) -> Optional[Tuple[float, float]]:
    """
    Accepts formats like:
    - "4.0-10.5"
    - "4.0 - 10.5"
    - "70-99"
    Returns (low, high) floats if possible.
    """
    if not rng:
        return None
    m = re.search(r"(-?\d+(\.\d+)?)\s*-\s*(-?\d+(\.\d+)?)", rng)
    if not m:
        return None
    low = _parse_value(m.group(1))
    high = _parse_value(m.group(3))
    if low is None or high is None:
        return None
    return (low, high)


def _status_from_range(value: Optional[float], ref: Optional[Tuple[float, float]]) -> Optional[str]:
    if value is None or ref is None:
        return None
    low, high = ref
    if value < low:
        return "low"
    if value > high:
        return "high"
    return "in_range"


def find_labs(text: str) -> List[Dict[str, Any]]:
    """
    Heuristic lab extraction.
    Tries to find patterns like:
      A1C 6.1 (H)
      GLUCOSE 102 H
      WBC 8.2 4.0-10.5
      Creatinine: 1.10 (0.70-1.30)

    Returns list of dicts with:
      name, value, units, flag, status, reference_range, explanation
    """
    if not text:
        return []

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    results: List[Dict[str, Any]] = []

    # Pattern: NAME <value> (<flag>) [units] [ref]
    # Example: A1C 6.1 (H)
    p1 = re.compile(
        r"^(?P<name>[A-Za-z][A-Za-z0-9\s\/\-\%]+?)[:\s]+(?P<value>-?\d+(\.\d+)?)\s*(?P<units>[A-Za-z%\/\.\-\s]{0,12})?\s*(\((?P<flag>[A-Za-z]+)\))?\s*(?P<ref>\d+(\.\d+)?\s*-\s*\d+(\.\d+)?)?$",
        re.IGNORECASE,
    )

    # Pattern: NAME <value> <flag> [units] [ref]
    # Example: GLUCOSE 102 H 70-99
    p2 = re.compile(
        r"^(?P<name>[A-Za-z][A-Za-z0-9\s\/\-\%]+?)\s+(?P<value>-?\d+(\.\d+)?)\s+(?P<flag>H|L|A|ABN|HIGH|LOW|ABNORMAL|CRITICAL|C)\s*(?P<units>[A-Za-z%\/\.\-\s]{0,12})?\s*(?P<ref>\d+(\.\d+)?\s*-\s*\d+(\.\d+)?)?$",
        re.IGNORECASE,
    )

    for ln in lines:
        m = p2.match(ln) or p1.match(ln)
        if not m:
            continue

        raw_name = (m.group("name") or "").strip()
        if not raw_name:
            continue

        # Normalize name key for lookup
        key = raw_name.upper().strip()
        key = re.sub(r"\s+", " ", key)

        value = _parse_value(m.group("value") or "")
        units = ((m.group("units") or "") or "").strip()
        flag = ((m.group("flag") or "") or "").strip()
        ref_text = ((m.group("ref") or "") or "").strip()

        # Determine status
        status: Optional[str] = None
        if flag:
            status = _flag_to_status(flag)
        else:
            ref_tuple = _parse_reference_range(ref_text)
            status = _status_from_range(value, ref_tuple)

        # Lookup explanation
        explanation = LAB_INFO.get(key)
        if not explanation:
            # try some common normalization variants
            explanation = LAB_INFO.get(key.replace("HEMOGLOBIN ", "HGB "))
        if not explanation:
            explanation = "Lab test: explanation not yet added."

        results.append(
            {
                "name": raw_name,
                "value": value,
                "units": units if units else None,
                "flag": flag if flag else None,
                "reference_range": ref_text if ref_text else None,
                "status": status,
                "explanation": explanation,
            }
        )

    # Deduplicate by (name,value,flag)
    dedup: List[Dict[str, Any]] = []
    seen = set()
    for r in results:
        sig = (r.get("name"), r.get("value"), r.get("flag"), r.get("reference_range"))
        if sig in seen:
            continue
        seen.add(sig)
        dedup.append(r)

    return dedup
