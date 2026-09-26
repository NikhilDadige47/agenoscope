import secrets
from typing import Tuple
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.errors import AppException
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.auth import (
    SignupRequest,
    LoginRequest,
    AuthResponse,
    CurrentUserResponse,
    TokenResponse,
)
from app.schemas.user import UserResponse
from app.schemas.workspace import WorkspaceResponse
from app.api.deps import get_current_active_user_and_workspace

router = APIRouter()


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    email_clean = payload.email.strip().lower()
    existing_user = db.query(User).filter(User.email == email_clean).first()
    if existing_user:
        raise AppException(
            code="EMAIL_ALREADY_EXISTS",
            message="A user with this email already exists",
            status_code=status.HTTP_409_CONFLICT,
        )

    # Create user
    password_hash = get_password_hash(payload.password)
    user = User(
        email=email_clean,
        password_hash=password_hash,
    )
    db.add(user)
    db.flush()

    # Automatically create default workspace for user
    default_ws_name = (
        payload.workspace_name.strip()
        if payload.workspace_name and payload.workspace_name.strip()
        else f"{email_clean.split('@')[0]}'s Workspace"
    )
    workspace = Workspace(
        owner_user_id=user.id,
        name=default_ws_name,
        ingestion_token_hash=None,
    )
    db.add(workspace)
    db.commit()
    db.refresh(user)
    db.refresh(workspace)

    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
        workspace=WorkspaceResponse.model_validate(workspace),
    )


@router.post("/login", response_model=AuthResponse)
@limiter.limit(settings.LOGIN_RATE_LIMIT)
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    email_clean = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email_clean).first()
    
    if not user or not verify_password(payload.password, user.password_hash):
        raise AppException(
            code="INVALID_CREDENTIALS",
            message="Invalid email or password",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    workspace = db.query(Workspace).filter(Workspace.owner_user_id == user.id).first()
    if not workspace:
        # Self-healing fallback if workspace somehow missing
        workspace = Workspace(
            owner_user_id=user.id,
            name=f"{email_clean.split('@')[0]}'s Workspace",
            ingestion_token_hash=None,
        )
        db.add(workspace)
        db.commit()
        db.refresh(workspace)

    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
        workspace=WorkspaceResponse.model_validate(workspace),
    )


@router.get("/me", response_model=CurrentUserResponse)
def get_me(current_data: Tuple[User, Workspace] = Depends(get_current_active_user_and_workspace)):
    user, workspace = current_data
    return CurrentUserResponse(
        user=UserResponse.model_validate(user),
        workspace=WorkspaceResponse.model_validate(workspace),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(request: Request, refresh_token: str, db: Session = Depends(get_db)):
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise AppException(
                code="INVALID_TOKEN",
                message="Token is not a refresh token",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        user_id = payload.get("sub")
    except Exception:
        raise AppException(
            code="INVALID_TOKEN",
            message="Invalid or expired refresh token",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppException(
            code="USER_NOT_FOUND",
            message="User does not exist",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    new_access_token = create_access_token(subject=user.id)
    new_refresh_token = create_refresh_token(subject=user.id)
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )
