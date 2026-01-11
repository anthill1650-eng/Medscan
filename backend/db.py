from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Database file lives next to this db.py file
DB_PATH = Path(__file__).resolve().parent / "mediscan.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                filename TEXT,
                content_type TEXT,
                ocr_text TEXT,
                result_json TEXT NOT NULL
            )
            """
        )


def save_scan(
    *,
    filename: Optional[str],
    content_type: Optional[str],
    ocr_text: str,
    result: Dict[str, Any],
) -> int:
    created_at = datetime.now(timezone.utc).isoformat()
    payload = json.dumps(result, ensure_ascii=False)

    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO scans (
                created_at,
                filename,
                content_type,
                ocr_text,
                result_json
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (created_at, filename, content_type, ocr_text, payload),
        )
        return int(cur.lastrowid)


def list_scans(limit: int = 50) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, filename, result_json
            FROM scans
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    results: List[Dict[str, Any]] = []
    for r in rows:
        try:
            parsed = json.loads(r["result_json"])
        except Exception:
            parsed = {}

        results.append(
            {
                "id": int(r["id"]),
                "created_at": r["created_at"],
                "filename": r["filename"],
                "count": parsed.get("count"),
                "overall_summary": parsed.get("overall_summary"),
            }
        )

    return results


def get_scan(scan_id: int) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT
                id,
                created_at,
                filename,
                content_type,
                ocr_text,
                result_json
            FROM scans
            WHERE id = ?
            """,
            (scan_id,),
        ).fetchone()

    if not row:
        return None

    try:
        parsed = json.loads(row["result_json"])
    except Exception:
        parsed = {}

    return {
        "id": int(row["id"]),
        "created_at": row["created_at"],
        "filename": row["filename"],
        "content_type": row["content_type"],
        "ocr_text": row["ocr_text"] or "",
        "ocr_text_preview": (row["ocr_text"] or "")[:800],
        **parsed,
    }
