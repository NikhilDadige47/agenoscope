import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { LogOut, Layers, Activity, Settings as SettingsIcon, Terminal } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, workspace, logout } = useAuth();

  return (
    <header className="navbar">
      <div className="navbar-left">
        <NavLink to="/runs" className="navbar-brand">
          <div className="navbar-logo-icon">
            <Activity size={18} />
          </div>
          <span>agenoscope</span>
        </NavLink>

        <nav className="navbar-nav">
          <NavLink
            to="/runs"
            className={({ isActive }) =>
              `nav-link ${isActive ? 'nav-link-active' : ''}`
            }
            id="nav-runs-link"
          >
            <Terminal size={15} />
            <span>Agent Runs</span>
          </NavLink>

          <NavLink
            to="/settings"
            className={({ isActive }) =>
              `nav-link ${isActive ? 'nav-link-active' : ''}`
            }
            id="nav-settings-link"
          >
            <SettingsIcon size={15} />
            <span>Settings</span>
          </NavLink>
        </nav>
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
