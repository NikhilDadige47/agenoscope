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
