import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ApiException } from '../api/client';
import { ArrowRight, AlertCircle, Loader2 } from 'lucide-react';

export const SignupPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [workspaceName, setWorkspaceName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { signup } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError('Password must be at least 8 characters long');
      return;
    }

    setIsSubmitting(true);

    try {
      await signup(email, password, workspaceName || undefined);
      navigate('/runs', { replace: true });
    } catch (err: any) {
      if (err instanceof ApiException) {
        setError(err.message);
      } else {
        setError('Failed to create account. Please check your network and try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="auth-wrapper">
      <div className="auth-card">
        <div className="auth-header">
          <div className="brand-badge">Get Started</div>
          <h1 className="brand-logo">Create Account</h1>
          <p className="auth-subtitle">Bootstrap your workspace for agent diagnostics</p>
        </div>

        {error && (
          <div className="alert-error" id="signup-error-alert" role="alert">
            <AlertCircle size={18} className="flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} id="signup-form">
          <div className="form-group">
            <label className="form-label" htmlFor="signup-email-input">
              Email Address
            </label>
            <input
              id="signup-email-input"
              type="email"
              className="form-input"
              placeholder="you@domain.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="signup-password-input">
              Password (minimum 8 characters)
            </label>
            <input
              id="signup-password-input"
              type="password"
              className="form-input"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="signup-workspace-input">
              Workspace Name <span style={{ color: 'var(--text-muted)' }}>(Optional)</span>
            </label>
            <input
              id="signup-workspace-input"
              type="text"
              className="form-input"
              placeholder="e.g. Production Agents"
              value={workspaceName}
              onChange={(e) => setWorkspaceName(e.target.value)}
            />
          </div>

          <button
            type="submit"
            id="signup-submit-button"
            className="btn-primary"
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                <span>Creating Account...</span>
              </>
            ) : (
              <>
                <span>Sign Up & Create Workspace</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </form>

        <div className="auth-footer">
          Already have an account?
          <Link to="/login" id="login-link">Sign in</Link>
        </div>
      </div>
    </div>
  );
};
