from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from app.schemas.user import UserResponse
from app.schemas.workspace import WorkspaceResponse


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    workspace_name: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponse(TokenResponse):
    user: UserResponse
    workspace: WorkspaceResponse


class CurrentUserResponse(BaseModel):
    user: UserResponse
    workspace: WorkspaceResponse
