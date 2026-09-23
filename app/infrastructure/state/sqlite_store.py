"""
SQLite-backed persistent state store with WAL mode for crash-resilient job management.
"""

import os
import json
import sqlite3
from datetime import datetime
from threading import Lock
from typing import Dict, Any, List, Optional
from pathlib import Path

from app.config.settings import PROJECT_ROOT

DB_PATH = str(PROJECT_ROOT / "jobs_state.db")
_db_lock = Lock()


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for high concurrency and zero corruption on crash
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def init_db() -> None:
    with _db_lock:
        with get_db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    document_id TEXT,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    stage TEXT NOT NULL DEFAULT 'parsing',
                    units_done INTEGER DEFAULT 0,
                    units_total INTEGER DEFAULT 0,
                    units_failed INTEGER DEFAULT 0,
                    failure_reason TEXT,
                    output_dir TEXT,
                    options_json TEXT,
                    data_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_id ON jobs(document_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON jobs(status);")
            conn.commit()


# Initialize database table on import
init_db()


def save_job(job_id: str, data: Dict[str, Any]) -> None:
    """Inserts or updates a job record in SQLite atomically."""
    with _db_lock:
        now_iso = datetime.now().isoformat()
        with get_db_connection() as conn:
            # Fetch existing row to merge fields
            cur = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
            row = cur.fetchone()
            
            existing = dict(row) if row else {}
            existing_data = {}
            if existing.get("data_json"):
                try:
                    existing_data = json.loads(existing["data_json"])
                except Exception:
                    pass
            
            # Merge dictionary data
            merged_data = {**existing_data, **data}
            
            status = data.get("status", existing.get("status", "PENDING"))
            stage = data.get("stage", existing.get("stage", "parsing"))
            document_id = data.get("document_id", existing.get("document_id", ""))
            output_dir = data.get("output_dir", existing.get("output_dir", ""))
            failure_reason = data.get("failure_reason", existing.get("failure_reason"))
            units_done = data.get("units_done", existing.get("units_done", 0))
            units_total = data.get("units_total", existing.get("units_total", 0))
            units_failed = data.get("units_failed", existing.get("units_failed", 0))
            
            options_json = existing.get("options_json", "{}")
            if "options" in data:
                options_json = json.dumps(data["options"])
                
            created_at = existing.get("created_at", now_iso)
            updated_at = now_iso
            completed_at = existing.get("completed_at")
            if status in ("DONE", "FAILED"):
                completed_at = now_iso
                
            conn.execute("""
                INSERT INTO jobs (
                    job_id, document_id, status, stage, units_done, units_total, units_failed,
                    failure_reason, output_dir, options_json, data_json, created_at, updated_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    document_id = excluded.document_id,
                    status = excluded.status,
                    stage = excluded.stage,
                    units_done = excluded.units_done,
                    units_total = excluded.units_total,
                    units_failed = excluded.units_failed,
                    failure_reason = excluded.failure_reason,
                    output_dir = excluded.output_dir,
                    options_json = excluded.options_json,
                    data_json = excluded.data_json,
                    updated_at = excluded.updated_at,
                    completed_at = excluded.completed_at;
            """, (
                job_id, document_id, status, stage, units_done, units_total, units_failed,
                failure_reason, output_dir, options_json, json.dumps(merged_data),
                created_at, updated_at, completed_at
            ))
            conn.commit()


def get_job(job_id: str) -> Dict[str, Any]:
    """Retrieves full job state dictionary."""
    with _db_lock:
        with get_db_connection() as conn:
            cur = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
            row = cur.fetchone()
            if not row:
                return {}
            
            result = dict(row)
            if result.get("data_json"):
                try:
                    payload = json.loads(result["data_json"])
                    result.update(payload)
                except Exception:
                    pass
            if result.get("options_json"):
                try:
                    result["options"] = json.loads(result["options_json"])
                except Exception:
                    pass
            return result


def find_job_by_document(document_id: str) -> Optional[Dict[str, Any]]:
    with _db_lock:
        with get_db_connection() as conn:
            cur = conn.execute("SELECT job_id FROM jobs WHERE document_id = ? ORDER BY updated_at DESC LIMIT 1", (document_id,))
            row = cur.fetchone()
            if row:
                return get_job(row["job_id"])
            return None


def get_all_jobs(limit: int = 50) -> List[Dict[str, Any]]:
    """Returns list of recent jobs for UI history/resume."""
    with _db_lock:
        with get_db_connection() as conn:
            cur = conn.execute("SELECT * FROM jobs ORDER BY updated_at DESC LIMIT ?", (limit,))
            rows = cur.fetchall()
            jobs = []
            for r in rows:
                j = dict(r)
                if j.get("data_json"):
                    try:
                        payload = json.loads(j["data_json"])
                        j.update(payload)
                    except Exception:
                        pass
                jobs.append(j)
            return jobs
