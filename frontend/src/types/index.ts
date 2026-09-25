export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface Workspace {
  id: string;
  owner_user_id: string;
  name: string;
  langsmith_project?: string | null;
  langsmith_connected?: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
  workspace: Workspace;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: any;
  };
}

export interface AgentRun {
  id: string;
  workspace_id: string;
  source: 'langsmith' | 'sdk';
  external_run_id?: string | null;
  name?: string | null;
  status: 'success' | 'error' | 'unknown';
  error_message?: string | null;
  latency_ms?: number | null;
  total_tokens?: number | null;
  raw_trace: Record<string, any>;
  fetched_at: string;
}

export interface LangSmithStatus {
  connected: boolean;
  project?: string | null;
  workspace_id: string;
  message?: string | null;
}

export interface LangSmithConnectPayload {
  langsmith_key: string;
  project: string;
}
