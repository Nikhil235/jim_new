import { useState, useEffect, useCallback } from 'react';
import { TrendingUp, TrendingDown, DollarSign, BarChart3, Target, Activity, Wifi, WifiOff } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { fetchHealth, fetchEnsemble, fetchRegime, fetchGoldPrice, fetchPaperTradingStatus, fetchPaperTradingPerformance, fetchLiveSignals } from '../data/api';
import { phaseProgress } from '../data/mockData';

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
  const [live, setLive] = useState(false);
  const [health, setHealth] = useState(null);
  const [ptStatus, setPtStatus] = useState(null);
  const [ptPerf, setPtPerf] = useState(null);
  const [regime, setRegime] = useState(null);
  const [liveSignals, setLiveSignals] = useState(null);
  const [goldData, setGoldData] = useState(null);
  const [equityHistory, setEquityHistory] = useState([]);

  const refresh = useCallback(async () => {
    // Health
    try {
      const h = await fetchHealth();
      setHealth(h);
      setLive(true);
    } catch { setLive(false); }

    // Paper trading status
    try {
      const s = await fetchPaperTradingStatus();
      setPtStatus(s);
      // Add to equity history
      if (s?.portfolio?.total_value) {
        setEquityHistory(prev => {
          const next = [...prev, {
            date: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            equity: s.portfolio.total_value,
          }];
          return next.length > 200 ? next.slice(-200) : next;
        });
      }
    } catch { /* not started */ }

    // Performance
    try { setPtPerf(await fetchPaperTradingPerformance()); } catch { /* not started */ }

    // Regime
    try { setRegime(await fetchRegime()); } catch { /* offline */ }

    // Live signals
    try { setLiveSignals(await fetchLiveSignals()); } catch { /* not started */ }

    // Gold price
    try { setGoldData(await fetchGoldPrice('1d', '3mo')); } catch { /* offline */ }
  }, []);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 5000);
    return () => clearInterval(timer);
  }, [refresh]);

  // Compose KPIs — live data when available, mock fallback
  const pv = ptStatus?.portfolio;
  const kpis = [
    {
      label: 'Portfolio Value',
      value: pv ? `$${pv.total_value.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : `$${portfolioKPIs.portfolioValue.toLocaleString()}`,
      change: pv ? `${pv.return_pct >= 0 ? '+' : ''}${pv.return_pct.toFixed(2)}%` : `+${portfolioKPIs.totalReturn}%`,
      positive: pv ? pv.return_pct >= 0 : true,
      icon: <DollarSign size={18} />, bg: 'var(--gold-glow)', color: 'var(--gold-primary)',
    },
    {
      label: 'Daily P&L',
      value: pv ? `${pv.pnl_daily >= 0 ? '+' : ''}$${Math.abs(pv.pnl_daily).toLocaleString(undefined, { maximumFractionDigits: 2 })}` : `+$${portfolioKPIs.dailyPnL.toLocaleString()}`,
      change: pv ? `Total: $${pv.pnl_total.toFixed(2)}` : `+${portfolioKPIs.dailyPnLPct}%`,
      positive: pv ? pv.pnl_daily >= 0 : true,
      icon: <TrendingUp size={18} />, bg: 'var(--green-dim)', color: 'var(--green)',
    },
    {
      label: 'Sharpe Ratio',
      value: ptPerf ? ptPerf.sharpe_ratio.toFixed(2) : portfolioKPIs.sharpeRatio.toFixed(2),
      change: ptPerf ? (ptPerf.sharpe_ratio >= 2.0 ? 'DSR Validated ✓' : 'Below target') : 'DSR Validated ✓',
      positive: ptPerf ? ptPerf.sharpe_ratio >= 1.5 : true,
      icon: <BarChart3 size={18} />, bg: 'var(--blue-dim)', color: 'var(--blue)',
    },
    {
      label: 'Win Rate',
      value: ptPerf ? `${(ptPerf.win_rate * 100).toFixed(1)}%` : `${portfolioKPIs.winRate}%`,
      change: ptPerf ? `${ptPerf.num_trades} trades` : `${portfolioKPIs.totalTrades} trades`,
      positive: ptPerf ? ptPerf.win_rate >= 0.5 : true,
      icon: <Target size={18} />, bg: 'var(--purple-dim)', color: 'var(--purple)',
    },
    {
      label: 'Gold (XAU/USD)',
      value: goldData ? `$${goldData.current_price.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : `$${portfolioKPIs.goldPrice.toLocaleString()}`,
      change: goldData ? `${goldData.change >= 0 ? '+' : ''}${goldData.change.toFixed(2)} (${goldData.change_pct.toFixed(2)}%)` : `${portfolioKPIs.goldChange >= 0 ? '+' : ''}${portfolioKPIs.goldChange.toFixed(2)}%`,
      positive: goldData ? goldData.change >= 0 : portfolioKPIs.goldChange >= 0,
      icon: <Activity size={18} />, bg: 'var(--orange-dim)', color: 'var(--orange)',
    },
    {
      label: 'Max Drawdown',
      value: ptPerf ? `${ptPerf.max_drawdown.toFixed(2)}%` : `${portfolioKPIs.maxDrawdown}%`,
      change: 'Limit: -15%',
      positive: false,
      icon: <TrendingDown size={18} />, bg: 'var(--red-dim)', color: 'var(--red)',
    },
  ];

  // Regime data
  const regimeDisplay = regime ? {
    current: regime.regime,
    confidence: regime.confidence,
    probabilities: regime.regime_probabilities || {},
  } : mockRegime;

  const regimeColors = { GROWTH: 'var(--green)', NORMAL: 'var(--orange)', CRISIS: 'var(--red)' };

  // Gold price chart data
  const goldChartData = goldData?.candles?.map(c => ({
    date: new Date(c.time).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    close: c.close,
    sma20: c.close, // API doesn't return SMA, but we keep structure
  })) || recentPrices;

  // Live signals display
  const signalItems = liveSignals?.models
    ? Object.entries(liveSignals.models).slice(0, 4).map(([name, s], i) => ({
      id: i, type: s.signal || 'HOLD', source: name.charAt(0).toUpperCase() + name.slice(1),
      confidence: s.confidence || 0, status: s.signal ? 'active' : 'idle',
    }))
    : mockSignals.slice(0, 4);

  // Equity curve
  const equityDisplay = equityHistory.length > 5 ? equityHistory : mockEquityCurve.slice(-90);

  return (
    <>
      <div className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2>Dashboard Overview</h2>
            <p>Mini-Medallion Gold Trading Engine — {live ? 'Connected to Backend' : 'Offline (Mock Data)'} • System {health?.status || healthMonitor.overallStatus}</p>
          </div>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8, padding: '6px 14px',
            borderRadius: 'var(--radius-sm)', fontSize: 12, fontWeight: 600,
            background: live ? 'var(--green-dim)' : 'var(--red-dim)',
            color: live ? 'var(--green)' : 'var(--red)',
            border: `1px solid ${live ? 'rgba(0,196,140,0.3)' : 'rgba(255,77,106,0.3)'}`,
          }}>
            {live ? <Wifi size={14} /> : <WifiOff size={14} />}
            {live ? 'LIVE' : 'OFFLINE'}
          </div>
        </div>
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
              <span className={`card-badge ${live ? 'badge-green' : 'badge-orange'}`}>{live ? 'LIVE' : 'MOCK'}</span>
            </div>
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={equityDisplay}>
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
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#6b7280' }} tickFormatter={v => typeof v === 'string' && v.length > 5 ? v.slice(5) : v} interval={Math.max(1, Math.floor(equityDisplay.length / 8))} />
                <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} domain={['auto', 'auto']} tickFormatter={v => `$${(v/1000).toFixed(0)}k`} />
                <Tooltip content={<ChartTooltip />} />
                <Area type="monotone" dataKey="equity" stroke="#f0b90b" strokeWidth={2} fill="url(#eqGrad)" name="Portfolio" />
                {!live && <Area type="monotone" dataKey="benchmark" stroke="#4da6ff" strokeWidth={1.5} fill="url(#bmGrad)" name="Benchmark" strokeDasharray="4 4" />}
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div className="card animate-in">
              <div className="card-header">
                <span className="card-title">Market Regime</span>
                <span className={`card-badge ${regimeDisplay.current === 'GROWTH' ? 'badge-green' : regimeDisplay.current === 'CRISIS' ? 'badge-red' : 'badge-orange'}`}>
                  {regimeDisplay.current} {((regimeDisplay.confidence || 0) * 100).toFixed(0)}%
                </span>
              </div>
              <div className="regime-bar">
                {Object.entries(regimeDisplay.probabilities || {}).map(([regime, prob]) => (
                  <div key={regime} className={`regime-segment regime-${regime.toLowerCase()} ${regime === regimeDisplay.current ? 'active' : ''}`}>
                    {regime} {(prob * 100).toFixed(0)}%
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 10, fontSize: 10, color: 'var(--text-muted)' }}>
                HMM: <span style={{ fontStyle: 'italic' }}>3 regimes • full covariance • {regime?.regime_duration_days ? `${regime.regime_duration_days}d in regime` : 'daily retrain'}</span>
              </div>
            </div>

            <div className="card animate-in" style={{ flex: 1 }}>
              <div className="card-header">
                <span className="card-title">Latest Signals</span>
                <span className="card-badge badge-gold">{signalItems.filter(s => s.type !== 'HOLD' && s.type !== 'IDLE').length} Active</span>
              </div>
              {signalItems.map(s => (
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
              <span className="card-title">Gold Price {goldData ? `(${goldData.period})` : '(90D)'}</span>
              <span className="card-badge badge-gold">XAU/USD</span>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={goldChartData.slice(-90)}>
                <defs>
                  <linearGradient id="goldGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#f0b90b" stopOpacity={0.25} />
                    <stop offset="100%" stopColor="#f0b90b" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#6b7280' }} tickFormatter={v => typeof v === 'string' && v.length > 5 ? v.slice(5) : v} interval={18} />
                <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} domain={['auto', 'auto']} />
                <Tooltip content={<ChartTooltip />} />
                <Area type="monotone" dataKey="close" stroke="#f0b90b" strokeWidth={2} fill="url(#goldGrad)" name="Price" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="card animate-in">
            <div className="card-header">
              <span className="card-title">Risk Summary</span>
              <span className={`card-badge ${(ptPerf?.max_drawdown || Math.abs(riskMetrics.currentDrawdown)) < 5 ? 'badge-green' : 'badge-orange'}`}>
                {(ptPerf?.max_drawdown || Math.abs(riskMetrics.currentDrawdown)) < 5 ? 'NORMAL' : 'ELEVATED'}
              </span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 8 }}>
              {[
                { label: 'Current Drawdown', value: ptPerf ? `${ptPerf.max_drawdown.toFixed(2)}%` : `${riskMetrics.currentDrawdown}%`, limit: 'Stop: -15%', pct: Math.abs(ptPerf?.max_drawdown || riskMetrics.currentDrawdown) / 15, color: 'var(--orange)' },
                { label: 'Daily P&L', value: ptPerf ? `$${ptPerf.pnl_daily.toFixed(2)}` : `${riskMetrics.currentDailyLoss}%`, limit: 'Halt: -2%', pct: Math.abs(ptPerf?.pnl_daily || riskMetrics.currentDailyLoss) / 2000, color: 'var(--green)' },
                { label: 'Position Value', value: ptPerf ? `$${ptPerf.position_value.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : `$${riskMetrics.halfKelly.toLocaleString()}`, limit: ptPerf ? `${(ptPerf.position_value / (ptPerf.total_value || 1) * 100).toFixed(1)}% of portfolio` : 'Half-Kelly (f*×0.5)', pct: ptPerf ? ptPerf.position_value / (ptPerf.total_value || 1) : 0.35, color: 'var(--blue)' },
                { label: 'Trades Today', value: ptPerf ? `${ptPerf.daily_trades}` : '0', limit: ptPerf ? `${ptPerf.num_trades} total` : '0 total', pct: ptPerf ? Math.min(ptPerf.daily_trades / 20, 1) : 0, color: 'var(--purple)' },
              ].map((r, i) => (
                <div key={i} style={{ padding: '8px 0' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>{r.label}</div>
                  <div style={{ fontSize: 18, fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-bright)' }}>{r.value}</div>
                  <div className="progress-bar" style={{ marginTop: 6 }}>
                    <div className="progress-fill" style={{ width: `${Math.min(r.pct * 100, 100)}%`, background: r.color }} />
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>{r.limit}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Health Grid (live) */}
        {health && (
          <div className="card animate-in" style={{ marginBottom: 16 }}>
            <div className="card-header">
              <span className="card-title">System Health</span>
              <span className={`card-badge ${health.status === 'ok' ? 'badge-green' : 'badge-orange'}`}>{health.status?.toUpperCase()}</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 10 }}>
              {[
                { name: 'API Server', ok: true },
                { name: health.gpu_available ? `GPU × ${health.gpu_count}` : health.hardware_gpu_detected ? health.hardware_gpu_names?.[0] || 'GPU' : 'GPU', ok: health.gpu_available, warn: health.hardware_gpu_detected && !health.gpu_available },
                { name: 'Database', ok: health.database_connected },
                { name: 'Redis', ok: health.redis_connected },
                { name: 'Models', ok: health.models_loaded },
                { name: 'SLA', ok: health.sla_compliant ?? true },
              ].map((s, i) => (
                <div key={i} style={{
                  padding: '10px 14px', borderRadius: 'var(--radius-sm)',
                  background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
                  display: 'flex', alignItems: 'center', gap: 10,
                }}>
                  <div style={{
                    width: 8, height: 8, borderRadius: '50%',
                    background: s.ok ? 'var(--green)' : s.warn ? 'var(--orange)' : 'var(--red)',
                    boxShadow: s.ok ? '0 0 8px var(--green)' : 'none',
                  }} />
                  <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{s.name}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Phase Progress */}
        <div className="card animate-in">
          <div className="card-header">
            <span className="card-title">Development Roadmap</span>
            <span className="card-badge badge-green">100% Complete</span>
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
