import logging
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.encryption import decrypt_secret
from app.core.errors import AppException
from app.models.workspace import Workspace
from app.models.agent_run import AgentRun
from app.services.langsmith_client import (
    langsmith_service,
    LangSmithAuthError,
    LangSmithConnectionError,
    LangSmithProjectNotFoundError,
    LangSmithClientError,
)

logger = logging.getLogger(__name__)


def sync_workspace_runs(
    db: Session,
    workspace: Workspace,
    limit: int = 50,
    fail_silently: bool = False,
) -> List[AgentRun]:
    """
    Syncs recent runs from LangSmith for the given workspace into agent_runs table.
    Upserts runs by (workspace_id, external_run_id).
    """
    if not workspace.langsmith_key_encrypted or not workspace.langsmith_project:
        return []

    try:
        api_key = decrypt_secret(workspace.langsmith_key_encrypted)
    except Exception as exc:
        logger.error("Failed to decrypt LangSmith key for workspace %s: %s", workspace.id, exc)
        if fail_silently:
            return []
        raise AppException(
            code="DECRYPTION_FAILED",
            message="Failed to decrypt stored credentials",
            status_code=500,
        )

    try:
        normalized_runs = []
        # Run fetch
        import asyncio
        # If in an async context or event loop, handle fetch
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # In FastAPI async endpoint or test loop
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                normalized_runs = loop.run_until_complete(
                    langsmith_service.fetch_runs(
                        api_key=api_key,
                        project_name=workspace.langsmith_project,
                        limit=limit,
                    )
                )
        else:
            normalized_runs = asyncio.run(
                langsmith_service.fetch_runs(
                    api_key=api_key,
                    project_name=workspace.langsmith_project,
                    limit=limit,
                )
            )

    except LangSmithAuthError as exc:
        logger.warning("LangSmith auth failed during sync: %s", exc)
        if fail_silently:
            return []
        raise AppException(
            code="LANGSMITH_AUTH_FAILED",
            message="LangSmith API key is invalid or revoked",
            status_code=400,
        )
    except LangSmithProjectNotFoundError as exc:
        logger.warning("LangSmith project not found during sync: %s", exc)
        if fail_silently:
            return []
        raise AppException(
            code="LANGSMITH_PROJECT_NOT_FOUND",
            message=str(exc),
            status_code=404,
        )
    except LangSmithConnectionError as exc:
        logger.warning("LangSmith unreachable during sync: %s", exc)
        if fail_silently:
            # Fall back to existing cached runs in DB
            return []
        raise AppException(
            code="LANGSMITH_UNREACHABLE",
            message=str(exc),
            status_code=502,
        )
    except Exception as exc:
        logger.error("Unexpected error during LangSmith sync: %s", exc)
        if fail_silently:
            return []
        raise AppException(
            code="LANGSMITH_SYNC_ERROR",
            message=f"Error syncing runs from LangSmith: {str(exc)}",
            status_code=502,
        )

    # Upsert into agent_runs
    synced_records = []
    now = datetime.now(timezone.utc)
    for item in normalized_runs:
        external_id = item.get("external_run_id")
        existing_run = None
        if external_id:
            existing_run = (
                db.query(AgentRun)
                .filter(
                    AgentRun.workspace_id == workspace.id,
                    AgentRun.external_run_id == external_id,
                )
                .first()
            )

        if existing_run:
            existing_run.name = item.get("name")
            existing_run.status = item.get("status") or "unknown"
            existing_run.error_message = item.get("error_message")
            existing_run.latency_ms = item.get("latency_ms")
            existing_run.total_tokens = item.get("total_tokens")
            existing_run.raw_trace = item.get("raw_trace") or {}
            existing_run.fetched_at = now
            synced_records.append(existing_run)
        else:
            new_run = AgentRun(
                workspace_id=workspace.id,
                source="langsmith",
                external_run_id=external_id,
                name=item.get("name"),
                status=item.get("status") or "unknown",
                error_message=item.get("error_message"),
                latency_ms=item.get("latency_ms"),
                total_tokens=item.get("total_tokens"),
                raw_trace=item.get("raw_trace") or {},
                fetched_at=now,
            )
            db.add(new_run)
            synced_records.append(new_run)

    db.commit()
    return synced_records


async def async_sync_workspace_runs(
    db: Session,
    workspace: Workspace,
    limit: int = 50,
    fail_silently: bool = False,
) -> List[AgentRun]:
    """
    Async version for direct use in FastAPI async endpoints.
    """
    if not workspace.langsmith_key_encrypted or not workspace.langsmith_project:
        return []

    try:
        api_key = decrypt_secret(workspace.langsmith_key_encrypted)
    except Exception as exc:
        logger.error("Failed to decrypt LangSmith key: %s", exc)
        if fail_silently:
            return []
        raise AppException(
            code="DECRYPTION_FAILED",
            message="Failed to decrypt stored credentials",
            status_code=500,
        )

    try:
        normalized_runs = await langsmith_service.fetch_runs(
            api_key=api_key,
            project_name=workspace.langsmith_project,
            limit=limit,
        )
    except LangSmithAuthError as exc:
        if fail_silently:
            return []
        raise AppException(
            code="LANGSMITH_AUTH_FAILED",
            message="LangSmith API key is invalid or revoked",
            status_code=400,
        )
    except LangSmithProjectNotFoundError as exc:
        if fail_silently:
            return []
        raise AppException(
            code="LANGSMITH_PROJECT_NOT_FOUND",
            message=str(exc),
            status_code=404,
        )
    except LangSmithConnectionError as exc:
        if fail_silently:
            return []
        raise AppException(
            code="LANGSMITH_UNREACHABLE",
            message=str(exc),
            status_code=502,
        )
    except Exception as exc:
        if fail_silently:
            return []
        raise AppException(
            code="LANGSMITH_SYNC_ERROR",
            message=f"Error syncing runs from LangSmith: {str(exc)}",
            status_code=502,
        )

    synced_records = []
    now = datetime.now(timezone.utc)
    for item in normalized_runs:
        external_id = item.get("external_run_id")
        existing_run = None
        if external_id:
            existing_run = (
                db.query(AgentRun)
                .filter(
                    AgentRun.workspace_id == workspace.id,
                    AgentRun.external_run_id == external_id,
                )
                .first()
            )

        if existing_run:
            existing_run.name = item.get("name")
            existing_run.status = item.get("status") or "unknown"
            existing_run.error_message = item.get("error_message")
            existing_run.latency_ms = item.get("latency_ms")
            existing_run.total_tokens = item.get("total_tokens")
            existing_run.raw_trace = item.get("raw_trace") or {}
            existing_run.fetched_at = now
            synced_records.append(existing_run)
        else:
            new_run = AgentRun(
                workspace_id=workspace.id,
                source="langsmith",
                external_run_id=external_id,
                name=item.get("name"),
                status=item.get("status") or "unknown",
                error_message=item.get("error_message"),
                latency_ms=item.get("latency_ms"),
                total_tokens=item.get("total_tokens"),
                raw_trace=item.get("raw_trace") or {},
                fetched_at=now,
            )
            db.add(new_run)
            synced_records.append(new_run)

    db.commit()
    return synced_records
