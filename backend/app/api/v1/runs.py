from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.errors import AppException
from app.models.user import User
from app.models.workspace import Workspace
from app.models.agent_run import AgentRun
from app.schemas.agent_run import AgentRunResponse
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/{run_id}", response_model=AgentRunResponse)
def get_run_by_id(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
    if not run:
        raise AppException(
            code="RUN_NOT_FOUND",
            message="Agent run not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    # Check tenant isolation
    workspace = db.query(Workspace).filter(Workspace.id == run.workspace_id).first()
    if not workspace or workspace.owner_user_id != current_user.id:
        raise AppException(
            code="FORBIDDEN",
            message="You do not have access to this run",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    return AgentRunResponse.model_validate(run)
