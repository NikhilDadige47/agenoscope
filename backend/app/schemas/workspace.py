from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class WorkspaceBase(BaseModel):
    name: str


class WorkspaceResponse(WorkspaceBase):
    id: str
    owner_user_id: str
    langsmith_project: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
