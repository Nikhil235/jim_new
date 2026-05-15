import { useState, useEffect, useCallback } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Wifi, WifiOff } from 'lucide-react';
import { fetchPaperTradingPerformance, fetchPaperTradingTrades, fetchPaperTradingStatus } from '../data/api';

const TT = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (<div className="custom-tooltip"><div className="label">{label}</div>
    {payload.map((p, i) => <div key={i} className="value" style={{ color: p.color }}>{p.name}: ${p.value?.toLocaleString?.()}</div>)}
  </div>);
};

export default function Portfolio() {
  const [live, setLive] = useState(false);
  const [perf, setPerf] = useState(null);
  const [trades, setTrades] = useState([]);
  const [eqHistory, setEqHistory] = useState([]);
  const [status, setStatus] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [p, t, s] = await Promise.all([
        fetchPaperTradingPerformance(),
        fetchPaperTradingTrades(50),
        fetchPaperTradingStatus(),
      ]);
      setPerf(p); setTrades(Array.isArray(t) ? t : []); setStatus(s); setLive(true);
      if (s?.portfolio?.total_value) {
        setEqHistory(prev => {
          const n = [...prev, { date: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), equity: s.portfolio.total_value }];
          return n.length > 300 ? n.slice(-300) : n;
        });
      }
    } catch { setLive(false); }
  }, []);

  useEffect(() => { refresh(); const t = setInterval(refresh, 5000); return () => clearInterval(t); }, [refresh]);

  if (!live) return (
    <><div className="page-header"><h2>Portfolio</h2><p>⚠ Backend offline — start the API server and paper trading engine</p></div>
    <div className="page-body"><div className="card" style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
      <WifiOff size={48} style={{ margin: '0 auto 16px', opacity: 0.3 }} /><div style={{ fontSize: 16, fontWeight: 600 }}>No Connection</div>
      <div style={{ fontSize: 12, marginTop: 8 }}>Start the API server and paper trading engine to view live portfolio data</div>
    </div></div></>
  );

  const pf = status?.portfolio || {};
  const kpis = [
    { label: 'Portfolio Value', value: `$${(pf.total_value || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}` },
    { label: 'Total Return', value: `${(pf.return_pct || 0) >= 0 ? '+' : ''}${(pf.return_pct || 0).toFixed(2)}%` },
    { label: 'Total Trades', value: perf?.num_trades || 0 },
    { label: 'Win Rate', value: `${((perf?.win_rate || 0) * 100).toFixed(1)}%` },
    { label: 'Sharpe Ratio', value: (perf?.sharpe_ratio || 0).toFixed(2) },
    { label: 'Profit Factor', value: (perf?.profit_factor || 0).toFixed(2) },
  ];

  const config = status?.config || {};

  return (<>
    <div className="page-header">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div><h2>Portfolio</h2><p>Live performance tracking, equity curve & trade history from API</p></div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '5px 12px', borderRadius: 'var(--radius-sm)', fontSize: 11, fontWeight: 600, background: 'var(--green-dim)', color: 'var(--green)', border: '1px solid rgba(0,196,140,0.3)' }}>
          <Wifi size={12} /> LIVE
        </div>
      </div>
    </div>
    <div className="page-body">
      <div className="kpi-grid" style={{ marginBottom: 20 }}>
        {kpis.map((m, i) => (<div key={i} className="kpi-card animate-in"><div className="kpi-label">{m.label}</div><div className="kpi-value" style={{ fontSize: 22 }}>{m.value}</div></div>))}
      </div>

      <div className="card animate-in" style={{ marginBottom: 16 }}>
        <div className="card-header"><span className="card-title">Live Equity Curve</span><span className="card-badge badge-green">LIVE</span></div>
        <ResponsiveContainer width="100%" height={320}>
          <AreaChart data={eqHistory}>
            <defs><linearGradient id="eqG" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#f0b90b" stopOpacity={0.3} /><stop offset="100%" stopColor="#f0b90b" stopOpacity={0} /></linearGradient></defs>
            <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#6b7280' }} interval={Math.max(1, Math.floor(eqHistory.length / 10))} />
            <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} tickFormatter={v => `$${(v / 1000).toFixed(0)}k`} domain={['auto', 'auto']} />
            <Tooltip content={<TT />} />
            <Area type="monotone" dataKey="equity" stroke="#f0b90b" strokeWidth={2} fill="url(#eqG)" name="Portfolio" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="grid-2" style={{ marginBottom: 16 }}>
        <div className="card animate-in">
          <div className="card-header"><span className="card-title">Trade History</span><span className="card-badge badge-gold">{trades.length} trades</span></div>
          <table className="data-table">
            <thead><tr><th>ID</th><th>Date</th><th>Side</th><th>Entry</th><th>Exit</th><th>P&L</th><th>Model</th></tr></thead>
            <tbody>
              {trades.slice(0, 20).map((t, i) => {
                const pnl = t.pnl || 0;
                return (<tr key={i}>
                  <td className="mono" style={{ fontSize: 11 }}>{(t.trade_id || '').toString().slice(0, 10)}</td>
                  <td style={{ fontSize: 12 }}>{t.created_at ? new Date(t.created_at).toLocaleDateString() : '—'}</td>
                  <td><span style={{ color: t.signal_type === 'LONG' ? 'var(--green)' : 'var(--red)', fontWeight: 600, fontSize: 12 }}>{t.signal_type || '—'}</span></td>
                  <td className="mono">${Number(t.entry_price || 0).toFixed(2)}</td>
                  <td className="mono">{t.exit_price ? `$${Number(t.exit_price).toFixed(2)}` : '—'}</td>
                  <td className="mono" style={{ color: pnl >= 0 ? 'var(--green)' : 'var(--red)', fontWeight: 600 }}>{pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}</td>
                  <td><span className="card-badge badge-blue" style={{ fontSize: 10 }}>{t.model_name || '—'}</span></td>
                </tr>);
              })}
            </tbody>
          </table>
        </div>

        <div className="card animate-in">
          <div className="card-header"><span className="card-title">Engine Configuration</span><span className="card-badge badge-purple">LIVE</span></div>
          <div style={{ marginTop: 4 }}>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>Active Config</div>
            {[
              ['Initial Capital', `$${(config.initial_capital || 100000).toLocaleString()}`],
              ['Kelly Fraction', config.kelly_fraction || '—'],
              ['Max Position', `${((config.max_position_pct || 0) * 100).toFixed(0)}%`],
              ['Max Daily Loss', `${((config.max_daily_loss_pct || 0) * 100).toFixed(1)}%`],
              ['Max Drawdown', `${((config.max_drawdown_pct || 0) * 100).toFixed(0)}%`],
              ['Min Confidence', `${((config.min_confidence || 0) * 100).toFixed(0)}%`],
            ].map(([k, v], i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{k}</span>
                <span className="mono" style={{ fontSize: 12, color: 'var(--text-bright)' }}>{v}</span>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 16 }}>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>Performance Metrics</div>
            {[
              ['Sharpe Ratio', (perf?.sharpe_ratio || 0).toFixed(2), (perf?.sharpe_ratio || 0) >= 2.0],
              ['Max Drawdown', `${(perf?.max_drawdown || 0).toFixed(2)}%`, Math.abs(perf?.max_drawdown || 0) < 10],
              ['Win Rate', `${((perf?.win_rate || 0) * 100).toFixed(1)}%`, (perf?.win_rate || 0) >= 0.51],
              ['Profit Factor', (perf?.profit_factor || 0).toFixed(2), (perf?.profit_factor || 0) >= 1.5],
            ].map(([k, v, pass], i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderBottom: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{k}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span className="mono" style={{ fontSize: 12, color: 'var(--text-bright)' }}>{v}</span>
                  <span style={{ fontSize: 10, color: pass ? 'var(--green)' : 'var(--red)', fontWeight: 600 }}>{pass ? '✓ PASS' : '✗ FAIL'}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  </>);
}
