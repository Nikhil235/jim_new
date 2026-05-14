import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, ComposedChart, Line } from 'recharts';
import { regimeData, modelMetrics, featureImportance, featureConfig, waveletBands, signals } from '../data/mockData';

const TT = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="custom-tooltip">
      <div className="label">{label}</div>
      {payload.map((p, i) => <div key={i} className="value" style={{ color: p.color }}>{p.name}: {p.value}</div>)}
    </div>
  );
};

function ModelConfigCard({ title, badge, configs }) {
  return (
    <div className="card animate-in">
      <div className="card-header">
        <span className="card-title">{title}</span>
        <span className="card-badge badge-purple">{badge}</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
        {configs.map(([k, v], i) => (
          <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid var(--border-color)' }}>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{k}</span>
            <span className="mono" style={{ fontSize: 11, color: 'var(--text-bright)' }}>{v}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Models() {
  return (
    <>
      <div className="page-header">
        <h2>Models & Signals</h2>
        <p>Phase 3 Complete — HMM, Wavelet, Genetic, LSTM, TFT & Ensemble • All 6 models validated</p>
      </div>
      <div className="page-body">
        {/* Model Stats */}
        <div className="kpi-grid" style={{ marginBottom: 20 }}>
          {[
            { label: 'HMM Accuracy', value: `${(modelMetrics.hmm.accuracy * 100).toFixed(1)}%`, sub: `${modelMetrics.hmm.regimeChanges} regime changes` },
            { label: 'Wavelet SNR', value: `+${modelMetrics.wavelet.snrImprovement} dB`, sub: `${modelMetrics.wavelet.noiseRemoved}% noise removed` },
            { label: 'Ensemble Sharpe', value: modelMetrics.ensemble.sharpe.toFixed(2), sub: `Win: ${(modelMetrics.ensemble.winRate * 100).toFixed(1)}%` },
            { label: 'LSTM Val Loss', value: modelMetrics.lstm.valLoss.toFixed(4), sub: `Epoch ${modelMetrics.lstm.epochs}/100` },
            { label: 'Genetic Best', value: modelMetrics.genetic.bestFitness.toFixed(2), sub: `Gen ${modelMetrics.genetic.generation}/500` },
            { label: 'TFT Val Loss', value: modelMetrics.tft.valLoss.toFixed(4), sub: `${modelMetrics.tft.attentionHeads} attention heads` },
          ].map((m, i) => (
            <div key={i} className="kpi-card animate-in">
              <div className="kpi-label">{m.label}</div>
              <div className="kpi-value" style={{ fontSize: 22 }}>{m.value}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>{m.sub}</div>
            </div>
          ))}
        </div>

        <div className="grid-2" style={{ marginBottom: 16 }}>
          <div className="card animate-in">
            <div className="card-header">
              <span className="card-title">Regime Probabilities (30D)</span>
              <span className="card-badge badge-green">Current: {regimeData.current}</span>
            </div>
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={regimeData.history}>
                <XAxis dataKey="date" tick={{ fontSize: 9, fill: '#6b7280' }} tickFormatter={v => v.slice(8)} />
                <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} domain={[0, 1]} tickFormatter={v => `${(v * 100).toFixed(0)}%`} />
                <Tooltip content={<TT />} />
                <Area type="monotone" dataKey="GROWTH" stackId="1" stroke="#00c48c" fill="rgba(0,196,140,0.4)" name="Growth" />
                <Area type="monotone" dataKey="NORMAL" stackId="1" stroke="#ff9f43" fill="rgba(255,159,67,0.4)" name="Normal" />
                <Area type="monotone" dataKey="CRISIS" stackId="1" stroke="#ff4d6a" fill="rgba(255,77,106,0.4)" name="Crisis" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

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

        {/* Model Architecture Configs */}
        <div className="grid-3" style={{ marginBottom: 16 }}>
          <ModelConfigCard title="HMM Regime Detector" badge="hmm_regime.py" configs={[
            ['Regimes', modelMetrics.hmm.config.nRegimes], ['Covariance', modelMetrics.hmm.config.covarianceType],
            ['Iterations', modelMetrics.hmm.config.nIter.toLocaleString()], ['Retrain', modelMetrics.hmm.config.retrainFrequency],
          ]} />
          <ModelConfigCard title="Genetic Algorithm" badge="DEAP" configs={[
            ['Population', modelMetrics.genetic.config.populationSize.toLocaleString()], ['Generations', modelMetrics.genetic.config.generations],
            ['Crossover', modelMetrics.genetic.config.crossoverProb], ['Mutation', modelMetrics.genetic.config.mutationProb],
          ]} />
          <ModelConfigCard title="TFT Network" badge="Multi-Head Attn" configs={[
            ['Hidden Size', modelMetrics.tft.config.hiddenSize], ['Attn Heads', modelMetrics.tft.config.attentionHeads],
            ['Dropout', modelMetrics.tft.config.dropout], ['Quantiles', modelMetrics.tft.config.quantiles.join(', ')],
          ]} />
        </div>

        <div className="grid-2" style={{ marginBottom: 16 }}>
          <ModelConfigCard title="LSTM Network" badge="PyTorch CUDA" configs={[
            ['Hidden Size', modelMetrics.lstm.config.hiddenSize], ['Layers', modelMetrics.lstm.config.numLayers],
            ['Bidirectional', modelMetrics.lstm.config.bidirectional ? 'Yes' : 'No'], ['Dropout', modelMetrics.lstm.config.dropout],
            ['Seq Length', modelMetrics.lstm.config.seqLength], ['Batch Size', modelMetrics.lstm.config.batchSize],
          ]} />
          <ModelConfigCard title="Ensemble Strategy" badge={modelMetrics.ensemble.config.method} configs={[
            ['Method', modelMetrics.ensemble.config.method], ['Meta-Learner', modelMetrics.ensemble.config.metaLearner],
            ['Sharpe', modelMetrics.ensemble.sharpe], ['Profit Factor', modelMetrics.ensemble.profitFactor],
          ]} />
        </div>

        <div className="grid-2">
          <div className="card animate-in">
            <div className="card-header">
              <span className="card-title">Feature Importance</span>
              <span className="card-badge badge-gold">{featureConfig.totalFeatures}+ features</span>
            </div>
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={featureImportance} layout="vertical" margin={{ left: 100 }}>
                <XAxis type="number" tick={{ fontSize: 10, fill: '#6b7280' }} tickFormatter={v => `${(v * 100).toFixed(0)}%`} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: '#9ca3af' }} width={100} />
                <Tooltip content={<TT />} />
                <Bar dataKey="importance" name="Importance" fill="rgba(240,185,11,0.6)" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

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
            <div style={{ marginTop: 16, borderTop: '1px solid var(--border-color)', paddingTop: 12 }}>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>Feature Categories</div>
              {featureConfig.categories.map((c, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', fontSize: 11 }}>
                  <span style={{ color: 'var(--text-secondary)' }}>{c.name}</span>
                  <span className="mono" style={{ color: 'var(--gold-primary)' }}>{c.count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
