import { Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { useUser, useClerk, AuthenticateWithRedirectCallback } from '@clerk/react';
import { useEffect } from 'react';
import { LayoutDashboard, BarChart3, BrainCircuit, ShieldCheck, Wallet, Server, Zap, GitBranch, FlaskConical, Activity, FileText, Users } from 'lucide-react';
import Overview from './pages/Overview';
import MarketData from './pages/MarketData';
import Models from './pages/Models';
import RiskManagement from './pages/RiskManagement';
import Portfolio from './pages/Portfolio';
import Infrastructure from './pages/Infrastructure';
import Execution from './pages/Execution';
import Backtesting from './pages/Backtesting';
import PaperTrading from './pages/PaperTrading';
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
  { section: 'System' },
  { path: '/execution', icon: Zap, label: 'Execution Engine' },
  { path: '/infra', icon: Server, label: 'Infrastructure' },
  { path: '/operations', icon: Users, label: 'Team & Ops' },
];

function SsoCallbackRoute() {
  useEffect(() => {
    // #region agent log
    fetch('http://127.0.0.1:7498/ingest/0829a907-b6db-4bac-a83c-374903799449',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'edbe57'},body:JSON.stringify({sessionId:'edbe57',location:'App.jsx:SsoCallbackRoute',message:'SSO callback route mounted',data:{uses:'AuthenticateWithRedirectCallback'},timestamp:Date.now(),hypothesisId:'B'})}).catch(()=>{});
    // #endregion
  }, []);
  return (
    <AuthenticateWithRedirectCallback signUpForceRedirectUrl="/dashboard" signInForceRedirectUrl="/dashboard" />
  );
}

export default function App() {
  const { isLoaded, isSignedIn, user } = useUser();
  const { signOut } = useClerk();

  useEffect(() => {
    // #region agent log
    fetch('http://127.0.0.1:7498/ingest/0829a907-b6db-4bac-a83c-374903799449',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'edbe57'},body:JSON.stringify({sessionId:'edbe57',location:'App.jsx:auth-state',message:'Clerk auth snapshot',data:{isLoaded,isSignedIn,path:window.location.pathname},timestamp:Date.now(),hypothesisId:'C'})}).catch(()=>{});
    // #endregion
  }, [isLoaded, isSignedIn]);

  // Show a premium glassmorphic loading screen during Clerk initialization
  if (!isLoaded) {
    return (
      <div className="login-container">
        <div className="orb orb-1"></div>
        <div className="orb orb-2"></div>
        <div className="orb orb-3"></div>
        <div className="login-glass-card animate-in flex flex-col items-center justify-center py-16 max-w-md w-full rounded-2xl border border-white/10 bg-slate-900/60 backdrop-blur-xl shadow-2xl relative z-10">
          <Activity className="spin-icon animate-spin text-gold-primary mb-4" size={32} />
          <p className="text-xs text-gold-primary tracking-widest uppercase font-semibold">Initializing Secure Auth Link...</p>
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
          <div className="pb-4 mb-4 border-b border-white/5">
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-gold-glow border border-gold-border flex items-center justify-center text-gold-primary font-bold text-sm">
                  {user?.primaryEmailAddress?.emailAddress?.charAt(0).toUpperCase() || 'O'}
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="text-xs text-text-primary font-medium truncate">
                    {user?.primaryEmailAddress?.emailAddress}
                  </span>
                  <span className="text-[10px] text-text-muted">Terminal Operator</span>
                </div>
              </div>
              <button
                onClick={() => signOut()}
                className="w-full py-2 px-3 mt-1 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 hover:border-red-500/30 text-red-400 hover:text-red-300 font-semibold text-xs rounded-md transition-all cursor-pointer text-center"
              >
                Disconnect Link
              </button>
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

