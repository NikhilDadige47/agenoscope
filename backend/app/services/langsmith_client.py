import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

DEFAULT_LANGSMITH_ENDPOINT = "https://api.smith.langchain.com"


class LangSmithClientError(Exception):
    """Base exception for LangSmith integration errors."""
    pass


class LangSmithAuthError(LangSmithClientError):
    """Raised when the LangSmith API key is invalid or unauthorized."""
    pass


class LangSmithProjectNotFoundError(LangSmithClientError):
    """Raised when the specified project is not found."""
    pass


class LangSmithConnectionError(LangSmithClientError):
    """Raised when LangSmith cannot be reached due to network/server failure."""
    pass


class LangSmithService:
    def __init__(self, endpoint: str = DEFAULT_LANGSMITH_ENDPOINT, timeout_seconds: float = 10.0):
        self.endpoint = endpoint.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _get_headers(self, api_key: str) -> Dict[str, str]:
        return {
            "x-api-key": api_key,
            "Accept": "application/json",
            "User-Agent": "agenoscope/0.1.0",
        }

    async def validate_credentials(self, api_key: str, project_name: str) -> bool:
        """
        Validates the API key and verifies that the project exists or can be queried.
        Raises LangSmithAuthError, LangSmithProjectNotFoundError, or LangSmithConnectionError.
        """
        if not api_key or not api_key.strip():
            raise LangSmithAuthError("LangSmith API key is required")
        if not project_name or not project_name.strip():
            raise LangSmithProjectNotFoundError("Project name is required")

        headers = self._get_headers(api_key.strip())
        url = f"{self.endpoint}/api/v1/sessions"
        params = {"name": project_name.strip()}

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url, headers=headers, params=params)

                if response.status_code in (401, 403):
                    logger.warning("LangSmith authentication failed for project %s", project_name)
                    raise LangSmithAuthError("Invalid LangSmith API key or unauthorized access")

                if response.status_code == 404:
                    raise LangSmithProjectNotFoundError(f"Project '{project_name}' not found on LangSmith")

                if response.status_code >= 500 or response.status_code in (502, 503, 504):
                    raise LangSmithConnectionError("LangSmith service is currently unreachable")

                if response.status_code >= 400:
                    raise LangSmithClientError(f"LangSmith API returned error: {response.text}")

                # Check if sessions returned contains the project
                data = response.json()
                if isinstance(data, list) and len(data) == 0:
                    # Some versions return empty list if project does not exist
                    # Let's also check /runs with limit=1 to be sure
                    runs_url = f"{self.endpoint}/api/v1/runs"
                    runs_res = await client.get(runs_url, headers=headers, params={"project_name": project_name, "limit": 1})
                    if runs_res.status_code in (401, 403):
                        raise LangSmithAuthError("Invalid LangSmith API key")
                    if runs_res.status_code == 404:
                        raise LangSmithProjectNotFoundError(f"Project '{project_name}' not found on LangSmith")

                return True

        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
            logger.error("Network error connecting to LangSmith: %s", exc)
            raise LangSmithConnectionError("Failed to connect to LangSmith API: network unreachable or timed out") from exc
        except (LangSmithAuthError, LangSmithProjectNotFoundError, LangSmithConnectionError, LangSmithClientError):
            raise
        except Exception as exc:
            logger.error("Unexpected error validating LangSmith credentials: %s", exc)
            raise LangSmithConnectionError(f"Failed to communicate with LangSmith: {str(exc)}") from exc

    async def fetch_runs(
        self, api_key: str, project_name: str, limit: int = 50, error_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Fetches runs for a given project from LangSmith and normalizes them into internal schema.
        """
        headers = self._get_headers(api_key.strip())
        url = f"{self.endpoint}/api/v1/runs"
        params: Dict[str, Any] = {
            "project_name": project_name.strip(),
            "limit": limit,
        }
        if error_only:
            params["error"] = "true"

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url, headers=headers, params=params)

                if response.status_code in (401, 403):
                    raise LangSmithAuthError("Invalid LangSmith API key or unauthorized access")

                if response.status_code == 404:
                    raise LangSmithProjectNotFoundError(f"Project '{project_name}' not found")

                if response.status_code >= 500:
                    raise LangSmithConnectionError("LangSmith service is currently unreachable")

                if not response.is_success:
                    raise LangSmithClientError(f"LangSmith fetch failed with status {response.status_code}")

                raw_runs = response.json()
                if not isinstance(raw_runs, list):
                    raw_runs = raw_runs.get("runs", []) if isinstance(raw_runs, dict) else []

                return [self.normalize_run(run) for run in raw_runs]

        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
            logger.error("Network error fetching runs from LangSmith: %s", exc)
            raise LangSmithConnectionError("Failed to fetch runs: LangSmith API unreachable or timed out") from exc
        except (LangSmithAuthError, LangSmithProjectNotFoundError, LangSmithConnectionError, LangSmithClientError):
            raise
        except Exception as exc:
            logger.error("Unexpected error fetching LangSmith runs: %s", exc)
            raise LangSmithConnectionError(f"Unexpected error fetching LangSmith runs: {str(exc)}") from exc

    @staticmethod
    def normalize_run(raw_run: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes a LangSmith run dictionary into the internal AgentRun structure.
        """
        run_id = str(raw_run.get("id") or raw_run.get("run_id") or "")
        name = raw_run.get("name") or "AgentRun"
        raw_error = raw_run.get("error")

        if raw_error:
            status = "error"
            error_message = str(raw_error)
        elif raw_run.get("status") == "error":
            status = "error"
            error_message = raw_run.get("error_message") or "Unknown execution error"
        elif raw_run.get("status") in ("success", "completed") or (not raw_error and raw_run.get("end_time")):
            status = "success"
            error_message = None
        else:
            status = "unknown"
            error_message = None

        latency_ms: Optional[float] = None
        start_time_raw = raw_run.get("start_time")
        end_time_raw = raw_run.get("end_time")
        if start_time_raw and end_time_raw:
            try:
                start_dt = datetime.fromisoformat(str(start_time_raw).replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(str(end_time_raw).replace("Z", "+00:00"))
                latency_ms = round((end_dt - start_dt).total_seconds() * 1000.0, 2)
            except Exception:
                latency_ms = None
        elif "latency" in raw_run:
            try:
                latency_ms = float(raw_run["latency"]) * 1000.0
            except Exception:
                latency_ms = None

        total_tokens: Optional[int] = None
        if "total_tokens" in raw_run and raw_run["total_tokens"] is not None:
            try:
                total_tokens = int(raw_run["total_tokens"])
            except Exception:
                pass
        elif isinstance(raw_run.get("extra"), dict):
            extra = raw_run["extra"]
            token_usage = extra.get("token_usage") or extra.get("total_tokens")
            if isinstance(token_usage, dict):
                total_tokens = token_usage.get("total_tokens")
            elif isinstance(token_usage, int):
                total_tokens = token_usage

        return {
            "external_run_id": run_id,
            "name": name,
            "source": "langsmith",
            "status": status,
            "error_message": error_message,
            "latency_ms": latency_ms,
            "total_tokens": total_tokens,
            "raw_trace": raw_run,
        }


# Global default instance
langsmith_service = LangSmithService()
