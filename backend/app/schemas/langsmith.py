from typing import Optional
from pydantic import BaseModel, Field


class LangSmithConnectRequest(BaseModel):
    langsmith_key: str = Field(..., min_length=10, max_length=255, description="LangSmith API Key")
    project: str = Field(..., min_length=1, max_length=255, description="LangSmith Project Name")


class LangSmithStatusResponse(BaseModel):
    connected: bool
    project: Optional[str] = None
    workspace_id: str
    message: Optional[str] = None
