import { useState } from 'react';
import { Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { LayoutDashboard, BarChart3, BrainCircuit, ShieldCheck, Wallet, Server, Zap, GitBranch, FlaskConical, Activity, FileText, Users, Database, Menu, X, ArrowRightLeft, TrendingUp } from 'lucide-react';
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
import GoldSilverRatio from './pages/GoldSilverRatio';

const navItems = [
  { section: 'Trading' },
  { path: '/dashboard', icon: LayoutDashboard, label: 'Overview' },
  { path: '/market', icon: BarChart3, label: 'Market Data' },
  { path: '/models', icon: BrainCircuit, label: 'Models & Signals' },
  { path: '/gs-ratio', icon: ArrowRightLeft, label: 'G/S Ratio' },
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

function DashboardShell() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="app-layout">
      {/* Mobile Header */}
      <div className="mobile-header">
        <div className="mobile-logo-wrap">
          <div className="logo-icon w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold bg-gradient-to-br from-[#f0b90b] to-[#d4a20a] text-[#0a0e1a] shadow-[0_0_15px_rgba(240,185,11,0.2)]">M</div>
          <h1>Mini-Medallion</h1>
        </div>
        <button className="mobile-menu-btn" onClick={() => setIsSidebarOpen(true)}>
          <Menu size={24} />
        </button>
      </div>

      {/* Sidebar Overlay */}
      <div 
        className={`sidebar-overlay ${isSidebarOpen ? 'open' : ''}`}
        onClick={() => setIsSidebarOpen(false)}
      />

      {/* Sidebar */}
      <aside className={`sidebar ${isSidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-logo" style={{ justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div className="logo-icon">M</div>
            <div>
              <h1>Mini-Medallion</h1>
              <span>Gold Trading Engine</span>
            </div>
          </div>
          <button 
            className="mobile-menu-btn mobile-close-btn" 
            style={{ display: 'none' }} 
            onClick={() => setIsSidebarOpen(false)}
          >
            <X size={20} />
          </button>
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
                onClick={() => setIsSidebarOpen(false)}
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
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Overview />} />
          <Route path="/market" element={<MarketData />} />
          <Route path="/models" element={<Models />} />
          <Route path="/gs-ratio" element={<GoldSilverRatio />} />
          <Route path="/risk" element={<RiskManagement />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/backtest" element={<Backtesting />} />
          <Route path="/paper-trading" element={<PaperTrading />} />
          <Route path="/prediction-log" element={<PredictionLog />} />
          <Route path="/execution" element={<Execution />} />
          <Route path="/infra" element={<Infrastructure />} />
          <Route path="/operations" element={<Operations />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return <DashboardShell />;
}

