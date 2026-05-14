import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { riskMetrics, advancedRiskMetrics, metaLabeler, gpuVaR, positionManager } from '../data/mockData';

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
        <p>Phase 4-6C Complete — Circuit breakers, Dynamic Kelly, GPU VaR, Meta-Labeler, Stress Testing & Dynamic Risk Adjustment</p>
      </div>
      <div className="page-body">
        <div className="kpi-grid" style={{ marginBottom: 20 }}>
          {[
            { label: 'Kelly Position', value: `$${riskMetrics.halfKelly.toLocaleString()}`, sub: 'Half-Kelly (f*×0.5)' },
            { label: 'VaR (95%)', value: `$${gpuVaR.var95.toLocaleString()}`, sub: `${gpuVaR.scenariosRan.toLocaleString()} sims • ${gpuVaR.computeTimeMs}ms` },
            { label: 'CVaR (99%)', value: `$${gpuVaR.cvar99.toLocaleString()}`, sub: 'Expected Shortfall' },
            { label: 'Omega Ratio', value: advancedRiskMetrics.omegaRatio.toFixed(2), sub: '> 1 is good' },
            { label: 'Critic Accuracy', value: `${(metaLabeler.valAccuracy * 100).toFixed(0)}%`, sub: `Threshold: ${(metaLabeler.threshold * 100)}%` },
            { label: 'Open Positions', value: positionManager.openPositions.length, sub: `Max: ${positionManager.maxPositions}` },
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
            <CircuitBreaker name="Daily Loss → Halt Trading" status={riskMetrics.circuitBreakers.dailyLoss.status} value={riskMetrics.circuitBreakers.dailyLoss.value} limit={riskMetrics.circuitBreakers.dailyLoss.limit} />
            <CircuitBreaker name="Drawdown → Stop All" status={riskMetrics.circuitBreakers.drawdown.status} value={riskMetrics.circuitBreakers.drawdown.value} limit={riskMetrics.circuitBreakers.drawdown.limit} />
            <CircuitBreaker name="Drawdown → Reduce 50%" status={riskMetrics.circuitBreakers.drawdownReduce.status} value={riskMetrics.circuitBreakers.drawdownReduce.value} limit={riskMetrics.circuitBreakers.drawdownReduce.limit} />
            <CircuitBreaker name="Model Disagreement" status={riskMetrics.circuitBreakers.modelDisagreement.status} value={riskMetrics.circuitBreakers.modelDisagreement.value} limit={riskMetrics.circuitBreakers.modelDisagreement.limit} unit="" />
            <CircuitBreaker name="Data Feed Latency" status={riskMetrics.circuitBreakers.latency.status} value={riskMetrics.circuitBreakers.latency.value} limit={riskMetrics.circuitBreakers.latency.limit} unit="ms" />
          </div>

          {/* Monte Carlo */}
          <div className="card animate-in">
            <div className="card-header">
              <span className="card-title">Monte Carlo Simulation</span>
              <span className="card-badge badge-purple">{riskMetrics.monteCarlo.nSimulations.toLocaleString()} sims</span>
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

        <div className="grid-2" style={{ marginBottom: 16 }}>
          {/* Meta-Labeler (Critic Model) */}
          <div className="card animate-in">
            <div className="card-header">
              <span className="card-title">Meta-Labeler (Critic Model)</span>
              <span className="card-badge badge-purple">XGBoost</span>
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 12, padding: 10, background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', fontFamily: 'var(--font-mono)' }}>
              "We don't predict the market, we predict our own accuracy." — Trader → Critic → Execute/Skip
            </div>
            <table className="data-table">
              <thead><tr><th>Signal</th><th>Trader</th><th>Critic</th><th>Decision</th><th>Regime</th></tr></thead>
              <tbody>
                {metaLabeler.recentDecisions.map((d, i) => (
                  <tr key={i}>
                    <td><span style={{ color: d.signal === 'LONG' ? 'var(--green)' : d.signal === 'SHORT' ? 'var(--red)' : 'var(--blue)', fontWeight: 600, fontSize: 12 }}>{d.signal}</span></td>
                    <td className="mono">{(d.traderConf * 100).toFixed(0)}%</td>
                    <td className="mono" style={{ color: d.criticConf >= metaLabeler.threshold ? 'var(--green)' : 'var(--red)' }}>{(d.criticConf * 100).toFixed(0)}%</td>
                    <td><span className={`card-badge ${d.execute ? 'badge-green' : 'badge-red'}`}>{d.execute ? 'EXECUTE' : 'SKIP'}</span></td>
                    <td style={{ fontSize: 11 }}>{d.regime}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Advanced Risk Metrics */}
          <div className="card animate-in">
            <div className="card-header">
              <span className="card-title">Advanced Risk Metrics</span>
              <span className="card-badge badge-blue">PHASE 4</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 8 }}>
              {[
                { label: 'Omega Ratio', value: advancedRiskMetrics.omegaRatio.toFixed(2), good: advancedRiskMetrics.omegaRatio > 1.5 },
                { label: 'Ulcer Index', value: advancedRiskMetrics.ulcerIndex.toFixed(2), good: advancedRiskMetrics.ulcerIndex < 5 },
                { label: 'CVaR (95%)', value: `${advancedRiskMetrics.conditionalVaR.toFixed(2)}%`, good: true },
                { label: 'Expected Shortfall', value: advancedRiskMetrics.expectedShortfall.toFixed(4), good: true },
                { label: 'Tail Ratio', value: advancedRiskMetrics.tailRatio.toFixed(2), good: advancedRiskMetrics.tailRatio > 1 },
                { label: 'Recovery Factor', value: advancedRiskMetrics.recoveryFactor.toFixed(2), good: advancedRiskMetrics.recoveryFactor > 2 },
                { label: 'Stress-Adj Sharpe', value: advancedRiskMetrics.stressAdjustedSharpe.toFixed(2), good: advancedRiskMetrics.stressAdjustedSharpe > 2 },
              ].map((m, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border-color)' }}>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{m.label}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-bright)' }}>{m.value}</span>
                    <span style={{ fontSize: 10, color: m.good ? 'var(--green)' : 'var(--orange)' }}>{m.good ? '✓' : '~'}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="grid-2" style={{ marginBottom: 16 }}>
          {/* Position Manager */}
          <div className="card animate-in">
            <div className="card-header">
              <span className="card-title">Position Manager</span>
              <span className="card-badge badge-gold">{positionManager.openPositions.length} Open</span>
            </div>
            <table className="data-table">
              <thead><tr><th>ID</th><th>Dir</th><th>Size</th><th>Entry</th><th>P&L</th><th>Status</th></tr></thead>
              <tbody>
                {positionManager.openPositions.map(p => (
                  <tr key={p.id}>
                    <td className="mono" style={{ fontSize: 11 }}>{p.id}</td>
                    <td><span style={{ color: p.direction > 0 ? 'var(--green)' : 'var(--red)', fontWeight: 600 }}>{p.direction > 0 ? 'LONG' : 'SHORT'}</span></td>
                    <td className="mono">{p.size}</td>
                    <td className="mono">${p.entryPrice.toFixed(2)}</td>
                    <td className="mono" style={{ color: p.currentPnl >= 0 ? 'var(--green)' : 'var(--red)' }}>{p.currentPnl >= 0 ? '+' : ''}${p.currentPnl.toFixed(2)}</td>
                    <td><span className="card-badge badge-gold">{p.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 12, marginTop: 12, borderTop: '1px solid var(--border-color)', paddingTop: 12 }}>
              {[
                ['Win Rate', `${(positionManager.stats.winRate * 100).toFixed(1)}%`],
                ['Total P&L', `$${positionManager.stats.totalPnl.toLocaleString()}`],
                ['Profit Factor', positionManager.stats.profitFactor.toFixed(2)],
              ].map(([k, v], i) => (
                <div key={i} style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{k}</div>
                  <div className="mono" style={{ fontSize: 16, fontWeight: 700, color: 'var(--gold-primary)' }}>{v}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Stress Tests */}
          <div className="card animate-in">
            <div className="card-header">
              <span className="card-title">GPU Stress Test Scenarios</span>
              <span className="card-badge badge-orange">{gpuVaR.usedGPU ? 'GPU' : 'CPU'} MODE</span>
            </div>
            <table className="data-table">
              <thead><tr><th>Scenario</th><th>P&L Impact</th><th>% Impact</th></tr></thead>
              <tbody>
                {advancedRiskMetrics.stressTests.map((s, i) => (
                  <tr key={i}>
                    <td style={{ fontSize: 12 }}>{s.name}</td>
                    <td className="mono" style={{ color: s.impact >= 0 ? 'var(--green)' : 'var(--red)', fontWeight: 600 }}>
                      {s.impact >= 0 ? '+' : ''}${s.impact.toLocaleString()}
                    </td>
                    <td className="mono" style={{ color: s.pctImpact >= 0 ? 'var(--green)' : 'var(--red)' }}>
                      {s.pctImpact >= 0 ? '+' : ''}{s.pctImpact.toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginTop: 12, borderTop: '1px solid var(--border-color)', paddingTop: 12 }}>
              {[
                ['VaR 95%', `$${gpuVaR.var95.toLocaleString()}`],
                ['VaR 99%', `$${gpuVaR.var99.toLocaleString()}`],
                ['Scenarios', gpuVaR.scenariosRan.toLocaleString()],
                ['Compute', `${gpuVaR.computeTimeMs}ms`],
              ].map(([k, v], i) => (
                <div key={i} style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{k}</div>
                  <div className="mono" style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-bright)' }}>{v}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Kelly Criterion */}
        <div className="card animate-in">
          <div className="card-header"><span className="card-title">Dynamic Kelly Criterion — Regime-Aware Position Sizing</span></div>
          <div style={{ padding: 12, background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
            f* = (p × b − q) / b &nbsp;&nbsp;→&nbsp;&nbsp; Growth: f* × 0.65 &nbsp;|&nbsp; Normal: f* × 0.50 &nbsp;|&nbsp; Crisis: f* × 0.25
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5,1fr)', gap: 20 }}>
            {[
              { label: 'Full Kelly %', value: `${(riskMetrics.kellyFraction * 100).toFixed(2)}%` },
              { label: 'Half Kelly $', value: `$${riskMetrics.halfKelly.toLocaleString()}` },
              { label: 'Crisis Kelly $', value: `$${riskMetrics.quarterKelly.toLocaleString()}` },
              { label: 'Max Position', value: `${(riskMetrics.kellyConfig.maxPositionPct * 100).toFixed(0)}%` },
              { label: 'Stops', value: `${positionManager.trailingStopPct}% trail` },
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
