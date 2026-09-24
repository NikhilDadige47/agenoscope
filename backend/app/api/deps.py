from typing import Tuple
from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import decode_token
from app.core.errors import AppException
from app.models.user import User
from app.models.workspace import Workspace

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise AppException(
            code="UNAUTHORIZED",
            message="Authentication credentials were not provided",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise AppException(
                code="INVALID_TOKEN",
                message="Invalid token type",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        user_id = payload.get("sub")
        if not user_id:
            raise AppException(
                code="INVALID_TOKEN",
                message="Token subject missing",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
    except Exception:
        raise AppException(
            code="INVALID_TOKEN",
            message="Could not validate credentials",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppException(
            code="USER_NOT_FOUND",
            message="User associated with this token does not exist",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    return user


def get_current_workspace(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Workspace:
    workspace = db.query(Workspace).filter(Workspace.owner_user_id == current_user.id).first()
    if not workspace:
        raise AppException(
            code="WORKSPACE_NOT_FOUND",
            message="No workspace found for current user",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return workspace


def get_current_active_user_and_workspace(
    current_user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
) -> Tuple[User, Workspace]:
    return current_user, workspace
