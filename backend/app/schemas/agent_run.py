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


class RunIngestRequest(BaseModel):
    name: Optional[str] = "agent_run"
    external_run_id: Optional[str] = None
    status: Optional[str] = "unknown"
    error_message: Optional[str] = None
    latency_ms: Optional[float] = None
    total_tokens: Optional[int] = None
    raw_trace: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="allow")


class RunIngestResponse(BaseModel):
    run_id: str
    workspace_id: str
    source: str = "sdk"
    status: str
    external_run_id: Optional[str] = None
    is_duplicate: bool = False
    message: str

