import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { Navbar } from '../components/Navbar';
import { api, ApiException } from '../api/client';
import { LangSmithStatus } from '../types';
import {
  Link as LinkIcon,
  CheckCircle,
  AlertCircle,
  Loader2,
  Trash2,
  ShieldCheck,
  Eye,
  EyeOff,
  Terminal,
} from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const { workspace, refreshWorkspace } = useAuth();
  const [langsmithStatus, setLangsmithStatus] = useState<LangSmithStatus | null>(null);
  const [loadingStatus, setLoadingStatus] = useState<boolean>(true);

  // Form state
  const [apiKey, setApiKey] = useState<string>('');
  const [project, setProject] = useState<string>('');
  const [showKey, setShowKey] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [disconnecting, setDisconnecting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const fetchStatus = async () => {
    if (!workspace) return;
    try {
      setLoadingStatus(true);
      const res = await api.getLangSmithStatus(workspace.id);
      setLangsmithStatus(res);
      if (res.project) {
        setProject(res.project);
      }
    } catch (err: any) {
      console.error('Failed to fetch LangSmith status', err);
    } finally {
      setLoadingStatus(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, [workspace?.id]);

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspace) return;

    setErrorMessage(null);
    setSuccessMessage(null);

    if (!apiKey.trim()) {
      setErrorMessage('Please enter your LangSmith API Key.');
      return;
    }
    if (!project.trim()) {
      setErrorMessage('Please enter your LangSmith Project Name.');
      return;
    }

    setSubmitting(true);
    try {
      const res = await api.connectLangSmith(workspace.id, {
        langsmith_key: apiKey.trim(),
        project: project.trim(),
      });
      setLangsmithStatus(res);
      setSuccessMessage(`Successfully connected to LangSmith project "${res.project}"! Runs are now syncing.`);
      setApiKey('');
      await refreshWorkspace();
    } catch (err) {
      if (err instanceof ApiException) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Failed to connect to LangSmith. Please verify your network and credentials.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleDisconnect = async () => {
    if (!workspace) return;
    if (!window.confirm('Are you sure you want to disconnect LangSmith from this workspace?')) {
      return;
    }

    setDisconnecting(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const res = await api.disconnectLangSmith(workspace.id);
      setLangsmithStatus(res);
      setSuccessMessage('LangSmith has been disconnected.');
      setApiKey('');
      await refreshWorkspace();
    } catch (err: any) {
      setErrorMessage('Failed to disconnect LangSmith.');
    } finally {
      setDisconnecting(false);
    }
  };

  return (
    <div className="app-container">
      <Navbar />

      <main className="main-content">
        <div className="page-header">
          <div>
            <h1 className="page-title">Workspace Settings</h1>
            <p className="page-description">
              Manage telemetry integrations, API credentials, and ingestion sources for{' '}
              <strong style={{ color: '#c7d2fe' }}>{workspace?.name}</strong>.
            </p>
          </div>
        </div>

        <div className="settings-grid">
          {/* LangSmith Card */}
          <div className="settings-card" id="langsmith-settings-card">
            <div className="settings-card-header">
              <div className="settings-card-icon langsmith-icon">
                <LinkIcon size={20} />
              </div>
              <div className="settings-card-title-group">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <h2 className="settings-card-title">LangSmith Telemetry</h2>
                  {loadingStatus ? (
                    <Loader2 size={16} className="spinner" />
                  ) : langsmithStatus?.connected ? (
                    <span className="badge badge-success" id="langsmith-connected-badge">
                      <span className="pulsing-dot" /> Connected
                    </span>
                  ) : (
                    <span className="badge badge-neutral" id="langsmith-disconnected-badge">
                      Not Connected
                    </span>
                  )}
                </div>
                <p className="settings-card-subtitle">
                  Connect your LangSmith project to automatically ingest, index, and diagnose failed agent traces.
                </p>
              </div>
            </div>

            {/* Error or Success banners */}
            {errorMessage && (
              <div className="alert-banner alert-banner-error" id="langsmith-error-banner">
                <AlertCircle size={18} />
                <span>{errorMessage}</span>
              </div>
            )}

            {successMessage && (
              <div className="alert-banner alert-banner-success" id="langsmith-success-banner">
                <CheckCircle size={18} />
                <span>{successMessage}</span>
              </div>
            )}

            {/* Connected State View */}
            {!loadingStatus && langsmithStatus?.connected && (
              <div className="connected-panel" id="langsmith-connected-panel">
                <div className="connected-details">
                  <div className="detail-item">
                    <span className="detail-label">Connected Project</span>
                    <span className="detail-value font-mono" id="connected-project-name">
                      {langsmithStatus.project}
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Status</span>
                    <span className="detail-value text-success">Active & Syncing</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Security</span>
                    <span className="detail-value text-muted" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      <ShieldCheck size={14} style={{ color: '#10b981' }} /> Encrypted at rest (AES)
                    </span>
                  </div>
                </div>

                <div className="connected-actions">
                  <button
                    type="button"
                    className="btn-danger"
                    id="disconnect-langsmith-btn"
                    onClick={handleDisconnect}
                    disabled={disconnecting}
                  >
                    {disconnecting ? (
                      <>
                        <Loader2 size={16} className="spinner" />
                        <span>Disconnecting...</span>
                      </>
                    ) : (
                      <>
                        <Trash2 size={16} />
                        <span>Disconnect LangSmith</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}

            {/* Connect / Update Form */}
            <form onSubmit={handleConnect} className="settings-form" id="langsmith-form">
              <div className="form-group">
                <label htmlFor="langsmith-project-input" className="form-label">
                  Project Name <span style={{ color: '#ef4444' }}>*</span>
                </label>
                <input
                  id="langsmith-project-input"
                  type="text"
                  className="input-field"
                  placeholder="e.g. production-agent, customer-support"
                  value={project}
                  onChange={(e) => setProject(e.target.value)}
                  disabled={submitting}
                  required
                />
                <span className="form-help">
                  The exact name of your LangSmith project containing the agent runs.
                </span>
              </div>

              <div className="form-group">
                <label htmlFor="langsmith-key-input" className="form-label">
                  LangSmith API Key <span style={{ color: '#ef4444' }}>*</span>
                </label>
                <div className="password-input-wrapper">
                  <input
                    id="langsmith-key-input"
                    type={showKey ? 'text' : 'password'}
                    className="input-field"
                    placeholder="lsv2_pt_..."
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    disabled={submitting}
                    required
                  />
                  <button
                    type="button"
                    className="password-toggle-btn"
                    onClick={() => setShowKey(!showKey)}
                    tabIndex={-1}
                  >
                    {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                <span className="form-help">
                  Personal or service API key with read access to the project.
                </span>
              </div>

              <div className="security-notice">
                <ShieldCheck size={16} style={{ color: '#818cf8', flexShrink: 0 }} />
                <span>
                  <strong>Security Guarantee:</strong> Your key is encrypted at rest using server-side AES encryption,
                  used solely to fetch runs for your workspace, and never returned in any API response.
                </span>
              </div>

              <div className="form-actions">
                <button
                  type="submit"
                  className="btn-primary"
                  id="connect-langsmith-btn"
                  disabled={submitting}
                >
                  {submitting ? (
                    <>
                      <Loader2 size={16} className="spinner" />
                      <span>Validating with LangSmith...</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle size={16} />
                      <span>{langsmithStatus?.connected ? 'Update Connection' : 'Connect Project'}</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>

          {/* Custom Webhook / SDK Card (Slice 003 Preview) */}
          <div className="settings-card" id="sdk-settings-card" style={{ opacity: 0.85 }}>
            <div className="settings-card-header">
              <div className="settings-card-icon" style={{ background: 'rgba(6, 182, 212, 0.1)', color: '#06b6d4' }}>
                <Terminal size={20} />
              </div>
              <div className="settings-card-title-group">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <h2 className="settings-card-title">Custom SDK / Webhook Ingestion</h2>
                  <span className="badge badge-neutral">Slice 003</span>
                </div>
                <p className="settings-card-subtitle">
                  Ingest execution traces directly from Python or TypeScript agent runtimes without LangSmith.
                </p>
              </div>
            </div>

            <div className="info-box">
              <p>
                Direct webhook ingestion endpoints and per-workspace ingestion tokens will be configurable here in{' '}
                <strong>SLICE-003</strong>.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};
