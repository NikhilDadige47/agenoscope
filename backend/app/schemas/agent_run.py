from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class AgentRunBase(BaseModel):
    name: Optional[str] = None
    source: str = "langsmith"
    external_run_id: Optional[str] = None
    status: str = "unknown"
    error_message: Optional[str] = None
    latency_ms: Optional[float] = None
    total_tokens: Optional[int] = None
    raw_trace: Dict[str, Any] = {}


class AgentRunResponse(AgentRunBase):
    id: str
    workspace_id: str
    fetched_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentRunListResponse(BaseModel):
    runs: List[AgentRunResponse]
    total: int
    langsmith_connected: bool = False
    project: Optional[str] = None
