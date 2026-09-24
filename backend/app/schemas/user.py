from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict, Field


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")


class UserResponse(UserBase):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
