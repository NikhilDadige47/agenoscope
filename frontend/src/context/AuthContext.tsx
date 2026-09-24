import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, Workspace, AuthResponse } from '../types';
import { api } from '../api/client';

interface AuthContextType {
  user: User | null;
  workspace: Workspace | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, workspaceName?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('access_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const saveAuthSession = (authData: AuthResponse) => {
    localStorage.setItem('access_token', authData.access_token);
    localStorage.setItem('refresh_token', authData.refresh_token);
    setToken(authData.access_token);
    setUser(authData.user);
    setWorkspace(authData.workspace);
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setToken(null);
    setUser(null);
    setWorkspace(null);
  };

  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem('access_token');
      if (storedToken) {
        try {
          const data = await api.getMe();
          setUser(data.user);
          setWorkspace(data.workspace);
        } catch {
          // Token invalid or expired
          logout();
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = async (email: string, password: string) => {
    const data = await api.login(email, password);
    saveAuthSession(data);
  };

  const signup = async (email: string, password: string, workspaceName?: string) => {
    const data = await api.signup(email, password, workspaceName);
    saveAuthSession(data);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        workspace,
        token,
        isAuthenticated: !!user && !!token,
        isLoading,
        login,
        signup,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
