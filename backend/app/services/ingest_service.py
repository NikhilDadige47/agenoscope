import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from sqlalchemy.orm import Session

from app.core.errors import AppException
from app.models.agent_run import AgentRun
from app.models.workspace import Workspace
from app.schemas.agent_run import RunIngestRequest

logger = logging.getLogger(__name__)

# Max payload size: 5MB to prevent resource exhaustion / DoS (NFR-001)
MAX_PAYLOAD_SIZE_BYTES = 5 * 1024 * 1024


def normalize_status(status_val: Optional[str], error_message: Optional[str] = None) -> str:
    """
    Normalizes status string to one of ('success', 'error', 'unknown').
    If status is omitted or unknown but error_message is present, infers 'error'.
    """
    if not status_val or str(status_val).lower().strip() in ("unknown", ""):
        return "error" if error_message else "unknown"
    
    s = str(status_val).lower().strip()
    if s in ("error", "failed", "failure", "err"):
        return "error"
    elif s in ("success", "ok", "completed", "passed"):
        return "success"
    return "error" if error_message else "unknown"


def ingest_agent_run(
    db: Session,
    workspace: Workspace,
    payload: RunIngestRequest,
    raw_body_dict: Optional[Dict[str, Any]] = None,
) -> Tuple[AgentRun, bool]:
    """
    Ingests an agent run trace via SDK/webhook (REQ-004, NFR-007).
    Returns (AgentRun, is_duplicate).
    Idempotent on (workspace_id, external_run_id).
    """
    # Determine the raw_trace dict
    if payload.raw_trace is not None and isinstance(payload.raw_trace, dict):
        trace_data = payload.raw_trace
    elif raw_body_dict is not None and isinstance(raw_body_dict, dict):
        trace_data = raw_body_dict
    else:
        trace_data = payload.model_dump(exclude_unset=True)

    # Check payload size (in bytes as JSON string)
    try:
        dumped_len = len(json.dumps(trace_data).encode("utf-8"))
        if dumped_len > MAX_PAYLOAD_SIZE_BYTES:
            raise AppException(
                code="PAYLOAD_TOO_LARGE",
                message=f"Trace payload size ({dumped_len} bytes) exceeds maximum limit of {MAX_PAYLOAD_SIZE_BYTES} bytes (5MB)",
                status_code=413,
            )
    except (TypeError, ValueError):
        pass

    normalized_status = normalize_status(payload.status, payload.error_message)
    now = datetime.now(timezone.utc)

    # Check for duplicate external_run_id within this workspace (Idempotent ingestion)
    is_duplicate = False
    existing_run: Optional[AgentRun] = None
    if payload.external_run_id:
        existing_run = (
            db.query(AgentRun)
            .filter(
                AgentRun.workspace_id == workspace.id,
                AgentRun.external_run_id == str(payload.external_run_id),
            )
            .first()
        )

    if existing_run:
        # Idempotently update existing record
        existing_run.name = payload.name or existing_run.name
        existing_run.status = normalized_status
        existing_run.error_message = payload.error_message or existing_run.error_message
        existing_run.latency_ms = payload.latency_ms if payload.latency_ms is not None else existing_run.latency_ms
        existing_run.total_tokens = payload.total_tokens if payload.total_tokens is not None else existing_run.total_tokens
        existing_run.raw_trace = trace_data
        existing_run.fetched_at = now
        db.commit()
        db.refresh(existing_run)
        logger.info(
            "Idempotently updated agent run %s for workspace %s (external_id=%s)",
            existing_run.id,
            workspace.id,
            payload.external_run_id,
        )
        return existing_run, True

    # Otherwise create new record
    new_run = AgentRun(
        workspace_id=workspace.id,
        source="sdk",
        external_run_id=str(payload.external_run_id) if payload.external_run_id else None,
        name=payload.name or "AgentRun",
        status=normalized_status,
        error_message=payload.error_message,
        latency_ms=payload.latency_ms,
        total_tokens=payload.total_tokens,
        raw_trace=trace_data,
        fetched_at=now,
    )
    db.add(new_run)
    db.commit()
    db.refresh(new_run)

    logger.info(
        "Ingested new agent run %s for workspace %s via SDK/webhook (source=sdk)",
        new_run.id,
        workspace.id,
    )
    return new_run, False
