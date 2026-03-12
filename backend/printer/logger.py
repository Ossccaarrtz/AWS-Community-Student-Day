"""
Structured JSON logging for print jobs.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import JOB_LOG_FILE
from .models import LabelSpec


def log_job(
    job_id: str,
    action: str,
    selected_printer: Optional[str],
    chosen_method: str,
    label: Optional[LabelSpec],
    transport: str,
    result: str,
    warnings: list[str] | None = None,
    error_class: str | None = None,
) -> None:
    """
    Append a structured JSON log entry for a print job.

    Log file: ./print_jobs.log (one JSON object per line).
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "job_id": job_id,
        "action": action,
        "selected_printer": selected_printer,
        "chosen_method": chosen_method,
        "label_size": (
            f"{label.width_in}x{label.height_in}in"
            if label else "unknown"
        ),
        "copies": label.copies if label else 0,
        "transport": transport,
        "result": result,
        "warnings": warnings or [],
    }

    if error_class:
        entry["error_class"] = error_class

    log_path = Path(JOB_LOG_FILE)
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        # If we can't write the log, don't crash the print job
        pass


def read_recent_jobs(count: int = 20) -> list[dict]:
    """Read the most recent N job log entries."""
    log_path = Path(JOB_LOG_FILE)
    if not log_path.exists():
        return []

    lines: list[str] = []
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return []

    entries = []
    for line in lines[-count:]:
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries
