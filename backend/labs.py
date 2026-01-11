import re
from typing import Any, Dict, List, Optional, Tuple

LAB_INFO: Dict[str, str] = {
    "A1C": "Hemoglobin A1C: estimate of average blood sugar over about 2–3 months.",
    "GLUCOSE": "Glucose: the amount of sugar in your blood at the time of the test.",
    "WBC": "White blood cells: help fight infection.",
    "CREATININE": "Creatinine: related to kidney function.",
}

PANEL_MAP: Dict[str, str] = {
    "A1C": "Diabetes",
    "GLUCOSE": "Diabetes",
    "WBC": "CBC",
    "CREATININE": "CMP",
}

ALIASES: Dict[str, str] = {
    "HEMOGLOBIN A1C": "A1C",
    "HBA1C": "A1C",
    "A1C": "A1C",
    "GLUCOSE": "GLUCOSE",
    "WBC": "WBC",
    "WHITE BLOOD CELLS": "WBC",
    "CREATININE": "CREATININE",
}

# Default ranges used when a lab line doesn't include a reference range.
# These ranges can vary by lab; treat them as reasonable defaults.
DEFAULT_RANGES: Dict[str, Tuple[float, float]] = {
    "A1C": (4.0, 5.6),
    "GLUCOSE": (70.0, 99.0),
}

UNITS = r"(?:%|mg\/dL|K\/uL)"

def normalize(name: str) -> str:
    return re.sub(r"\s+", " ", name.upper().strip())

def parse_range(r: str) -> Optional[Tuple[float, float]]:
    m = re.search(r"(\d+\.?\d*)\s*-\s*(\d+\.?\d*)", r)
    if not m:
        return None
    return float(m.group(1)), float(m.group(2))

def status_from_range(val: float, ref: Optional[Tuple[float, float]]) -> Optional[str]:
    if not ref:
        return None
    lo, hi = ref
    if val < lo:
        return "low"
    if val > hi:
        return "high"
    return "in_range"

def canonical_key(raw_name: str) -> str:
    n = normalize(raw_name)
    return ALIASES.get(n, n)

def find_labs(text: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    p1 = re.compile(
        rf"""^(?P<name>[A-Za-z ][A-Za-z0-9 ]*)
             \s*[: ]\s*
             (?P<value>\d+\.?\d*)
             \s*(?P<units>{UNITS})?
             \s*(?:\((?P<ref>\d+\.?\d*\s*-\s*\d+\.?\d*)\))?
             \s*(?:\((?P<flag>H|L)\))?
             \s*$""",
        re.I | re.X,
    )

    p2 = re.compile(
        rf"""^(?P<name>[A-Za-z ][A-Za-z0-9 ]*)
             \s+(?P<value>\d+\.?\d*)
             \s+(?P<ref>\d+\.?\d*\s*-\s*\d+\.?\d*)
             \s*(?P<units>{UNITS})?
             \s*$""",
        re.I | re.X,
    )

    p3 = re.compile(
        rf"""^(?P<name>[A-Za-z ][A-Za-z0-9 ]*)
             \s+(?P<value>\d+\.?\d*)
             \s+(?P<flag>H|L)
             \s*(?P<units>{UNITS})?
             \s*(?P<ref>\d+\.?\d*\s*-\s*\d+\.?\d*)?
             \s*$""",
        re.I | re.X,
    )

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        m = p3.match(line) or p2.match(line) or p1.match(line)
        if not m:
            continue

        name = (m.group("name") or "").strip()
        key = canonical_key(name)

        value = float(m.group("value"))
        ref = m.groupdict().get("ref")
        flag = m.groupdict().get("flag")
        units = m.groupdict().get("units")

        ref_tuple = parse_range(ref) if ref else None

        # Apply default ranges when missing
        if ref_tuple is None and key in DEFAULT_RANGES:
            ref_tuple = DEFAULT_RANGES[key]
            if not ref:
                ref = f"{ref_tuple[0]}-{ref_tuple[1]}"

        # Prefer explicit flags if present; otherwise compute from range
        if flag:
            status = "high" if flag.upper() == "H" else "low"
        else:
            status = status_from_range(value, ref_tuple) if ref_tuple else None

        results.append(
            {
                "name": name,
                "value": value,
                "units": units,
                "reference_range": ref,
                "status": status,
                "panel": PANEL_MAP.get(key, "Other"),
                "explanation": LAB_INFO.get(key, "Lab test"),
            }
        )

    return results
