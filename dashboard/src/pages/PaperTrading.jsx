import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Play, Pause, DollarSign, TrendingUp, Activity, Target, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';
import { paperTrading, stressTestData, dynamicRisk, featureDrift } from '../data/mockData';

const signalColor = (s) => s === 'LONG' ? 'var(--green)' : s === 'SHORT' ? 'var(--red)' : 'var(--text-muted)';
const signalBg = (s) => s === 'LONG' ? 'var(--green-dim)' : s === 'SHORT' ? 'var(--red-dim)' : 'var(--bg-input)';
const signalIcon = (s) => s === 'LONG' ? <ArrowUpRight size={12} /> : s === 'SHORT' ? <ArrowDownRight size={12} /> : <Minus size={12} />;

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="custom-tooltip">
      <div className="label">{label}</div>
      {payload.map((p, i) => (
        <div key={i} className="value" style={{ color: p.color }}>{p.name}: {typeof p.value === 'number' ? p.value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : p.value}</div>
      ))}
    </div>
  );
};

export default function PaperTrading() {
  const pt = paperTrading;
  const pf = pt.portfolio;

  return (
    <>
      <div className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2>📄 Paper Trading Engine</h2>
            <p>Phase 6B — Live simulated trading with 6-model signal generation, Kelly sizing & circuit breakers</p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8, padding: '8px 16px',
              background: pt.status === 'RUNNING' ? 'var(--green-dim)' : 'var(--red-dim)',
              border: `1px solid ${pt.status === 'RUNNING' ? 'rgba(0,196,140,0.3)' : 'rgba(255,77,106,0.3)'}`,
              borderRadius: 'var(--radius-sm)', fontSize: 13, fontWeight: 600,
              color: pt.status === 'RUNNING' ? 'var(--green)' : 'var(--red)',
            }}>
              {pt.status === 'RUNNING' ? <Play size={14} /> : <Pause size={14} />}
              {pt.status}
            </div>
          </div>
        </div>
      </div>

      <div className="page-body">
        {/* KPI Row */}
        <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(5, 1fr)' }}>
          {[
            { label: 'Portfolio Value', value: `$${pf.totalValue.toLocaleString()}`, change: `+${pf.returnPct}%`, positive: true, icon: <DollarSign size={16} /> },
            { label: 'Total P&L', value: `$${pf.pnlTotal.toLocaleString()}`, change: `+$${pf.dailyPnl.toLocaleString()} today`, positive: true, icon: <TrendingUp size={16} /> },
            { label: 'Win Rate', value: `${(pf.winRate * 100).toFixed(1)}%`, change: `${pf.numTrades} trades`, positive: pf.winRate > 0.5, icon: <Target size={16} /> },
            { label: 'Sharpe Ratio', value: pf.sharpeRatio.toFixed(2), change: 'Annualized', positive: pf.sharpeRatio > 1.5, icon: <Activity size={16} /> },
            { label: 'Max Drawdown', value: `${pf.maxDrawdown}%`, change: 'Peak-to-trough', positive: pf.maxDrawdown > -5, icon: <ArrowDownRight size={16} /> },
          ].map((kpi, i) => (
            <div key={i} className="kpi-card animate-in">
              <div className="kpi-label"><span style={{
                width: 28, height: 28, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: 'var(--gold-glow)', color: 'var(--gold-primary)',
              }}>{kpi.icon}</span> {kpi.label}</div>
              <div className="kpi-value">{kpi.value}</div>
              <div className={`kpi-change ${kpi.positive ? 'positive' : 'negative'}`}>{kpi.change}</div>
            </div>
          ))}
        </div>

        {/* Equity Curve + Daily P&L */}
        <div className="grid-2" style={{ marginBottom: 20 }}>
          <div className="card animate-in">
            <div className="card-header">
              <span className="card-title">Paper Trading Equity Curve</span>
              <span className="card-badge badge-green">LIVE</span>
            </div>
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={pt.equityCurve}>
                <defs>
                  <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#f0b90b" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#f0b90b" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 10 }} tickFormatter={(v) => v.slice(5)} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} domain={['dataMin - 500', 'dataMax + 500']} />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="equity" stroke="#f0b90b" fill="url(#eqGrad)" strokeWidth={2} name="Equity" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="card animate-in">
            <div className="card-header">
              <span className="card-title">Daily P&L</span>
              <span className="card-badge badge-blue">14 DAYS</span>
            </div>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={pt.dailyPnLHistory}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 10 }} tickFormatter={(v) => v.slice(5)} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} tickFormatter={(v) => `$${v}`} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="pnl" radius={[4, 4, 0, 0]} name="P&L">
                  {pt.dailyPnLHistory.map((d, i) => (
                    <Cell key={i} fill={d.pnl >= 0 ? '#00c48c' : '#ff4d6a'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Model Signals + Trade History */}
        <div className="grid-2" style={{ marginBottom: 20 }}>
          <div className="card animate-in">
            <div className="card-header">
              <span className="card-title">Model Signal Status</span>
              <span className="card-badge badge-gold">6 MODELS</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              {Object.entries(pt.modelSignals).map(([model, sig]) => (
                <div key={model} style={{
                  padding: 14, borderRadius: 'var(--radius-sm)',
                  background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-bright)', textTransform: 'capitalize' }}>{model}</span>
                    <span style={{
                      fontSize: 10, fontWeight: 700, padding: '3px 8px', borderRadius: 12,
                      background: signalBg(sig.lastSignal), color: signalColor(sig.lastSignal),
                      display: 'flex', alignItems: 'center', gap: 4,
                    }}>
                      {signalIcon(sig.lastSignal)} {sig.lastSignal}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)' }}>
                    <span>Conf: <span style={{ color: sig.confidence >= 0.7 ? 'var(--green)' : sig.confidence >= 0.6 ? 'var(--orange)' : 'var(--red)', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{(sig.confidence * 100).toFixed(0)}%</span></span>
                    <span>{sig.signalCount} signals</span>
                  </div>
                  <div style={{ marginTop: 6 }}>
                    <div className="progress-bar">
                      <div className="progress-fill" style={{
                        width: `${sig.confidence * 100}%`,
                        background: sig.confidence >= 0.7 ? 'var(--green)' : sig.confidence >= 0.6 ? 'var(--orange)' : 'var(--red)',
                      }} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="card animate-in">
            <div className="card-header">
              <span className="card-title">Recent Trades</span>
              <span className="card-badge badge-purple">{pt.recentTrades.length} TRADES</span>
            </div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th><th>Model</th><th>Signal</th><th>Entry</th><th>Exit</th><th>P&L</th><th>Status</th>
                </tr>
              </thead>
              <tbody>
                {pt.recentTrades.map((t) => (
                  <tr key={t.tradeId}>
                    <td className="mono">{t.tradeId}</td>
                    <td style={{ fontWeight: 600 }}>{t.model}</td>
                    <td><span style={{ color: signalColor(t.signal), fontWeight: 600, fontSize: 11 }}>{t.signal}</span></td>
                    <td className="mono">${t.entry.toFixed(2)}</td>
                    <td className="mono">${t.exit.toFixed(2)}</td>
                    <td className="mono" style={{ color: t.pnl >= 0 ? 'var(--green)' : 'var(--red)', fontWeight: 600 }}>
                      {t.pnl >= 0 ? '+' : ''}${t.pnl.toFixed(2)}
                    </td>
                    <td><span className={`card-badge ${t.status === 'CLOSED' ? 'badge-green' : 'badge-blue'}`}>{t.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Stress Testing + Dynamic Risk + Feature Drift */}
        <div className="grid-3" style={{ marginBottom: 20 }}>
          {/* Stress Testing Summary */}
          <div className="card animate-in">
            <div className="card-header">
              <span className="card-title">Stress Testing</span>
              <span className={`card-badge ${stressTestData.riskLevel === 'moderate' ? 'badge-orange' : stressTestData.riskLevel === 'low' ? 'badge-green' : 'badge-red'}`}>
                {stressTestData.riskLevel.toUpperCase()}
              </span>
            </div>
            <div style={{ textAlign: 'center', marginBottom: 16 }}>
              <div style={{ fontSize: 36, fontWeight: 800, fontFamily: 'var(--font-mono)', color: stressTestData.resilienceScore >= 80 ? 'var(--green)' : stressTestData.resilienceScore >= 60 ? 'var(--orange)' : 'var(--red)' }}>
                {stressTestData.resilienceScore}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Resilience Score / 100</div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-around', marginBottom: 12 }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--green)' }}>{stressTestData.scenariosPassed}</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>Passed</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--red)' }}>{stressTestData.scenariosFailed}</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>Failed</div>
              </div>
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', borderTop: '1px solid var(--border-color)', paddingTop: 10 }}>
              {stressTestData.scenarios.slice(0, 4).map((s, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
                  <span>{s.name}</span>
                  <span style={{ color: s.status === 'passed' ? 'var(--green)' : 'var(--red)', fontWeight: 600, fontSize: 10, textTransform: 'uppercase' }}>{s.status}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Dynamic Risk */}
          <div className="card animate-in">
            <div className="card-header">
              <span className="card-title">Dynamic Risk</span>
              <span className="card-badge badge-blue">REAL-TIME</span>
            </div>
            <div style={{ textAlign: 'center', marginBottom: 12 }}>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Adjusted Kelly</div>
              <div style={{ fontSize: 28, fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--gold-primary)' }}>
                {dynamicRisk.adjustment.finalKelly.toFixed(4)}
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>Base: {dynamicRisk.baseKelly.toFixed(2)}</div>
            </div>
            {[
              { label: 'Volatility', mult: dynamicRisk.adjustment.volatilityMultiplier, detail: `VIX ${dynamicRisk.volatility.vixLevel} (${dynamicRisk.volatility.regime})` },
              { label: 'Drawdown', mult: dynamicRisk.adjustment.drawdownMultiplier, detail: `${dynamicRisk.drawdown.currentDrawdownPct}% DD` },
              { label: 'Consensus', mult: dynamicRisk.adjustment.consensusMultiplier, detail: `${dynamicRisk.modelConsensus.disagreementCount}/${dynamicRisk.modelConsensus.totalModels} disagree` },
              { label: 'Correlation', mult: dynamicRisk.adjustment.correlationMultiplier, detail: dynamicRisk.correlations.status },
            ].map((item, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderBottom: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{item.label}</span>
                <div style={{ textAlign: 'right' }}>
                  <span style={{
                    fontSize: 13, fontWeight: 600, fontFamily: 'var(--font-mono)',
                    color: item.mult >= 1.0 ? 'var(--green)' : item.mult >= 0.8 ? 'var(--orange)' : 'var(--red)',
                  }}>×{item.mult.toFixed(2)}</span>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{item.detail}</div>
                </div>
              </div>
            ))}
            <div style={{ marginTop: 10, padding: '8px 10px', borderRadius: 'var(--radius-sm)', background: 'var(--bg-secondary)', fontSize: 10, color: 'var(--text-muted)' }}>
              Risk Score: <span style={{ color: dynamicRisk.adjustment.riskScore <= 3 ? 'var(--green)' : dynamicRisk.adjustment.riskScore <= 6 ? 'var(--orange)' : 'var(--red)', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>{dynamicRisk.adjustment.riskScore}/10</span>
            </div>
          </div>

          {/* Feature Drift */}
          <div className="card animate-in">
            <div className="card-header">
              <span className="card-title">Feature Drift</span>
              <span className={`card-badge ${featureDrift.driftAlerts > 0 ? 'badge-orange' : 'badge-green'}`}>
                {featureDrift.driftAlerts} ALERTS
              </span>
            </div>
            <div style={{ maxHeight: 300, overflow: 'auto' }}>
              {featureDrift.features.map((f, i) => (
                <div key={i} style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '8px 0', borderBottom: '1px solid var(--border-color)',
                }}>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 500, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>{f.name}</div>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{f.samples.toLocaleString()} samples</div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ width: 60 }}>
                      <div className="progress-bar">
                        <div className="progress-fill" style={{
                          width: `${Math.min(f.driftScore * 100, 100)}%`,
                          background: f.status === 'stable' ? 'var(--green)' : f.status === 'warning' ? 'var(--orange)' : 'var(--red)',
                        }} />
                      </div>
                    </div>
                    <span style={{
                      fontSize: 10, fontWeight: 600, padding: '2px 6px', borderRadius: 10,
                      background: f.status === 'stable' ? 'var(--green-dim)' : f.status === 'warning' ? 'var(--orange-dim)' : 'var(--red-dim)',
                      color: f.status === 'stable' ? 'var(--green)' : f.status === 'warning' ? 'var(--orange)' : 'var(--red)',
                      textTransform: 'uppercase',
                    }}>{f.status}</span>
                  </div>
                </div>
              ))}
            </div>
            {featureDrift.recentAlerts.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>Recent Alerts</div>
                {featureDrift.recentAlerts.map((a, i) => (
                  <div key={i} style={{
                    padding: '6px 8px', borderRadius: 'var(--radius-sm)', marginBottom: 4,
                    background: a.severity === 'critical' ? 'var(--red-dim)' : 'var(--orange-dim)',
                    fontSize: 10, color: a.severity === 'critical' ? 'var(--red)' : 'var(--orange)',
                  }}>
                    ⚠ {a.feature} — {a.recommendation} ({a.time})
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Config Summary */}
        <div className="card animate-in">
          <div className="card-header">
            <span className="card-title">Paper Trading Configuration</span>
            <span className="card-badge badge-gold">XAUUSD</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
            {[
              { label: 'Initial Capital', value: `$${pt.config.initialCapital.toLocaleString()}` },
              { label: 'Kelly Fraction', value: pt.config.kellyFraction.toFixed(2) },
              { label: 'Max Position %', value: `${(pt.config.maxPositionPct * 100).toFixed(0)}%` },
              { label: 'Max Daily Loss', value: `${(pt.config.maxDailyLossPct * 100).toFixed(0)}%` },
              { label: 'Max Drawdown', value: `${(pt.config.maxDrawdownPct * 100).toFixed(0)}%` },
              { label: 'Commission', value: `$${pt.config.commissionPerTrade.toFixed(2)}/trade` },
              { label: 'Slippage Model', value: pt.config.slippageModel },
              { label: 'Min Confidence', value: `${(pt.config.minConfidence * 100).toFixed(0)}%` },
            ].map((c, i) => (
              <div key={i} style={{ padding: '10px 14px', borderRadius: 'var(--radius-sm)', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5 }}>{c.label}</div>
                <div style={{ fontSize: 15, fontWeight: 600, fontFamily: 'var(--font-mono)', color: 'var(--text-bright)', marginTop: 4 }}>{c.value}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
