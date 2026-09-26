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
  Copy,
  Key,
  RefreshCw,
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

  // Ingestion token state (Slice 003)
  const [hasIngestionToken, setHasIngestionToken] = useState<boolean>(false);
  const [loadingToken, setLoadingToken] = useState<boolean>(true);
  const [generatedToken, setGeneratedToken] = useState<string | null>(null);
  const [generatingToken, setGeneratingToken] = useState<boolean>(false);
  const [revokingToken, setRevokingToken] = useState<boolean>(false);
  const [tokenCopied, setTokenCopied] = useState<boolean>(false);
  const [tokenSnippetTab, setTokenSnippetTab] = useState<'curl' | 'python'>('curl');
  const [ingestError, setIngestError] = useState<string | null>(null);
  const [ingestSuccess, setIngestSuccess] = useState<string | null>(null);

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

    try {
      setLoadingToken(true);
      const tokenRes = await api.getIngestionTokenStatus(workspace.id);
      setHasIngestionToken(tokenRes.has_token);
    } catch (err: any) {
      console.error('Failed to fetch ingestion token status', err);
    } finally {
      setLoadingToken(false);
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

  const handleGenerateToken = async () => {
    if (!workspace) return;
    if (hasIngestionToken) {
      if (
        !window.confirm(
          'Rotating this ingestion token will immediately invalidate your previous token. Any pipelines using the old token will fail until updated. Continue?'
        )
      ) {
        return;
      }
    }

    setGeneratingToken(true);
    setIngestError(null);
    setIngestSuccess(null);
    try {
      const res = await api.generateIngestionToken(workspace.id);
      setGeneratedToken(res.token);
      setHasIngestionToken(true);
      setIngestSuccess('Ingestion token generated successfully! Please copy and store it securely now.');
      await refreshWorkspace();
    } catch (err: any) {
      setIngestError(err.message || 'Failed to generate ingestion token.');
    } finally {
      setGeneratingToken(false);
    }
  };

  const handleRevokeToken = async () => {
    if (!workspace) return;
    if (
      !window.confirm(
        'Are you sure you want to revoke this ingestion token? Agent runs pushed with this token will be rejected immediately.'
      )
    ) {
      return;
    }

    setRevokingToken(true);
    setIngestError(null);
    setIngestSuccess(null);
    try {
      await api.revokeIngestionToken(workspace.id);
      setGeneratedToken(null);
      setHasIngestionToken(false);
      setIngestSuccess('Ingestion token has been revoked.');
      await refreshWorkspace();
    } catch (err: any) {
      setIngestError(err.message || 'Failed to revoke ingestion token.');
    } finally {
      setRevokingToken(false);
    }
  };

  const handleCopyToken = () => {
    if (!generatedToken) return;
    navigator.clipboard.writeText(generatedToken);
    setTokenCopied(true);
    setTimeout(() => setTokenCopied(false), 2000);
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

          {/* Custom Webhook / SDK Card (Slice 003) */}
          <div className="settings-card" id="sdk-settings-card">
            <div className="settings-card-header">
              <div className="settings-card-icon" style={{ background: 'rgba(6, 182, 212, 0.15)', color: '#06b6d4' }}>
                <Terminal size={20} />
              </div>
              <div className="settings-card-title-group">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <h2 className="settings-card-title">Custom SDK / Webhook Ingestion</h2>
                  {loadingToken ? (
                    <Loader2 size={16} className="spinner" />
                  ) : hasIngestionToken ? (
                    <span className="badge badge-success" id="ingest-connected-badge">
                      <span className="pulsing-dot" /> Active
                    </span>
                  ) : (
                    <span className="badge badge-neutral" id="ingest-disconnected-badge">
                      Not Configured
                    </span>
                  )}
                </div>
                <p className="settings-card-subtitle">
                  Ingest execution traces directly from Python or TypeScript agent runtimes without LangSmith.
                </p>
              </div>
            </div>

            {/* Error or Success banners for Ingestion */}
            {ingestError && (
              <div className="alert-banner alert-banner-error" id="ingest-error-banner">
                <AlertCircle size={18} />
                <span>{ingestError}</span>
              </div>
            )}

            {ingestSuccess && (
              <div className="alert-banner alert-banner-success" id="ingest-success-banner">
                <CheckCircle size={18} />
                <span>{ingestSuccess}</span>
              </div>
            )}

            {/* Newly Generated Token Reveal Banner */}
            {generatedToken && (
              <div
                className="connected-panel"
                id="new-token-container"
                style={{
                  background: 'rgba(99, 102, 241, 0.08)',
                  borderColor: 'rgba(99, 102, 241, 0.3)',
                  flexDirection: 'column',
                  alignItems: 'stretch',
                  gap: '0.75rem',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#c7d2fe', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <Key size={14} style={{ color: '#818cf8' }} /> Your New Ingestion Token
                  </span>
                  <span style={{ fontSize: '0.75rem', color: '#f59e0b', fontWeight: 600 }}>
                    Copy now — will not be displayed again
                  </span>
                </div>

                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  <input
                    type="text"
                    readOnly
                    id="new-token-input"
                    value={generatedToken}
                    className="input-field font-mono"
                    style={{ background: '#0f172a', borderColor: '#4f46e5', color: '#a5b4fc', fontSize: '0.85rem' }}
                    onClick={(e) => (e.target as HTMLInputElement).select()}
                  />
                  <button
                    type="button"
                    className="btn-primary"
                    id="copy-token-btn"
                    onClick={handleCopyToken}
                    style={{ whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: '0.4rem' }}
                  >
                    {tokenCopied ? (
                      <>
                        <CheckCircle size={15} />
                        <span>Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy size={15} />
                        <span>Copy Token</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}

            {/* Active Ingestion Status Panel */}
            {!loadingToken && hasIngestionToken && (
              <div className="connected-panel" id="sdk-connected-panel">
                <div className="connected-details">
                  <div className="detail-item">
                    <span className="detail-label">Endpoint</span>
                    <span className="detail-value font-mono text-accent" id="ingest-endpoint-text">
                      POST /api/v1/ingest/run
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Status</span>
                    <span className="detail-value text-success">Active & Ready</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Security</span>
                    <span className="detail-value text-muted" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      <ShieldCheck size={14} style={{ color: '#10b981' }} /> SHA-256 Hashed (NFR-001)
                    </span>
                  </div>
                </div>

                <div className="connected-actions" style={{ display: 'flex', gap: '0.75rem' }}>
                  <button
                    type="button"
                    className="btn-secondary"
                    id="rotate-token-btn"
                    onClick={handleGenerateToken}
                    disabled={generatingToken}
                    title="Rotate ingestion token (invalidates old token)"
                  >
                    {generatingToken ? (
                      <>
                        <Loader2 size={15} className="spinner" />
                        <span>Rotating...</span>
                      </>
                    ) : (
                      <>
                        <RefreshCw size={15} />
                        <span>Rotate Token</span>
                      </>
                    )}
                  </button>

                  <button
                    type="button"
                    className="btn-danger"
                    id="revoke-token-btn"
                    onClick={handleRevokeToken}
                    disabled={revokingToken}
                    title="Revoke ingestion token"
                  >
                    {revokingToken ? (
                      <>
                        <Loader2 size={15} className="spinner" />
                        <span>Revoking...</span>
                      </>
                    ) : (
                      <>
                        <Trash2 size={15} />
                        <span>Revoke Token</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}

            {/* Initial Ingestion Token Creation Form */}
            {!loadingToken && !hasIngestionToken && (
              <div className="info-box" style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                <div>
                  <p style={{ fontWeight: 600, color: '#f8fafc', marginBottom: '0.25rem' }}>
                    Generate an Ingestion Token
                  </p>
                  <p style={{ fontSize: '0.84rem' }}>
                    A per-workspace high-entropy token allows your agent code, SDK, or CI to securely push execution traces directly into agenoscope.
                  </p>
                </div>
                <button
                  type="button"
                  className="btn-primary"
                  id="generate-token-btn"
                  onClick={handleGenerateToken}
                  disabled={generatingToken}
                  style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                >
                  {generatingToken ? (
                    <>
                      <Loader2 size={16} className="spinner" />
                      <span>Generating...</span>
                    </>
                  ) : (
                    <>
                      <Key size={16} />
                      <span>Generate Ingestion Token</span>
                    </>
                  )}
                </button>
              </div>
            )}

            {/* Integration Quickstart & Code Examples */}
            <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '1.25rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <span style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                  Integration Quickstart
                </span>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    type="button"
                    id="tab-curl-btn"
                    onClick={() => setTokenSnippetTab('curl')}
                    style={{
                      background: tokenSnippetTab === 'curl' ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
                      color: tokenSnippetTab === 'curl' ? '#a5b4fc' : 'var(--text-muted)',
                      border: '1px solid',
                      borderColor: tokenSnippetTab === 'curl' ? 'rgba(99, 102, 241, 0.4)' : 'transparent',
                      borderRadius: 'var(--radius-sm)',
                      padding: '0.25rem 0.65rem',
                      fontSize: '0.75rem',
                      cursor: 'pointer',
                    }}
                  >
                    cURL
                  </button>
                  <button
                    type="button"
                    id="tab-python-btn"
                    onClick={() => setTokenSnippetTab('python')}
                    style={{
                      background: tokenSnippetTab === 'python' ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
                      color: tokenSnippetTab === 'python' ? '#a5b4fc' : 'var(--text-muted)',
                      border: '1px solid',
                      borderColor: tokenSnippetTab === 'python' ? 'rgba(99, 102, 241, 0.4)' : 'transparent',
                      borderRadius: 'var(--radius-sm)',
                      padding: '0.25rem 0.65rem',
                      fontSize: '0.75rem',
                      cursor: 'pointer',
                    }}
                  >
                    Python
                  </button>
                </div>
              </div>

              <div
                style={{
                  background: '#090d16',
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-md)',
                  padding: '1rem',
                  overflowX: 'auto',
                }}
              >
                <pre style={{ margin: 0, fontSize: '0.8rem', fontFamily: 'var(--font-mono)', color: '#e2e8f0', lineHeight: 1.6 }}>
                  {tokenSnippetTab === 'curl' ? (
`curl -X POST "${window.location.origin}/api/v1/ingest/run" \\
  -H "X-Ingestion-Token: ${generatedToken || '<YOUR_INGESTION_TOKEN>'}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "financial-report-agent",
    "status": "error",
    "external_run_id": "run-abc-123",
    "error_message": "KeyError: 'financial_data' missing from tool response",
    "latency_ms": 1420.5,
    "total_tokens": 820,
    "raw_trace": {
      "steps": [
        {"action": "call_sec_filing_tool", "status": "failed", "error": "schema drift"}
      ]
    }
  }'`
                  ) : (
`import requests

url = "${window.location.origin}/api/v1/ingest/run"
headers = {
    "X-Ingestion-Token": "${generatedToken || '<YOUR_INGESTION_TOKEN>'}",
    "Content-Type": "application/json"
}
payload = {
    "name": "financial-report-agent",
    "status": "error",
    "external_run_id": "run-abc-123",
    "error_message": "KeyError: 'financial_data' missing from tool response",
    "latency_ms": 1420.5,
    "total_tokens": 820,
    "raw_trace": {
        "steps": [
            {"action": "call_sec_filing_tool", "status": "failed", "error": "schema drift"}
        ]
    }
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())`
                  )}
                </pre>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};
