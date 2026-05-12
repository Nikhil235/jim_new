import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { portfolioKPIs, tradeHistory, equityCurve } from '../data/mockData';

const TT = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="custom-tooltip">
      <div className="label">{label}</div>
      {payload.map((p, i) => <div key={i} className="value" style={{ color: p.color }}>{p.name}: ${p.value?.toLocaleString?.()}</div>)}
    </div>
  );
};

export default function Portfolio() {
  return (
    <>
      <div className="page-header">
        <h2>Portfolio</h2>
        <p>Performance tracking, equity curve & trade history</p>
      </div>
      <div className="page-body">
        <div className="kpi-grid" style={{ marginBottom: 20 }}>
          {[
            { label: 'Portfolio Value', value: `$${portfolioKPIs.portfolioValue.toLocaleString()}` },
            { label: 'Total Return', value: `+${portfolioKPIs.totalReturn}%` },
            { label: 'Total Trades', value: portfolioKPIs.totalTrades },
            { label: 'Win Rate', value: `${portfolioKPIs.winRate}%` },
            { label: 'Sharpe Ratio', value: portfolioKPIs.sharpeRatio.toFixed(2) },
          ].map((m, i) => (
            <div key={i} className="kpi-card animate-in">
              <div className="kpi-label">{m.label}</div>
              <div className="kpi-value" style={{ fontSize: 22 }}>{m.value}</div>
            </div>
          ))}
        </div>

        <div className="card animate-in" style={{ marginBottom: 16 }}>
          <div className="card-header">
            <span className="card-title">Equity Curve vs Benchmark</span>
            <span className="card-badge badge-gold">180 Days</span>
          </div>
          <ResponsiveContainer width="100%" height={320}>
            <AreaChart data={equityCurve}>
              <defs>
                <linearGradient id="eqG" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#f0b90b" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#f0b90b" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#6b7280' }} tickFormatter={v => v.slice(5)} interval={28} />
              <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} tickFormatter={v => `$${(v / 1000).toFixed(0)}k`} domain={['auto', 'auto']} />
              <Tooltip content={<TT />} />
              <Area type="monotone" dataKey="equity" stroke="#f0b90b" strokeWidth={2} fill="url(#eqG)" name="Portfolio" />
              <Area type="monotone" dataKey="benchmark" stroke="#4da6ff" strokeWidth={1.5} fill="none" name="Benchmark" strokeDasharray="4 4" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="card animate-in">
          <div className="card-header">
            <span className="card-title">Recent Trades</span>
            <span className="card-badge badge-gold">{tradeHistory.length} trades</span>
          </div>
          <table className="data-table">
            <thead>
              <tr><th>ID</th><th>Date</th><th>Side</th><th>Qty</th><th>Entry</th><th>Exit</th><th>P&L</th><th>Model</th></tr>
            </thead>
            <tbody>
              {tradeHistory.map(t => (
                <tr key={t.id}>
                  <td className="mono" style={{ fontSize: 11 }}>{t.id}</td>
                  <td style={{ fontSize: 12 }}>{t.date}</td>
                  <td><span style={{ color: t.side === 'BUY' ? 'var(--green)' : 'var(--red)', fontWeight: 600, fontSize: 12 }}>{t.side}</span></td>
                  <td className="mono">{t.qty}</td>
                  <td className="mono">${t.entry.toFixed(2)}</td>
                  <td className="mono">${t.exit.toFixed(2)}</td>
                  <td className="mono" style={{ color: t.pnl >= 0 ? 'var(--green)' : 'var(--red)', fontWeight: 600 }}>
                    {t.pnl >= 0 ? '+' : ''}${t.pnl.toFixed(2)} ({t.pnlPct >= 0 ? '+' : ''}{t.pnlPct}%)
                  </td>
                  <td><span className="card-badge badge-blue" style={{ fontSize: 10 }}>{t.model}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
