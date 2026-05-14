import { Routes, Route, NavLink, useLocation } from 'react-router-dom';
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

const navItems = [
  { section: 'Trading' },
  { path: '/', icon: LayoutDashboard, label: 'Overview' },
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

export default function App() {
  const location = useLocation();

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
                end={item.path === '/'}
              >
                <item.icon size={18} />
                {item.label}
              </NavLink>
            )
          )}
        </nav>

        <div className="sidebar-footer">
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
          <Route path="/" element={<Overview />} />
          <Route path="/market" element={<MarketData />} />
          <Route path="/models" element={<Models />} />
          <Route path="/risk" element={<RiskManagement />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/backtest" element={<Backtesting />} />
          <Route path="/paper-trading" element={<PaperTrading />} />
          <Route path="/execution" element={<Execution />} />
          <Route path="/infra" element={<Infrastructure />} />
          <Route path="/operations" element={<Operations />} />
        </Routes>
      </main>
    </div>
  );
}
