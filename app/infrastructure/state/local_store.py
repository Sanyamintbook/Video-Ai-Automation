"""
State store module wrapping SQLite persistence for 100% crash durability.
"""

from typing import Dict, Any, Optional
from app.infrastructure.state.sqlite_store import (
    save_job,
    get_job,
    find_job_by_document,
    get_all_jobs,
    DB_PATH
)

STATE_FILE = DB_PATH

def get_job_state(job_id: str) -> Dict[str, Any]:
    return get_job(job_id)

def update_job_state(job_id: str, new_state: Dict[str, Any]) -> None:
    save_job(job_id, new_state)

def set_job_state(job_id: str, state: Dict[str, Any]) -> None:
    save_job(job_id, state)
