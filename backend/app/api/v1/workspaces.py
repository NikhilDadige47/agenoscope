from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.errors import AppException
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.workspace import WorkspaceResponse
from app.api.deps import get_current_user, get_current_workspace

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
