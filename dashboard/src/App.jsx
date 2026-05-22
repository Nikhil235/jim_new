import { Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { useUser, useClerk, AuthenticateWithRedirectCallback } from '@clerk/react';
import { LayoutDashboard, BarChart3, BrainCircuit, ShieldCheck, Wallet, Server, Zap, GitBranch, FlaskConical, Activity, FileText, Users, Database } from 'lucide-react';
import Overview from './pages/Overview';
import MarketData from './pages/MarketData';
import Models from './pages/Models';
import RiskManagement from './pages/RiskManagement';
import Portfolio from './pages/Portfolio';
import Infrastructure from './pages/Infrastructure';
import Execution from './pages/Execution';
import Backtesting from './pages/Backtesting';
import PaperTrading from './pages/PaperTrading';
import PredictionLog from './pages/PredictionLog';
import Operations from './pages/Operations';
import SignIn from './pages/auth/SignIn';
import SignUp from './pages/auth/SignUp';
import ForgotPassword from './pages/auth/ForgotPassword';

const navItems = [
  { section: 'Trading' },
  { path: '/dashboard', icon: LayoutDashboard, label: 'Overview' },
  { path: '/market', icon: BarChart3, label: 'Market Data' },
  { path: '/models', icon: BrainCircuit, label: 'Models & Signals' },
  { section: 'Management' },
  { path: '/risk', icon: ShieldCheck, label: 'Risk Management' },
  { path: '/portfolio', icon: Wallet, label: 'Portfolio' },
  { path: '/backtest', icon: FlaskConical, label: 'Backtesting' },
  { path: '/paper-trading', icon: FileText, label: 'Paper Trading' },
  { path: '/prediction-log', icon: Database, label: 'Prediction Log' },
  { section: 'System' },
  { path: '/execution', icon: Zap, label: 'Execution Engine' },
  { path: '/infra', icon: Server, label: 'Infrastructure' },
  { path: '/operations', icon: Users, label: 'Team & Ops' },
];

function SsoCallbackRoute() {
  return (
    <AuthenticateWithRedirectCallback signUpForceRedirectUrl="/dashboard" signInForceRedirectUrl="/dashboard" />
  );
}

/* ── Shared sidebar + routes layout ── */
function DashboardShell({ user, onSignOut, onClearKey, hasCustomKey }) {
  return (
    <div className="app-layout">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="logo-icon">M</div>
          <div>
            <h1>Mini-Medallion</h1>
            <span>Gold Trading Engine</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          {navItems.map((item, i) =>
            item.section ? (
              <div key={i} className="nav-section-title">{item.section}</div>
            ) : (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                end={item.path === '/dashboard'}
              >
                <item.icon size={18} />
                {item.label}
              </NavLink>
            )
          )}
        </nav>

        <div className="sidebar-footer">
          {/* User Profile & Sign Out Controls */}
          <div style={{ paddingBottom: '16px', marginBottom: '16px', borderBottom: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{
                  width: '32px', height: '32px', borderRadius: '50%',
                  background: 'var(--gold-glow)', border: '1px solid var(--gold-border)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: 'var(--gold-primary)', fontWeight: 700, fontSize: '13px'
                }}>
                  {user?.primaryEmailAddress?.emailAddress?.charAt(0).toUpperCase() || 'D'}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                  <span style={{ fontSize: '12px', color: 'var(--text-primary)', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {user?.primaryEmailAddress?.emailAddress || 'developer@medallion.local'}
                  </span>
                  <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Terminal Operator</span>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '6px' }}>
                <button
                  onClick={onSignOut}
                  style={{
                    flex: 1, padding: '8px 12px', marginTop: '4px',
                    background: 'rgba(255,77,106,0.1)', border: '1px solid rgba(255,77,106,0.2)',
                    color: 'var(--red)', fontWeight: 600, fontSize: '11px',
                    borderRadius: '6px', cursor: 'pointer', textAlign: 'center',
                    transition: 'all 0.2s'
                  }}
                >
                  Disconnect Link
                </button>
                {hasCustomKey && onClearKey && (
                  <button
                    onClick={onClearKey}
                    title="Reset Clerk API Key"
                    style={{
                      padding: '8px 10px', marginTop: '4px',
                      background: 'rgba(255,159,67,0.1)', border: '1px solid rgba(255,159,67,0.2)',
                      color: 'var(--orange)', fontWeight: 600, fontSize: '11px',
                      borderRadius: '6px', cursor: 'pointer', textAlign: 'center',
                      transition: 'all 0.2s'
                    }}
                  >
                    Reset Key
                  </button>
                )}
              </div>
            </div>
          </div>

          <div className="status-badge">
            <span className="status-dot online" />
            <span>System Online — v3.0.0</span>
          </div>
          <div className="status-badge" style={{ marginTop: 6 }}>
            <Zap size={12} style={{ color: 'var(--gold-primary)' }} />
            <span>RTX 3050 • CUDA 12.1</span>
          </div>
          <div className="status-badge" style={{ marginTop: 6 }}>
            <GitBranch size={12} style={{ color: 'var(--green)' }} />
            <span>Phase 7 • 100% Complete</span>
          </div>
          <div className="status-badge" style={{ marginTop: 6 }}>
            <Activity size={12} style={{ color: 'var(--cyan)' }} />
            <span>60/60 Tests • 200+ Unit Tests</span>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Overview />} />
          <Route path="/market" element={<MarketData />} />
          <Route path="/models" element={<Models />} />
          <Route path="/risk" element={<RiskManagement />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/backtest" element={<Backtesting />} />
          <Route path="/paper-trading" element={<PaperTrading />} />
          <Route path="/prediction-log" element={<PredictionLog />} />
          <Route path="/execution" element={<Execution />} />
          <Route path="/infra" element={<Infrastructure />} />
          <Route path="/operations" element={<Operations />} />
          {/* Fallback to main dashboard for authenticated users */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </main>
    </div>
  );
}

/* ── Authenticated App (uses Clerk hooks) ── */
function AuthenticatedApp({ onClearKey, hasCustomKey }) {
  const { isLoaded, isSignedIn, user } = useUser();
  const { signOut } = useClerk();

  // Show a premium glassmorphic loading screen during Clerk initialization
  if (!isLoaded) {
    return (
      <div className="login-container">
        <div className="orb orb-1"></div>
        <div className="orb orb-2"></div>
        <div className="orb orb-3"></div>
        <div className="login-glass-card animate-in" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', paddingTop: '64px', paddingBottom: '64px' }}>
          <Activity className="spin-icon" size={32} style={{ color: 'var(--gold-primary)', marginBottom: '16px' }} />
          <p style={{ fontSize: '11px', color: 'var(--gold-primary)', letterSpacing: '2px', textTransform: 'uppercase', fontWeight: 600 }}>Initializing Secure Auth Link...</p>
        </div>
      </div>
    );
  }

  // Protect dashboard routes: Redirect to sign-in if unauthenticated
  if (!isSignedIn) {
    return (
      <Routes>
        <Route path="/sign-in" element={<SignIn />} />
        <Route path="/sign-up" element={<SignUp />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/sso-callback" element={<SsoCallbackRoute />} />
        <Route path="*" element={<Navigate to="/sign-in" replace />} />
      </Routes>
    );
  }

  return (
    <DashboardShell
      user={user}
      onSignOut={() => {
        localStorage.removeItem('AUTH_BYPASS');
        signOut();
        window.location.href = '/sign-in';
      }}
      onClearKey={onClearKey}
      hasCustomKey={hasCustomKey}
    />
  );
}

/* ── Main export: routes to bypass or authenticated app ── */
export default function App({ onClearKey, hasCustomKey }) {
  const hasBypass = localStorage.getItem('AUTH_BYPASS') === 'true';

  if (hasBypass) {
    return (
      <DashboardShell
        user={null}
        onSignOut={() => {
          localStorage.removeItem('AUTH_BYPASS');
          window.location.href = '/';
        }}
        onClearKey={onClearKey}
        hasCustomKey={hasCustomKey}
      />
    );
  }

  return <AuthenticatedApp onClearKey={onClearKey} hasCustomKey={hasCustomKey} />;
}

