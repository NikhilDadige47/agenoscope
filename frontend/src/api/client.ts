import { AuthResponse, ApiError } from '../types';

const API_BASE = '/api/v1';

export class ApiException extends Error {
  code: string;
  details?: any;

  constructor(code: string, message: string, details?: any) {
    super(message);
    this.name = 'ApiException';
    this.code = code;
    this.details = details;
  }
}

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem('access_token');
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorData: ApiError;
    try {
      errorData = await response.json();
    } catch {
      throw new ApiException(
        'HTTP_ERROR',
        `Request failed with status ${response.status}: ${response.statusText}`
      );
    }
    const code = errorData?.error?.code || 'UNKNOWN_ERROR';
    const message = errorData?.error?.message || 'An unexpected error occurred';
    throw new ApiException(code, message, errorData?.error?.details);
  }

  return response.json();
}

export const api = {
  async signup(email: string, password: string, workspaceName?: string): Promise<AuthResponse> {
    const res = await fetch(`${API_BASE}/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, workspace_name: workspaceName }),
    });
    return handleResponse<AuthResponse>(res);
  },

  async login(email: string, password: string): Promise<AuthResponse> {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    return handleResponse<AuthResponse>(res);
  },

  async getMe(): Promise<{ user: any; workspace: any }> {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse<{ user: any; workspace: any }>(res);
  },

  async getCurrentWorkspace(): Promise<any> {
    const res = await fetch(`${API_BASE}/workspaces/current`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse<any>(res);
  },

  async connectLangSmith(
    workspaceId: string,
    payload: { langsmith_key: string; project: string }
  ): Promise<any> {
    const res = await fetch(`${API_BASE}/workspaces/${workspaceId}/langsmith`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return handleResponse<any>(res);
  },

  async getLangSmithStatus(workspaceId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/workspaces/${workspaceId}/langsmith`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse<any>(res);
  },

  async disconnectLangSmith(workspaceId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/workspaces/${workspaceId}/langsmith`, {
      method: 'DELETE',
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse<any>(res);
  },

  async getRuns(
    workspaceId: string,
    options?: { status?: string; sync?: boolean }
  ): Promise<any[]> {
    const params = new URLSearchParams();
    if (options?.status && options.status !== 'all') {
      params.append('status', options.status);
    }
    if (options?.sync !== undefined) {
      params.append('sync', String(options.sync));
    }
    const queryString = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`${API_BASE}/workspaces/${workspaceId}/runs${queryString}`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse<any[]>(res);
  },

  async getRun(runId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/runs/${runId}`, {
      headers: {
        ...getAuthHeader(),
      },
    });
    return handleResponse<any>(res);
  },
};
