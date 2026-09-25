import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Float, Integer, JSON, Index
from sqlalchemy.orm import relationship
from app.db.session import Base


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(String(32), nullable=False, default="langsmith")  # 'langsmith' | 'sdk'
    external_run_id = Column(String(255), nullable=True, index=True)
    name = Column(String(255), nullable=True)
    status = Column(String(32), nullable=False, default="unknown")  # 'success' | 'error' | 'unknown'
    error_message = Column(Text, nullable=True)
    latency_ms = Column(Float, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    raw_trace = Column(JSON, nullable=False, default=dict)
    fetched_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    workspace = relationship("Workspace", back_populates="agent_runs")

    __table_args__ = (
        Index("ix_agent_runs_workspace_status", "workspace_id", "status"),
        Index("ix_agent_runs_workspace_external", "workspace_id", "external_run_id"),
    )
