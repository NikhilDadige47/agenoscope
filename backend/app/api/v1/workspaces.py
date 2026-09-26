import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.errors import AppException
from app.core.encryption import encrypt_secret
from app.core.security import generate_ingestion_token, hash_token
from app.models.user import User
from app.models.workspace import Workspace
from app.models.agent_run import AgentRun
from app.schemas.workspace import WorkspaceResponse, IngestionTokenResponse, IngestionTokenStatus
from app.schemas.langsmith import LangSmithConnectRequest, LangSmithStatusResponse
from app.schemas.agent_run import AgentRunResponse
from app.api.deps import get_current_user, get_current_workspace
from app.services.langsmith_client import (
    langsmith_service,
    LangSmithAuthError,
    LangSmithProjectNotFoundError,
    LangSmithConnectionError,
)
from app.services.run_service import async_sync_workspace_runs

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/current", response_model=WorkspaceResponse)
def get_current_workspace_endpoint(
    workspace: Workspace = Depends(get_current_workspace),
):
    return WorkspaceResponse.model_validate(workspace)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace_by_id(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise AppException(
            code="WORKSPACE_NOT_FOUND",
            message="Workspace not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    # Enforce multi-tenant data isolation (REQ-012)
    if workspace.owner_user_id != current_user.id:
        raise AppException(
            code="FORBIDDEN",
            message="You do not have access to this workspace",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    return WorkspaceResponse.model_validate(workspace)


@router.put("/{workspace_id}/langsmith", response_model=LangSmithStatusResponse)
async def connect_langsmith(
    workspace_id: str,
    payload: LangSmithConnectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise AppException(
            code="WORKSPACE_NOT_FOUND",
            message="Workspace not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if workspace.owner_user_id != current_user.id:
        raise AppException(
            code="FORBIDDEN",
            message="You do not have access to this workspace",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    # Validate credentials live with LangSmith
    try:
        await langsmith_service.validate_credentials(
            api_key=payload.langsmith_key,
            project_name=payload.project,
        )
    except LangSmithAuthError:
        raise AppException(
            code="LANGSMITH_AUTH_FAILED",
            message="Invalid LangSmith API key or unauthorized project",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except LangSmithProjectNotFoundError as exc:
        raise AppException(
            code="LANGSMITH_PROJECT_NOT_FOUND",
            message=str(exc),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    except LangSmithConnectionError as exc:
        raise AppException(
            code="LANGSMITH_UNREACHABLE",
            message="Unable to reach LangSmith API. Please verify network or service status.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )
    except Exception as exc:
        raise AppException(
            code="LANGSMITH_VALIDATION_ERROR",
            message=f"LangSmith connection failed: {str(exc)}",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Encrypt secret at rest (NFR-001)
    workspace.langsmith_key_encrypted = encrypt_secret(payload.langsmith_key)
    workspace.langsmith_project = payload.project
    db.commit()
    db.refresh(workspace)

    # Trigger initial run sync
    try:
        await async_sync_workspace_runs(db, workspace, limit=50, fail_silently=True)
    except Exception as e:
        logger.warning("Initial run sync failed for workspace %s: %s", workspace.id, e)

    return LangSmithStatusResponse(
        connected=True,
        project=workspace.langsmith_project,
        workspace_id=workspace.id,
        message="LangSmith connected successfully",
    )


@router.get("/{workspace_id}/langsmith", response_model=LangSmithStatusResponse)
def get_langsmith_status(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise AppException(
            code="WORKSPACE_NOT_FOUND",
            message="Workspace not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if workspace.owner_user_id != current_user.id:
        raise AppException(
            code="FORBIDDEN",
            message="You do not have access to this workspace",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    return LangSmithStatusResponse(
        connected=workspace.langsmith_connected,
        project=workspace.langsmith_project,
        workspace_id=workspace.id,
        message="Connected" if workspace.langsmith_connected else "Not connected",
    )


@router.delete("/{workspace_id}/langsmith", response_model=LangSmithStatusResponse)
def disconnect_langsmith(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise AppException(
            code="WORKSPACE_NOT_FOUND",
            message="Workspace not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if workspace.owner_user_id != current_user.id:
        raise AppException(
            code="FORBIDDEN",
            message="You do not have access to this workspace",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    workspace.langsmith_project = None
    workspace.langsmith_key_encrypted = None
    db.commit()

    return LangSmithStatusResponse(
        connected=False,
        project=None,
        workspace_id=workspace.id,
        message="LangSmith disconnected",
    )


@router.get("/{workspace_id}/runs", response_model=List[AgentRunResponse])
async def list_workspace_runs(
    workspace_id: str,
    status_filter: Optional[str] = Query(None, alias="status"),
    sync: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise AppException(
            code="WORKSPACE_NOT_FOUND",
            message="Workspace not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if workspace.owner_user_id != current_user.id:
        raise AppException(
            code="FORBIDDEN",
            message="You do not have access to this workspace",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    # Sync live from LangSmith if connected
    if sync and workspace.langsmith_connected:
        try:
            await async_sync_workspace_runs(db, workspace, limit=50, fail_silently=True)
        except Exception as e:
            logger.warning("Sync failed in list_workspace_runs: %s", e)

    query = db.query(AgentRun).filter(AgentRun.workspace_id == workspace.id)
    if status_filter and status_filter.lower() != "all":
        query = query.filter(AgentRun.status == status_filter.lower())

    runs = query.order_by(AgentRun.fetched_at.desc()).all()
    return [AgentRunResponse.model_validate(r) for r in runs]


@router.post("/{workspace_id}/ingestion-token", response_model=IngestionTokenResponse)
def generate_or_rotate_ingestion_token(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate or rotate the workspace's SDK/webhook ingestion token (REQ-004, NFR-001).
    Stores only the SHA-256 hash in the database.
    Returns the raw token once.
    """
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise AppException(
            code="WORKSPACE_NOT_FOUND",
            message="Workspace not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if workspace.owner_user_id != current_user.id:
        raise AppException(
            code="FORBIDDEN",
            message="You do not have access to this workspace",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    raw_token = generate_ingestion_token()
    token_hash = hash_token(raw_token)

    workspace.ingestion_token_hash = token_hash
    db.commit()
    db.refresh(workspace)

    return IngestionTokenResponse(
        token=raw_token,
        workspace_id=workspace.id,
        message="Ingestion token generated successfully. Copy and store this token securely now; it will not be displayed again.",
    )


@router.get("/{workspace_id}/ingestion-token", response_model=IngestionTokenStatus)
def get_ingestion_token_status(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Check if the workspace has an active ingestion token configured (REQ-004).
    """
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise AppException(
            code="WORKSPACE_NOT_FOUND",
            message="Workspace not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if workspace.owner_user_id != current_user.id:
        raise AppException(
            code="FORBIDDEN",
            message="You do not have access to this workspace",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    return IngestionTokenStatus(
        has_token=bool(workspace.ingestion_token_hash),
        workspace_id=workspace.id,
    )


@router.delete("/{workspace_id}/ingestion-token")
def revoke_ingestion_token(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Revoke the workspace's ingestion token (REQ-004).
    """
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise AppException(
            code="WORKSPACE_NOT_FOUND",
            message="Workspace not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if workspace.owner_user_id != current_user.id:
        raise AppException(
            code="FORBIDDEN",
            message="You do not have access to this workspace",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    workspace.ingestion_token_hash = None
    db.commit()
    db.refresh(workspace)

    return {
        "message": "Ingestion token revoked successfully",
        "workspace_id": workspace.id,
        "has_token": False,
    }

