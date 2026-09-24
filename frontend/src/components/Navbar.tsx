import React from 'react';
import { useAuth } from '../context/AuthContext';
import { LogOut, Layers, Activity } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, workspace, logout } = useAuth();

  return (
    <header className="navbar">
      <div className="navbar-brand">
        <div className="navbar-logo-icon">
          <Activity size={18} />
        </div>
        <span>agenoscope</span>
      </div>

      <div className="navbar-right">
        {workspace && (
          <div className="workspace-badge" id="current-workspace-badge">
            <Layers size={14} />
            <span>{workspace.name}</span>
          </div>
        )}
        {user && (
          <div className="user-email" id="current-user-email">
            <span>{user.email}</span>
          </div>
        )}
        <button
          id="logout-button"
          onClick={logout}
          className="btn-secondary"
          title="Sign out of account"
        >
          <LogOut size={14} />
          <span>Sign Out</span>
        </button>
      </div>
    </header>
  );
};
