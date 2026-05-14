import { Users, Calendar, GitPullRequest, AlertTriangle, BookOpen, BarChart3, CheckCircle, Clock, XCircle } from 'lucide-react';
import { teamOperations } from '../data/mockData';

const statusColor = (s) => s === 'production' ? 'var(--green)' : s === 'paper_trade' ? 'var(--gold-primary)' : s === 'review' ? 'var(--blue)' : s === 'backtest' ? 'var(--purple)' : 'var(--text-muted)';
const statusBg = (s) => s === 'production' ? 'var(--green-dim)' : s === 'paper_trade' ? 'var(--gold-glow)' : s === 'review' ? 'var(--blue-dim)' : s === 'backtest' ? 'var(--purple-dim)' : 'var(--bg-input)';
const sevColor = (s) => s === 'critical' ? 'var(--red)' : s === 'high' ? 'var(--orange)' : s === 'medium' ? 'var(--gold-primary)' : 'var(--text-muted)';

export default function Operations() {
  const ops = teamOperations;
  const rpt = ops.performanceReports;

  return (
    <>
      <div className="page-header">
        <h2>👥 Team & Operations</h2>
        <p>Phase 7 — Team management, model governance, incident tracking, operations scheduling & research catalog</p>
      </div>
      <div className="page-body">
        {/* KPI Row */}
        <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(5, 1fr)', marginBottom: 20 }}>
          {[
            { label: 'Team Members', value: ops.team.totalMembers, icon: <Users size={16} />, sub: `${ops.team.avgTenureDays}d avg tenure` },
            { label: 'Operations', value: ops.operations.totalOperations, icon: <Calendar size={16} />, sub: `${ops.operations.avgSuccessRate}% success` },
            { label: 'Governance', value: ops.governance.totalChanges, icon: <GitPullRequest size={16} />, sub: `${ops.governance.pipeline.production} in prod` },
            { label: 'Incidents', value: `${ops.incidents.unresolved}/${ops.incidents.total}`, icon: <AlertTriangle size={16} />, sub: 'Open / Total' },
            { label: 'Research Signals', value: `${ops.research.activeSignals}/${ops.research.totalSignals}`, icon: <BookOpen size={16} />, sub: `Avg Sharpe ${ops.research.avgDiscoverySharpe}` },
          ].map((k, i) => (
            <div key={i} className="kpi-card animate-in">
              <div className="kpi-label"><span style={{ width: 28, height: 28, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--gold-glow)', color: 'var(--gold-primary)' }}>{k.icon}</span> {k.label}</div>
              <div className="kpi-value">{k.value}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{k.sub}</div>
            </div>
          ))}
        </div>

        {/* Performance Reports */}
        <div className="card animate-in" style={{ marginBottom: 20 }}>
          <div className="card-header"><span className="card-title">Performance Reports</span><span className="card-badge badge-green">LIVE</span></div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
            {[['Daily', rpt.daily], ['Weekly', rpt.weekly], ['Monthly', rpt.monthly]].map(([period, d]) => (
              <div key={period} style={{ padding: 16, borderRadius: 'var(--radius-sm)', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-bright)', marginBottom: 10 }}>{period}</div>
                {[['P&L', `$${d.pnl.toLocaleString()}`], ['Trades', d.trades], ['Win Rate', `${(d.winRate * 100).toFixed(1)}%`], ['Sharpe', d.sharpe.toFixed(2)], ['Max DD', `${d.maxDD}%`]].map(([l, v], i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', fontSize: 12 }}>
                    <span style={{ color: 'var(--text-muted)' }}>{l}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: l === 'P&L' ? 'var(--green)' : 'var(--text-primary)' }}>{v}</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>

        {/* Team + Governance */}
        <div className="grid-2" style={{ marginBottom: 20 }}>
          <div className="card animate-in">
            <div className="card-header"><span className="card-title">Team Members</span><span className="card-badge badge-blue">{ops.team.totalMembers} ACTIVE</span></div>
            {ops.team.members.map((m) => (
              <div key={m.id} style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '10px 0', borderBottom: '1px solid var(--border-color)' }}>
                <div style={{ width: 36, height: 36, borderRadius: 10, background: 'linear-gradient(135deg, var(--gold-primary), var(--gold-secondary))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, fontWeight: 700, color: 'var(--bg-primary)' }}>
                  {m.name.charAt(0)}{m.name.split(' ').pop().charAt(0)}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-bright)' }}>{m.name}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{m.role} · {m.focus}</div>
                </div>
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', maxWidth: 180 }}>
                  {m.expertise.map((e, i) => (
                    <span key={i} style={{ fontSize: 9, padding: '2px 6px', borderRadius: 8, background: 'var(--bg-input)', color: 'var(--text-secondary)', fontWeight: 500 }}>{e}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="card animate-in">
            <div className="card-header"><span className="card-title">Model Governance Pipeline</span><span className="card-badge badge-purple">{ops.governance.totalChanges} CHANGES</span></div>
            {/* Pipeline visualization */}
            <div style={{ display: 'flex', gap: 6, marginBottom: 16 }}>
              {Object.entries(ops.governance.pipeline).filter(([, v]) => v > 0).map(([stage, count]) => (
                <div key={stage} style={{ flex: count, padding: '8px 6px', borderRadius: 'var(--radius-sm)', background: statusBg(stage), textAlign: 'center', minWidth: 40 }}>
                  <div style={{ fontSize: 16, fontWeight: 700, color: statusColor(stage) }}>{count}</div>
                  <div style={{ fontSize: 8, color: statusColor(stage), textTransform: 'uppercase', letterSpacing: 0.5 }}>{stage.replace('_', ' ')}</div>
                </div>
              ))}
            </div>
            <table className="data-table">
              <thead><tr><th>ID</th><th>Model</th><th>By</th><th>Sharpe</th><th>Status</th></tr></thead>
              <tbody>
                {ops.governance.recentChanges.map((c) => (
                  <tr key={c.id}>
                    <td className="mono">{c.id}</td>
                    <td style={{ fontWeight: 600 }}>{c.model}</td>
                    <td style={{ fontSize: 12 }}>{c.proposedBy}</td>
                    <td className="mono" style={{ color: c.sharpe >= 2.0 ? 'var(--green)' : 'var(--orange)' }}>{c.sharpe.toFixed(2)}</td>
                    <td><span style={{ fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 10, background: statusBg(c.status), color: statusColor(c.status), textTransform: 'uppercase' }}>{c.status.replace('_', ' ')}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Operations Schedule + Incidents */}
        <div className="grid-2" style={{ marginBottom: 20 }}>
          <div className="card animate-in">
            <div className="card-header"><span className="card-title">Scheduled Operations</span><span className="card-badge badge-gold">{ops.operations.totalOperations} OPS</span></div>
            {ops.operations.scheduled.map((op, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 0', borderBottom: '1px solid var(--border-color)' }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: op.successRate >= 99 ? 'var(--green)' : op.successRate >= 95 ? 'var(--orange)' : 'var(--red)' }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-bright)' }}>{op.name}</div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{op.responsible} · {op.duration}min · {op.frequency}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 12, fontFamily: 'var(--font-mono)', fontWeight: 600, color: op.successRate >= 99 ? 'var(--green)' : 'var(--orange)' }}>{op.successRate}%</div>
                  <div style={{ fontSize: 9, color: 'var(--text-muted)' }}>success</div>
                </div>
              </div>
            ))}
          </div>

          <div className="card animate-in">
            <div className="card-header"><span className="card-title">Incident Tracker</span>
              <span className={`card-badge ${ops.incidents.unresolved > 0 ? 'badge-orange' : 'badge-green'}`}>{ops.incidents.unresolved} OPEN</span>
            </div>
            {ops.incidents.recent.map((inc) => (
              <div key={inc.id} style={{ display: 'flex', alignItems: 'flex-start', gap: 12, padding: '10px 0', borderBottom: '1px solid var(--border-color)' }}>
                <div style={{ marginTop: 2 }}>
                  {inc.status === 'open' ? <AlertTriangle size={16} style={{ color: sevColor(inc.severity) }} /> : <CheckCircle size={16} style={{ color: 'var(--green)' }} />}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-bright)' }}>{inc.title}</span>
                    <span style={{ fontSize: 9, fontWeight: 600, padding: '2px 6px', borderRadius: 8, textTransform: 'uppercase', background: inc.severity === 'high' ? 'var(--red-dim)' : inc.severity === 'medium' ? 'var(--orange-dim)' : 'var(--bg-input)', color: sevColor(inc.severity) }}>{inc.severity}</span>
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
                    {inc.affected.join(', ')} · {new Date(inc.time).toLocaleDateString()}
                    {inc.resolution && <span style={{ color: 'var(--green)' }}> · ✓ {inc.resolution}</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Research Seminars */}
        <div className="card animate-in">
          <div className="card-header"><span className="card-title">Research & Signal Catalog</span><span className="card-badge badge-purple">{ops.research.totalSeminars} SEMINARS</span></div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
            <div style={{ padding: 16, borderRadius: 'var(--radius-sm)', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--green)', fontFamily: 'var(--font-mono)' }}>{ops.research.activeSignals}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Active Signals</div>
            </div>
            <div style={{ padding: 16, borderRadius: 'var(--radius-sm)', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--red)', fontFamily: 'var(--font-mono)' }}>{ops.research.retiredSignals}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Retired Signals</div>
            </div>
            <div style={{ padding: 16, borderRadius: 'var(--radius-sm)', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--gold-primary)', fontFamily: 'var(--font-mono)' }}>{ops.research.avgDiscoverySharpe.toFixed(2)}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Avg Discovery Sharpe</div>
            </div>
          </div>
          {ops.research.upcomingSeminars.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>Upcoming Seminars</div>
              {ops.research.upcomingSeminars.map((s, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 12px', borderRadius: 'var(--radius-sm)', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', marginBottom: 6 }}>
                  <BookOpen size={14} style={{ color: 'var(--purple)' }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-bright)' }}>{s.topic}</div>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{s.presenter} · {s.date}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
