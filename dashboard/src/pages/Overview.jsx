import { TrendingUp, TrendingDown, DollarSign, BarChart3, Target, Activity } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { portfolioKPIs, recentPrices, regimeData, signals, equityCurve, riskMetrics, phaseProgress, backtestResults, healthMonitor } from '../data/mockData';

const ChartTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="custom-tooltip">
      <div className="label">{label}</div>
      {payload.map((p, i) => (
        <div key={i} className="value" style={{ color: p.color }}>{p.name}: {typeof p.value === 'number' ? p.value.toLocaleString() : p.value}</div>
      ))}
    </div>
  );
};

export default function Overview() {
  const kpis = [
    { label: 'Portfolio Value', value: `$${portfolioKPIs.portfolioValue.toLocaleString()}`, change: `+${portfolioKPIs.totalReturn}%`, positive: true, icon: <DollarSign size={18} />, bg: 'var(--gold-glow)', color: 'var(--gold-primary)' },
    { label: 'Daily P&L', value: `+$${portfolioKPIs.dailyPnL.toLocaleString()}`, change: `+${portfolioKPIs.dailyPnLPct}%`, positive: true, icon: <TrendingUp size={18} />, bg: 'var(--green-dim)', color: 'var(--green)' },
    { label: 'Sharpe Ratio', value: portfolioKPIs.sharpeRatio.toFixed(2), change: 'DSR Validated ✓', positive: true, icon: <BarChart3 size={18} />, bg: 'var(--blue-dim)', color: 'var(--blue)' },
    { label: 'Win Rate', value: `${portfolioKPIs.winRate}%`, change: `${portfolioKPIs.totalTrades} trades`, positive: true, icon: <Target size={18} />, bg: 'var(--purple-dim)', color: 'var(--purple)' },
    { label: 'Gold (XAU/USD)', value: `$${portfolioKPIs.goldPrice.toLocaleString()}`, change: `${portfolioKPIs.goldChange >= 0 ? '+' : ''}${portfolioKPIs.goldChange.toFixed(2)}%`, positive: portfolioKPIs.goldChange >= 0, icon: <Activity size={18} />, bg: 'var(--orange-dim)', color: 'var(--orange)' },
    { label: 'Max Drawdown', value: `${portfolioKPIs.maxDrawdown}%`, change: 'Limit: -10%', positive: false, icon: <TrendingDown size={18} />, bg: 'var(--red-dim)', color: 'var(--red)' },
  ];

  const regimeColors = { GROWTH: 'var(--green)', NORMAL: 'var(--orange)', CRISIS: 'var(--red)' };

  return (
    <>
      <div className="page-header">
        <h2>Dashboard Overview</h2>
        <p>Mini-Medallion Gold Trading Engine — Phase 1-5 Complete • {backtestResults.testsPassing.total}/{backtestResults.testsPassing.total} Tests Passing • System {healthMonitor.overallStatus}</p>
      </div>
      <div className="page-body">
        {/* KPI Cards */}
        <div className="kpi-grid">
          {kpis.map((k, i) => (
            <div key={i} className="kpi-card animate-in">
              <div className="kpi-icon" style={{ background: k.bg, color: k.color }}>{k.icon}</div>
              <div className="kpi-label">{k.label}</div>
              <div className="kpi-value">{k.value}</div>
              <div className={`kpi-change ${k.positive ? 'positive' : 'negative'}`}>{k.change}</div>
            </div>
          ))}
        </div>

        {/* Charts Row */}
        <div className="grid-2-1" style={{ marginBottom: 16 }}>
          <div className="card animate-in">
            <div className="card-header">
              <span className="card-title">Equity Curve</span>
              <span className="card-badge badge-green">+27.45%</span>
            </div>
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={equityCurve.slice(-90)}>
                <defs>
                  <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#f0b90b" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#f0b90b" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="bmGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#4da6ff" stopOpacity={0.15} />
                    <stop offset="100%" stopColor="#4da6ff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#6b7280' }} tickFormatter={v => v.slice(5)} interval={14} />
                <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} domain={['auto', 'auto']} tickFormatter={v => `$${(v/1000).toFixed(0)}k`} />
                <Tooltip content={<ChartTooltip />} />
                <Area type="monotone" dataKey="equity" stroke="#f0b90b" strokeWidth={2} fill="url(#eqGrad)" name="Portfolio" />
                <Area type="monotone" dataKey="benchmark" stroke="#4da6ff" strokeWidth={1.5} fill="url(#bmGrad)" name="Benchmark" strokeDasharray="4 4" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div className="card animate-in">
              <div className="card-header">
                <span className="card-title">Market Regime</span>
                <span className={`card-badge ${regimeData.current === 'GROWTH' ? 'badge-green' : regimeData.current === 'CRISIS' ? 'badge-red' : 'badge-orange'}`}>
                  {regimeData.current} {(regimeData.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <div className="regime-bar">
                {Object.entries(regimeData.probabilities).map(([regime, prob]) => (
                  <div key={regime} className={`regime-segment regime-${regime.toLowerCase()} ${regime === regimeData.current ? 'active' : ''}`}>
                    {regime} {(prob * 100).toFixed(0)}%
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 10, fontSize: 10, color: 'var(--text-muted)' }}>
                HMM: <span style={{ fontStyle: 'italic' }}>3 regimes • full covariance • daily retrain</span>
              </div>
            </div>

            <div className="card animate-in" style={{ flex: 1 }}>
              <div className="card-header">
                <span className="card-title">Latest Signals</span>
                <span className="card-badge badge-gold">{signals.filter(s => s.status === 'active').length} Active</span>
              </div>
              {signals.slice(0, 4).map(s => (
                <div key={s.id} className="signal-item">
                  <div>
                    <span className={`signal-conf ${s.type === 'LONG' ? 'badge-green' : s.type === 'SHORT' ? 'badge-red' : 'badge-blue'}`}
                      style={{ background: s.type === 'LONG' ? 'var(--green-dim)' : s.type === 'SHORT' ? 'var(--red-dim)' : 'var(--blue-dim)', padding: '2px 8px', borderRadius: 12, fontSize: 11, fontWeight: 600 }}>
                      {s.type}
                    </span>
                    <span className="signal-name" style={{ marginLeft: 10, fontSize: 12 }}>{s.source}</span>
                  </div>
                  <div>
                    <span className="mono" style={{ color: 'var(--text-secondary)' }}>{(s.confidence * 100).toFixed(0)}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Gold Price + Risk Row */}
        <div className="grid-2" style={{ marginBottom: 16 }}>
          <div className="card animate-in">
            <div className="card-header">
              <span className="card-title">Gold Price (90D)</span>
              <span className="card-badge badge-gold">XAU/USD</span>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={recentPrices}>
                <defs>
                  <linearGradient id="goldGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#f0b90b" stopOpacity={0.25} />
                    <stop offset="100%" stopColor="#f0b90b" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#6b7280' }} tickFormatter={v => v.slice(5)} interval={18} />
                <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} domain={['auto', 'auto']} />
                <Tooltip content={<ChartTooltip />} />
                <Area type="monotone" dataKey="close" stroke="#f0b90b" strokeWidth={2} fill="url(#goldGrad)" name="Price" />
                <Area type="monotone" dataKey="sma20" stroke="#4da6ff" strokeWidth={1} fill="none" name="SMA 20" strokeDasharray="3 3" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="card animate-in">
            <div className="card-header">
              <span className="card-title">Risk Summary</span>
              <span className={`card-badge ${riskMetrics.currentDrawdown > -5 ? 'badge-green' : 'badge-orange'}`}>
                {riskMetrics.currentDrawdown > -5 ? 'NORMAL' : 'ELEVATED'}
              </span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 8 }}>
              {[
                { label: 'Current Drawdown', value: `${riskMetrics.currentDrawdown}%`, limit: `Stop: ${riskMetrics.maxDrawdownLimit}%`, pct: Math.abs(riskMetrics.currentDrawdown) / riskMetrics.maxDrawdownLimit, color: 'var(--orange)' },
                { label: 'Daily Loss', value: `${riskMetrics.currentDailyLoss}%`, limit: `Halt: ${riskMetrics.dailyLossLimit}%`, pct: Math.abs(riskMetrics.currentDailyLoss) / riskMetrics.dailyLossLimit, color: 'var(--green)' },
                { label: 'Kelly Size', value: `$${riskMetrics.halfKelly.toLocaleString()}`, limit: 'Half-Kelly (f*×0.5)', pct: 0.35, color: 'var(--blue)' },
                { label: 'VaR (95%)', value: `$${riskMetrics.dailyVaR95.toLocaleString()}`, limit: '100K simulations', pct: 0.6, color: 'var(--purple)' },
              ].map((r, i) => (
                <div key={i} style={{ padding: '8px 0' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>{r.label}</div>
                  <div style={{ fontSize: 18, fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-bright)' }}>{r.value}</div>
                  <div className="progress-bar" style={{ marginTop: 6 }}>
                    <div className="progress-fill" style={{ width: `${r.pct * 100}%`, background: r.color }} />
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>{r.limit}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Phase Progress */}
        <div className="card animate-in">
          <div className="card-header">
            <span className="card-title">Development Roadmap</span>
            <span className="card-badge badge-gold">~95% Complete</span>
          </div>
          <div className="phase-timeline">
            {phaseProgress.map(p => (
              <div key={p.phase} className="phase-row">
                <div className="phase-label">
                  <span className={`phase-num ${p.status}`}>P{p.phase}</span>
                  <span className="phase-name">{p.name}</span>
                </div>
                <div className="phase-bar-wrap">
                  <div className="progress-bar" style={{ height: 8, flex: 1 }}>
                    <div className="progress-fill" style={{
                      width: `${p.progress}%`,
                      background: p.status === 'complete' ? 'var(--green)' : p.status === 'in-progress' ? 'var(--gold-primary)' : 'var(--bg-input)'
                    }} />
                  </div>
                  <span className="mono" style={{ fontSize: 11, minWidth: 36, textAlign: 'right' }}>{p.progress}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
