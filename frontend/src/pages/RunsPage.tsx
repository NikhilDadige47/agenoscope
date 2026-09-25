import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Navbar } from '../components/Navbar';
import { api } from '../api/client';
import { AgentRun } from '../types';
import {
  Bot,
  Link as LinkIcon,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Clock,
  Coins,
  Code,
  X,
  Sparkles,
  Search,
} from 'lucide-react';

export const RunsPage: React.FC = () => {
  const { workspace } = useAuth();
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [syncing, setSyncing] = useState<boolean>(false);
  const [statusFilter, setStatusFilter] = useState<'all' | 'error' | 'success'>('error');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedRun, setSelectedRun] = useState<AgentRun | null>(null);

  const fetchRuns = async (isSync: boolean = false) => {
    if (!workspace) return;
    try {
      if (isSync) {
        setSyncing(true);
      } else {
        setLoading(true);
      }
      const data = await api.getRuns(workspace.id, {
        status: statusFilter,
        sync: isSync,
      });
      setRuns(data);
    } catch (err) {
      console.error('Failed to fetch runs', err);
    } finally {
      setLoading(false);
      setSyncing(false);
    }
  };

  useEffect(() => {
    fetchRuns(false);
  }, [workspace?.id, statusFilter]);

  const handleSync = () => {
    fetchRuns(true);
  };

  const filteredRuns = runs.filter((run) => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    return (
      (run.name && run.name.toLowerCase().includes(query)) ||
      (run.external_run_id && run.external_run_id.toLowerCase().includes(query)) ||
      (run.error_message && run.error_message.toLowerCase().includes(query))
    );
  });

  const errorCount = runs.filter((r) => r.status === 'error').length;

  return (
    <div className="app-container">
      <Navbar />

      <main className="main-content">
        <div className="page-header">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <h1 className="page-title">Agent Runs</h1>
              {workspace?.langsmith_project && (
                <span className="badge badge-accent" id="connected-project-pill">
                  <LinkIcon size={12} /> {workspace.langsmith_project}
                </span>
              )}
            </div>
            <p className="page-description">
              Diagnostic traces and failure analysis for workspace{' '}
              <strong style={{ color: '#c7d2fe' }}>{workspace?.name}</strong>
            </p>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button
              id="refresh-runs-btn"
              onClick={handleSync}
              disabled={syncing || loading}
              className="btn-secondary"
              title="Sync latest runs from LangSmith"
            >
              <RefreshCw size={15} className={syncing ? 'spinner' : ''} />
              <span>{syncing ? 'Syncing...' : 'Sync LangSmith'}</span>
            </button>
            <Link to="/settings" className="btn-secondary">
              <LinkIcon size={15} />
              <span>Integration Settings</span>
            </Link>
          </div>
        </div>

        {/* Not connected banner if LangSmith is not configured */}
        {!workspace?.langsmith_connected && !workspace?.langsmith_project && (
          <div className="alert-banner alert-banner-info" id="langsmith-prompt-banner" style={{ marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <LinkIcon size={18} style={{ color: '#818cf8', flexShrink: 0 }} />
              <div>
                <strong>LangSmith Not Connected:</strong> Connect your LangSmith project to automatically ingest failed
                agent runs and unlock automated diagnosis.
              </div>
            </div>
            <Link to="/settings" className="btn-primary" style={{ padding: '0.4rem 0.9rem', fontSize: '0.85rem' }}>
              Connect Now
            </Link>
          </div>
        )}

        {/* Filters and Controls */}
        <div className="runs-toolbar">
          <div className="filter-tabs" role="tablist">
            <button
              id="filter-errors-tab"
              role="tab"
              aria-selected={statusFilter === 'error'}
              className={`filter-tab ${statusFilter === 'error' ? 'filter-tab-active filter-tab-error' : ''}`}
              onClick={() => setStatusFilter('error')}
            >
              <AlertCircle size={15} />
              <span>Errors Only</span>
              {statusFilter === 'error' && errorCount > 0 && (
                <span className="tab-count-badge tab-count-error">{errorCount}</span>
              )}
            </button>

            <button
              id="filter-all-tab"
              role="tab"
              aria-selected={statusFilter === 'all'}
              className={`filter-tab ${statusFilter === 'all' ? 'filter-tab-active' : ''}`}
              onClick={() => setStatusFilter('all')}
            >
              <span>All Runs</span>
            </button>

            <button
              id="filter-success-tab"
              role="tab"
              aria-selected={statusFilter === 'success'}
              className={`filter-tab ${statusFilter === 'success' ? 'filter-tab-active filter-tab-success' : ''}`}
              onClick={() => setStatusFilter('success')}
            >
              <CheckCircle2 size={15} />
              <span>Success</span>
            </button>
          </div>

          <div className="search-input-wrapper">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              id="runs-search-input"
              placeholder="Filter by agent name, ID, or error..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-field"
            />
          </div>
        </div>

        {/* Content Area */}
        {loading ? (
          <div className="loading-state-card">
            <RefreshCw size={24} className="spinner text-accent" />
            <p>Loading agent traces...</p>
          </div>
        ) : filteredRuns.length === 0 ? (
          <div className="empty-state-card" id="runs-empty-state">
            <div className="empty-icon-wrapper">
              {statusFilter === 'error' ? <CheckCircle2 size={32} style={{ color: '#10b981' }} /> : <Bot size={32} />}
            </div>

            <h2 className="empty-title">
              {statusFilter === 'error'
                ? 'No failed runs found'
                : searchQuery
                ? 'No matching runs found'
                : 'No runs recorded yet'}
            </h2>
            <p className="empty-text">
              {statusFilter === 'error'
                ? 'Great news! There are currently no recorded failure traces matching this filter in your connected project.'
                : !workspace?.langsmith_connected
                ? 'Connect your LangSmith project in Settings to pull agent runs automatically.'
                : 'Click "Sync LangSmith" above to fetch the latest traces from your project.'}
            </p>

            {!workspace?.langsmith_connected && (
              <div style={{ marginTop: '1.25rem' }}>
                <Link to="/settings" className="btn-primary">
                  <LinkIcon size={16} />
                  <span>Configure LangSmith Integration</span>
                </Link>
              </div>
            )}
          </div>
        ) : (
          <div className="runs-list" id="runs-list-container">
            {filteredRuns.map((run) => (
              <div
                key={run.id}
                className={`run-card ${run.status === 'error' ? 'run-card-error' : ''}`}
                id={`run-item-${run.id}`}
              >
                <div className="run-card-header">
                  <div className="run-card-left">
                    <span
                      className={`run-status-badge ${
                        run.status === 'error'
                          ? 'status-error'
                          : run.status === 'success'
                          ? 'status-success'
                          : 'status-unknown'
                      }`}
                    >
                      {run.status === 'error' ? (
                        <>
                          <AlertCircle size={13} />
                          <span>FAILED</span>
                        </>
                      ) : run.status === 'success' ? (
                        <>
                          <CheckCircle2 size={13} />
                          <span>SUCCESS</span>
                        </>
                      ) : (
                        <span>{run.status.toUpperCase()}</span>
                      )}
                    </span>

                    <h3 className="run-name">{run.name || 'AgentRun'}</h3>
                    {run.external_run_id && (
                      <span className="run-id-pill font-mono" title={run.external_run_id}>
                        {run.external_run_id.length > 16
                          ? `${run.external_run_id.slice(0, 14)}...`
                          : run.external_run_id}
                      </span>
                    )}
                  </div>

                  <div className="run-card-metrics">
                    {run.latency_ms !== null && run.latency_ms !== undefined && (
                      <div className="metric-badge" title="Execution Latency">
                        <Clock size={13} />
                        <span>{run.latency_ms < 1000 ? `${run.latency_ms}ms` : `${(run.latency_ms / 1000).toFixed(2)}s`}</span>
                      </div>
                    )}

                    {run.total_tokens !== null && run.total_tokens !== undefined && (
                      <div className="metric-badge" title="Total Tokens">
                        <Coins size={13} />
                        <span>{run.total_tokens.toLocaleString()} tok</span>
                      </div>
                    )}

                    <div className="run-timestamp" title={run.fetched_at}>
                      {new Date(run.fetched_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </div>
                </div>

                {/* Error preview box */}
                {run.status === 'error' && run.error_message && (
                  <div className="run-error-preview">
                    <span className="error-prefix">Root Error:</span>
                    <span className="error-text font-mono">{run.error_message}</span>
                  </div>
                )}

                {/* Card actions */}
                <div className="run-card-footer">
                  <div className="source-tag">
                    <span className="source-dot" />
                    <span>via {run.source}</span>
                  </div>

                  <div className="card-actions">
                    <button
                      type="button"
                      className="btn-ghost"
                      onClick={() => setSelectedRun(run)}
                      title="Inspect full JSON trace payload"
                    >
                      <Code size={14} />
                      <span>View Trace</span>
                    </button>

                    {run.status === 'error' && (
                      <button
                        type="button"
                        className="btn-diagnose-preview"
                        title="Automated diagnosis workflow (Slice 004)"
                        onClick={() => alert(`Run ${run.external_run_id || run.id} selected for diagnosis. (Diagnosis Workflow unlocks in SLICE-004)`)}
                      >
                        <Sparkles size={14} />
                        <span>Diagnose</span>
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Trace Modal / Drawer */}
        {selectedRun && (
          <div className="modal-backdrop" onClick={() => setSelectedRun(null)}>
            <div className="modal-container" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <Code size={18} style={{ color: '#818cf8' }} />
                  <div>
                    <h3 className="modal-title">Trace Details: {selectedRun.name || selectedRun.id}</h3>
                    <p className="modal-subtitle font-mono">External ID: {selectedRun.external_run_id || 'N/A'}</p>
                  </div>
                </div>
                <button
                  type="button"
                  className="modal-close-btn"
                  onClick={() => setSelectedRun(null)}
                >
                  <X size={18} />
                </button>
              </div>

              <div className="modal-body">
                {selectedRun.error_message && (
                  <div className="alert-banner alert-banner-error" style={{ marginBottom: '1rem' }}>
                    <AlertCircle size={16} />
                    <span className="font-mono" style={{ fontSize: '0.85rem' }}>{selectedRun.error_message}</span>
                  </div>
                )}

                <div className="json-viewer-wrapper">
                  <div className="json-viewer-header">
                    <span>Normalized Trace Representation</span>
                    <span className="json-viewer-size">
                      {JSON.stringify(selectedRun.raw_trace).length} bytes
                    </span>
                  </div>
                  <pre className="json-pre">
                    {JSON.stringify(selectedRun.raw_trace, null, 2)}
                  </pre>
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setSelectedRun(null)}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};
