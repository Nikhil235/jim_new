import React, { StrictMode, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ClerkProvider } from '@clerk/react'
import { Key, Save } from 'lucide-react'
import './index.css'
import App from './App.jsx'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error("Clerk initialization error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="login-container">
          <div className="orb orb-1"></div>
          <div className="orb orb-2"></div>
          <div className="orb orb-3"></div>
          <div className="login-glass-card" style={{ textAlign: 'center' }}>
            <div className="login-logo-icon">M</div>
            <h2 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-bright)', marginBottom: '8px' }}>Secure Link Offline</h2>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '24px' }}>
              Could not establish connection to the authorization servers. The saved Clerk Publishable Key may be invalid or expired.
            </p>
            <button
              onClick={() => {
                localStorage.removeItem('VITE_CLERK_PUBLISHABLE_KEY');
                window.location.reload();
              }}
              className="login-button"
            >
              Reset Config Key
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

function MainApp() {
  const [clerkKey, setClerkKey] = useState(() => {
    return localStorage.getItem('VITE_CLERK_PUBLISHABLE_KEY') || import.meta.env.VITE_CLERK_PUBLISHABLE_KEY || '';
  });
  const [inputKey, setInputKey] = useState('');
  const [error, setError] = useState('');

  const isPlaceholder = !clerkKey || clerkKey === 'pk_test_Y2xlcmsuYWNjb3VudHMuZGV2JA' || clerkKey.trim() === '';

  const handleSaveKey = (e) => {
    e.preventDefault();
    if (!inputKey.startsWith('pk_')) {
      setError('Invalid key format. Clerk Publishable Keys must start with "pk_"');
      return;
    }
    localStorage.setItem('VITE_CLERK_PUBLISHABLE_KEY', inputKey.trim());
    setClerkKey(inputKey.trim());
    setError('');
    window.location.reload();
  };

  const handleClearKey = () => {
    localStorage.removeItem('VITE_CLERK_PUBLISHABLE_KEY');
    setClerkKey(import.meta.env.VITE_CLERK_PUBLISHABLE_KEY || '');
    window.location.reload();
  };

  if (isPlaceholder) {
    return (
      <div className="login-container">
        {/* Background Orbs */}
        <div className="orb orb-1"></div>
        <div className="orb orb-2"></div>
        <div className="orb orb-3"></div>

        <div className="login-glass-card animate-in" style={{ maxWidth: '480px' }}>
          <div className="login-header">
            <div className="login-logo-icon">M</div>
            <h2>Clerk Auth Setup</h2>
            <p>Configuration Panel</p>
          </div>

          <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '24px', textAlign: 'center' }}>
            <p style={{ marginBottom: '16px' }}>
              A valid <strong style={{ color: 'var(--text-bright)' }}>Clerk Publishable Key</strong> is required to enable secure login for the Mini-Medallion Trading Dashboard.
            </p>
            <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '16px', textAlign: 'left' }}>
              <h4 style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-bright)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '10px' }}>How to configure your credentials:</h4>
              <ol style={{ listStylePosition: 'inside', color: 'var(--text-muted)', fontSize: '12px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <li>Log in to your <a href="https://dashboard.clerk.com/" target="_blank" rel="noopener noreferrer">Clerk Dashboard</a>.</li>
                <li>Select your application instance (or create a new one).</li>
                <li>Go to <strong>API Keys</strong> in the sidebar, and copy the <strong>Publishable Key</strong>.</li>
                <li>Paste it below to load instantly, or set <code style={{ fontFamily: 'var(--font-mono)', fontSize: '11px' }}>VITE_CLERK_PUBLISHABLE_KEY</code> in your <code style={{ fontFamily: 'var(--font-mono)', fontSize: '11px' }}>dashboard/.env</code>.</li>
              </ol>
            </div>
          </div>

          {error && (
            <div style={{ marginBottom: '16px', padding: '12px', background: 'rgba(255,77,106,0.1)', border: '1px solid rgba(255,77,106,0.2)', color: 'var(--red)', fontSize: '12px', borderRadius: 'var(--radius-sm)', textAlign: 'center', fontWeight: 500 }}>
              {error}
            </div>
          )}

          <form onSubmit={handleSaveKey} className="login-form">
            <div className="input-group">
              <input
                type="text"
                placeholder="Paste Clerk Publishable Key (pk_test_...)"
                value={inputKey}
                onChange={(e) => setInputKey(e.target.value)}
                required
                style={{ fontFamily: 'var(--font-mono)', fontSize: '13px' }}
              />
              <Key className="input-icon" size={18} />
            </div>

            <button type="submit" className="login-button">
              <Save size={18} /> Apply Publishable Key
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <ClerkProvider
        publishableKey={clerkKey}
        signInUrl="/sign-in"
        signUpUrl="/sign-up"
        afterSignOutUrl="/sign-in"
        signInFallbackRedirectUrl="/dashboard"
        signUpFallbackRedirectUrl="/dashboard"
      >
        <BrowserRouter>
          <App onClearKey={handleClearKey} hasCustomKey={!!localStorage.getItem('VITE_CLERK_PUBLISHABLE_KEY')} />
        </BrowserRouter>
      </ClerkProvider>
    </ErrorBoundary>
  );
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <MainApp />
  </StrictMode>,
)
