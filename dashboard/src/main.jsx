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
        <div className="login-container flex items-center justify-center min-h-screen bg-[#0a0e1a] relative overflow-hidden p-4">
          <div className="orb orb-1"></div>
          <div className="orb orb-2"></div>
          <div className="orb orb-3"></div>
          <div className="login-glass-card max-w-md w-full p-8 rounded-2xl border border-white/10 bg-slate-900/60 backdrop-blur-xl shadow-2xl relative z-10 text-center">
            <div className="login-logo-icon w-14 h-14 bg-gradient-to-br from-gold-primary to-gold-secondary rounded-xl flex items-center justify-center text-2xl font-extrabold text-bg-primary shadow-lg mx-auto mb-4">M</div>
            <h2 className="text-xl font-bold text-white mb-2">Secure Link Offline</h2>
            <p className="text-sm text-slate-300 mb-6">
              Could not establish connection to the authorization servers. The saved Clerk Publishable Key may be invalid or expired.
            </p>
            <button
              onClick={() => {
                localStorage.removeItem('VITE_CLERK_PUBLISHABLE_KEY');
                window.location.reload();
              }}
              className="w-full py-3 px-4 bg-gradient-to-r from-gold-primary to-gold-secondary hover:from-gold-secondary hover:to-gold-primary text-bg-primary font-bold rounded-lg shadow-md cursor-pointer transition-all duration-300 transform hover:-translate-y-0.5"
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
      <div className="login-container flex items-center justify-center min-h-screen bg-[#0a0e1a] relative overflow-hidden p-4">
        {/* Background Orbs */}
        <div className="orb orb-1"></div>
        <div className="orb orb-2"></div>
        <div className="orb orb-3"></div>

        <div className="login-glass-card animate-in max-w-lg w-full p-8 rounded-2xl border border-white/10 bg-slate-900/60 backdrop-blur-xl shadow-2xl relative z-10">
          <div className="login-header text-center mb-6">
            <div className="login-logo-icon w-14 h-14 bg-gradient-to-br from-gold-primary to-gold-secondary rounded-xl flex items-center justify-center text-2xl font-extrabold text-bg-primary shadow-lg mx-auto mb-4">M</div>
            <h2 className="text-2xl font-bold text-white tracking-tight mb-1">Clerk Auth Setup</h2>
            <p className="text-xs text-gold-primary font-semibold uppercase tracking-wider">Configuration Panel</p>
          </div>

          <div className="text-sm text-slate-300 space-y-4 mb-6">
            <p className="text-center">
              A valid <strong>Clerk Publishable Key</strong> is required to enable secure login for the Mini-Medallion Trading Dashboard.
            </p>
            <div className="bg-white/5 border border-white/10 rounded-lg p-4 space-y-2 text-xs">
              <h4 className="font-semibold text-white uppercase text-[10px] tracking-wider">How to configure your credentials:</h4>
              <ol className="list-decimal list-inside space-y-1 text-slate-400">
                <li>Log in to your <a href="https://dashboard.clerk.com/" target="_blank" rel="noopener noreferrer" className="text-gold-primary hover:underline font-medium">Clerk Dashboard</a>.</li>
                <li>Select your application instance (or create a new one).</li>
                <li>Go to <strong>API Keys</strong> in the sidebar, and copy the <strong>Publishable Key</strong>.</li>
                <li>Paste it below to load instantly, or set <code>VITE_CLERK_PUBLISHABLE_KEY</code> in your <code>dashboard/.env</code>.</li>
              </ol>
            </div>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded-lg text-center font-medium">
              {error}
            </div>
          )}

          <form onSubmit={handleSaveKey} className="flex flex-col gap-4">
            <div className="input-group relative">
              <input
                type="text"
                placeholder="Paste Clerk Publishable Key (pk_test_...)"
                value={inputKey}
                onChange={(e) => setInputKey(e.target.value)}
                required
                className="w-full pl-12 pr-4 py-3 bg-slate-950/80 border border-white/5 rounded-lg text-white text-sm placeholder-slate-500 focus:outline-none focus:border-gold-primary focus:ring-1 focus:ring-gold-primary/30 transition-all font-mono"
              />
              <Key className="input-icon absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
            </div>

            <button
              type="submit"
              className="w-full flex items-center justify-center gap-2 py-3 px-4 bg-gradient-to-r from-gold-primary to-gold-secondary hover:from-gold-secondary hover:to-gold-primary text-bg-primary font-bold rounded-lg shadow-md cursor-pointer transition-all duration-300 transform hover:-translate-y-0.5 active:translate-y-0"
            >
              <Save size={18} /> Apply Publishable Key
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <ClerkProvider publishableKey={clerkKey}>
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
