import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, ComposedChart, Line } from 'recharts';
import { regimeData, modelMetrics, featureImportance, waveletBands, signals } from '../data/mockData';

const TT = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="custom-tooltip">
      <div className="label">{label}</div>
      {payload.map((p, i) => <div key={i} className="value" style={{ color: p.color }}>{p.name}: {p.value}</div>)}
    </div>
  );
};

export default function Models() {
  return (
    <>
      <div className="page-header">
        <h2>Models & Signals</h2>
        <p>HMM Regime Detection, Wavelet Analysis, Ensemble Performance & Signal Tracking</p>
      </div>
      <div className="page-body">
        {/* Model Stats */}
        <div className="kpi-grid" style={{ marginBottom: 20 }}>
          {[
            { label: 'HMM Accuracy', value: `${(modelMetrics.hmm.accuracy * 100).toFixed(1)}%`, sub: `${modelMetrics.hmm.regimeChanges} regime changes` },
            { label: 'Wavelet SNR', value: `+${modelMetrics.wavelet.snrImprovement} dB`, sub: `${modelMetrics.wavelet.noiseRemoved}% noise removed` },
            { label: 'Ensemble Sharpe', value: modelMetrics.ensemble.sharpe.toFixed(2), sub: `Win: ${(modelMetrics.ensemble.winRate * 100).toFixed(1)}%` },
            { label: 'LSTM Val Loss', value: modelMetrics.lstm.valLoss.toFixed(4), sub: `Epoch ${modelMetrics.lstm.epochs}/100` },
          ].map((m, i) => (
            <div key={i} className="kpi-card animate-in">
              <div className="kpi-label">{m.label}</div>
              <div className="kpi-value" style={{ fontSize: 22 }}>{m.value}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>{m.sub}</div>
            </div>
          ))}
        </div>

        <div className="grid-2" style={{ marginBottom: 16 }}>
          {/* Regime Probabilities Over Time */}
          <div className="card animate-in">
            <div className="card-header">
              <span className="card-title">Regime Probabilities (30D)</span>
              <span className={`card-badge badge-green`}>Current: {regimeData.current.toUpperCase()}</span>
            </div>
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={regimeData.history}>
                <XAxis dataKey="date" tick={{ fontSize: 9, fill: '#6b7280' }} tickFormatter={v => v.slice(8)} />
                <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} domain={[0, 1]} tickFormatter={v => `${(v * 100).toFixed(0)}%`} />
                <Tooltip content={<TT />} />
                <Area type="monotone" dataKey="bull" stackId="1" stroke="#00c48c" fill="rgba(0,196,140,0.4)" name="Bull" />
                <Area type="monotone" dataKey="sideways" stackId="1" stroke="#ff9f43" fill="rgba(255,159,67,0.4)" name="Sideways" />
                <Area type="monotone" dataKey="bear" stackId="1" stroke="#ff4d6a" fill="rgba(255,77,106,0.4)" name="Bear" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Wavelet Decomposition */}
          <div className="card animate-in">
            <div className="card-header">
              <span className="card-title">Wavelet Denoising</span>
              <span className="card-badge badge-purple">{modelMetrics.wavelet.family} — L{modelMetrics.wavelet.bands}</span>
            </div>
            <ResponsiveContainer width="100%" height={240}>
              <ComposedChart data={waveletBands.slice(-30)}>
                <XAxis dataKey="date" tick={{ fontSize: 9, fill: '#6b7280' }} tickFormatter={v => v.slice(8)} />
                <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} domain={['auto', 'auto']} />
                <Tooltip content={<TT />} />
                <Line type="monotone" dataKey="original" stroke="rgba(255,255,255,0.2)" strokeWidth={1} dot={false} name="Original" />
                <Line type="monotone" dataKey="denoised" stroke="#f0b90b" strokeWidth={2} dot={false} name="Denoised" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="grid-2">
          {/* Feature Importance */}
          <div className="card animate-in">
            <div className="card-header"><span className="card-title">Feature Importance</span></div>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={featureImportance} layout="vertical" margin={{ left: 80 }}>
                <XAxis type="number" tick={{ fontSize: 10, fill: '#6b7280' }} tickFormatter={v => `${(v * 100).toFixed(0)}%`} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: '#9ca3af' }} width={80} />
                <Tooltip content={<TT />} />
                <Bar dataKey="importance" name="Importance" fill="rgba(240,185,11,0.6)" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* All Signals */}
          <div className="card animate-in">
            <div className="card-header"><span className="card-title">Signal Log</span><span className="card-badge badge-gold">{signals.length} signals</span></div>
            <table className="data-table">
              <thead><tr><th>Time</th><th>Type</th><th>Source</th><th>Conf</th><th>Status</th></tr></thead>
              <tbody>
                {signals.map(s => (
                  <tr key={s.id}>
                    <td className="mono">{s.time}</td>
                    <td><span style={{ color: s.type === 'LONG' ? 'var(--green)' : s.type === 'SHORT' ? 'var(--red)' : 'var(--blue)', fontWeight: 600, fontSize: 12 }}>{s.type}</span></td>
                    <td style={{ fontSize: 12 }}>{s.source}</td>
                    <td className="mono">{(s.confidence * 100).toFixed(0)}%</td>
                    <td><span className={`card-badge ${s.status === 'active' ? 'badge-green' : s.status === 'filled' ? 'badge-blue' : 'badge-orange'}`}>{s.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
}
