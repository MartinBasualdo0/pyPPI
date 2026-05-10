import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

DB_PATH = Path(__file__).parent / "captured_endpoints.db"


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS endpoints (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                url              TEXT    NOT NULL,
                path             TEXT    NOT NULL,
                method           TEXT    NOT NULL,
                request_headers  TEXT,
                request_body     TEXT,
                response_status  INTEGER,
                response_body    TEXT,
                captured_at      DATETIME NOT NULL,
                body_hash        TEXT    NOT NULL UNIQUE,
                relevance_score  INTEGER,
                relevance_reason TEXT,
                coverage_status  TEXT,
                coverage_notes   TEXT
            )
        """)
        conn.commit()


def _make_hash(url: str, method: str, request_body: str | None) -> str:
    key = f"{method}:{url}:{request_body or ''}"
    return hashlib.sha256(key.encode()).hexdigest()


def _extract_path(url: str) -> str:
    try:
        return urlparse(url).path
    except Exception:
        return url.split("?")[0]


def save_endpoint(data: dict) -> bool:
    """Insert endpoint into DB. Returns True if new, False if duplicate."""
    body_hash = _make_hash(data["url"], data["method"], data.get("request_body"))
    path = _extract_path(data["url"])

    try:
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO endpoints
                    (url, path, method, request_headers, request_body,
                     response_status, response_body, captured_at, body_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["url"],
                    path,
                    data["method"],
                    data.get("request_headers"),
                    data.get("request_body"),
                    data.get("response_status"),
                    data.get("response_body"),
                    datetime.now().isoformat(),
                    body_hash,
                ),
            )
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False


def get_unanalyzed() -> list[dict]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM endpoints WHERE relevance_score IS NULL ORDER BY id"
        ).fetchall()
        return [dict(row) for row in rows]


def update_analysis(
    endpoint_id: int,
    relevance_score: int,
    relevance_reason: str,
    coverage_status: str,
    coverage_notes: str,
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            UPDATE endpoints
            SET relevance_score = ?, relevance_reason = ?,
                coverage_status = ?, coverage_notes = ?
            WHERE id = ?
            """,
            (relevance_score, relevance_reason, coverage_status, coverage_notes, endpoint_id),
        )
        conn.commit()


def get_all() -> list[dict]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM endpoints ORDER BY relevance_score DESC NULLS LAST, id"
        ).fetchall()
        return [dict(row) for row in rows]


def get_stats() -> dict:
    with _connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM endpoints").fetchone()[0]
        analyzed = conn.execute(
            "SELECT COUNT(*) FROM endpoints WHERE relevance_score IS NOT NULL"
        ).fetchone()[0]
        new_relevant = conn.execute(
            "SELECT COUNT(*) FROM endpoints WHERE relevance_score >= 1 AND coverage_status = 'NEW'"
        ).fetchone()[0]
        return {"total": total, "analyzed": analyzed, "new_relevant": new_relevant}
