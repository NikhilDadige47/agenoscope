import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    owner_user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    langsmith_project = Column(String(255), nullable=True)
    langsmith_key_encrypted = Column(String(1024), nullable=True)
    ingestion_token_hash = Column(String(255), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    owner = relationship("User", back_populates="workspaces")
