import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { riskMetrics } from '../data/mockData';

const TT = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="custom-tooltip">
      <div className="label">{label}</div>
      {payload.map((p, i) => <div key={i} className="value" style={{ color: p.color }}>{p.name}: {p.value}</div>)}
    </div>
  );
};

function CircuitBreaker({ name, status, value, limit, unit = '%' }) {
  const pct = Math.min(Math.abs(value / limit) * 100, 100);
  const color = status === 'ok' ? 'var(--green)' : status === 'warning' ? 'var(--orange)' : 'var(--red)';
  return (
    <div style={{ padding: '14px 0', borderBottom: '1px solid var(--border-color)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
        <span style={{ fontSize: 13, fontWeight: 500 }}>{name}</span>
        <span style={{ fontSize: 12, fontWeight: 600, color }}>{status.toUpperCase()}</span>
      </div>
      <div className="progress-bar" style={{ height: 8 }}>
        <div className="progress-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
        <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>Current: {value}{unit}</span>
        <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>Limit: {limit}{unit}</span>
      </div>
    </div>
  );
}

export default function RiskManagement() {
  const mcReturns = riskMetrics.monteCarloResults.map(r => ({ ...r, fill: r.return >= 0 ? 'rgba(0,196,140,0.5)' : 'rgba(255,77,106,0.5)' }));

  return (
    <>
      <div className="page-header">
        <h2>Risk Management</h2>
        <p>Circuit breakers, Kelly sizing, VaR analysis & Monte Carlo simulation</p>
      </div>
      <div className="page-body">
        <div className="kpi-grid" style={{ marginBottom: 20 }}>
          {[
            { label: 'Kelly Position', value: `$${riskMetrics.halfKelly.toLocaleString()}`, sub: 'Half-Kelly' },
            { label: 'VaR (95%)', value: `$${riskMetrics.dailyVaR95.toLocaleString()}`, sub: 'Daily' },
            { label: 'CVaR (99%)', value: `$${riskMetrics.cvar99.toLocaleString()}`, sub: 'Expected Shortfall' },
            { label: 'Drawdown', value: `${riskMetrics.currentDrawdown}%`, sub: `Limit: ${riskMetrics.maxDrawdownLimit}%` },
          ].map((m, i) => (
            <div key={i} className="kpi-card animate-in">
              <div className="kpi-label">{m.label}</div>
              <div className="kpi-value" style={{ fontSize: 22 }}>{m.value}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>{m.sub}</div>
            </div>
          ))}
        </div>

        <div className="grid-2" style={{ marginBottom: 16 }}>
          {/* Circuit Breakers */}
          <div className="card animate-in">
            <div className="card-header">
              <span className="card-title">Circuit Breakers</span>
              <span className="card-badge badge-green">ALL CLEAR</span>
            </div>
            <CircuitBreaker name="Daily Loss" status={riskMetrics.circuitBreakers.dailyLoss.status} value={riskMetrics.circuitBreakers.dailyLoss.value} limit={riskMetrics.circuitBreakers.dailyLoss.limit} />
            <CircuitBreaker name="Max Drawdown" status={riskMetrics.circuitBreakers.drawdown.status} value={riskMetrics.circuitBreakers.drawdown.value} limit={riskMetrics.circuitBreakers.drawdown.limit} />
            <CircuitBreaker name="Model Disagreement" status={riskMetrics.circuitBreakers.modelDisagreement.status} value={riskMetrics.circuitBreakers.modelDisagreement.value} limit={riskMetrics.circuitBreakers.modelDisagreement.limit} unit="" />
            <CircuitBreaker name="Data Latency" status={riskMetrics.circuitBreakers.latency.status} value={riskMetrics.circuitBreakers.latency.value} limit={riskMetrics.circuitBreakers.latency.limit} unit="ms" />
          </div>

          {/* Monte Carlo */}
          <div className="card animate-in">
            <div className="card-header">
              <span className="card-title">Monte Carlo Simulation</span>
              <span className="card-badge badge-purple">50 scenarios</span>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={mcReturns.sort((a, b) => a.return - b.return)}>
                <XAxis tick={false} />
                <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} tickFormatter={v => `${v}%`} />
                <Tooltip content={<TT />} />
                <Bar dataKey="return" name="Return %">
                  {mcReturns.sort((a, b) => a.return - b.return).map((d, i) => (
                    <Cell key={i} fill={d.return >= 0 ? 'rgba(0,196,140,0.6)' : 'rgba(255,77,106,0.6)'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Kelly Criterion Details */}
        <div className="card animate-in">
          <div className="card-header"><span className="card-title">Kelly Criterion Sizing</span></div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 20, padding: '8px 0' }}>
            {[
              { label: 'Full Kelly %', value: `${(riskMetrics.kellyFraction * 100).toFixed(2)}%` },
              { label: 'Half Kelly %', value: `${(riskMetrics.kellyFraction * 50).toFixed(2)}%` },
              { label: 'Full Kelly $', value: `$${riskMetrics.kellyPositionSize.toLocaleString()}` },
              { label: 'Half Kelly $', value: `$${riskMetrics.halfKelly.toLocaleString()}` },
            ].map((k, i) => (
              <div key={i} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>{k.label}</div>
                <div className="mono" style={{ fontSize: 20, fontWeight: 700, color: 'var(--gold-primary)' }}>{k.value}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
