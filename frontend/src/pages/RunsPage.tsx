import React from 'react';
import { useAuth } from '../context/AuthContext';
import { Navbar } from '../components/Navbar';
import { Bot, Terminal, Link as LinkIcon } from 'lucide-react';

export const RunsPage: React.FC = () => {
  const { workspace } = useAuth();

  return (
    <div className="app-container">
      <Navbar />

      <main className="main-content">
        <div className="page-header">
          <div>
            <h1 className="page-title">Agent Runs</h1>
            <p className="page-description">
              Diagnostic traces and failure analysis for workspace{' '}
              <strong style={{ color: '#c7d2fe' }}>{workspace?.name}</strong>
            </p>
          </div>
        </div>

        <div className="empty-state-card" id="runs-empty-state">
          <div className="empty-icon-wrapper">
            <Bot size={32} />
          </div>

          <h2 className="empty-title">No runs yet</h2>
          <p className="empty-text">
            There are currently no recorded agent runs in this workspace. Once you connect LangSmith
            or push traces via the agenoscope SDK, your runs will automatically appear here.
          </p>

          <div className="next-steps-grid">
            <div className="next-step-box">
              <div className="next-step-title">
                <LinkIcon size={16} style={{ color: '#818cf8' }} />
                <span>LangSmith Integration</span>
              </div>
              <p className="next-step-desc">
                Connect your LangSmith project to automatically pull and filter failed agent traces (Slice 002).
              </p>
            </div>

            <div className="next-step-box">
              <div className="next-step-title">
                <Terminal size={16} style={{ color: '#06b6d4' }} />
                <span>SDK / Webhook Push</span>
              </div>
              <p className="next-step-desc">
                Directly push execution traces from Python or TypeScript agent runtimes via webhook (Slice 003).
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};
