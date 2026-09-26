import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.rate_limit import limiter
from app.models.workspace import Workspace
from app.schemas.agent_run import RunIngestRequest, RunIngestResponse
from app.api.deps import get_workspace_from_ingestion_token
from app.services.ingest_service import ingest_agent_run

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/run", response_model=RunIngestResponse)
@limiter.limit("120/minute")
async def ingest_run(
    request: Request,
    payload: RunIngestRequest,
    workspace: Workspace = Depends(get_workspace_from_ingestion_token),
    db: Session = Depends(get_db),
):
    """
    Ingest a run trace pushed from an SDK or webhook (REQ-004).
    Authenticated via high-entropy per-workspace ingestion token.
    Idempotent when external_run_id is supplied.
    """
    # Extract raw body dictionary if available
    raw_body_dict = None
    try:
        body_json = await request.json()
        if isinstance(body_json, dict):
            raw_body_dict = body_json
    except Exception:
        pass

    run, is_duplicate = ingest_agent_run(
        db=db,
        workspace=workspace,
        payload=payload,
        raw_body_dict=raw_body_dict,
    )

    message = (
        f"Run {run.id} updated (idempotent duplicate)"
        if is_duplicate
        else f"Run {run.id} ingested successfully"
    )

    return RunIngestResponse(
        run_id=run.id,
        workspace_id=run.workspace_id,
        source=run.source,
        status=run.status,
        external_run_id=run.external_run_id,
        is_duplicate=is_duplicate,
        message=message,
    )
