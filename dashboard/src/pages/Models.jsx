import { useState, useEffect, useCallback } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, ComposedChart, Line, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts';
import { Wifi, WifiOff, Radio, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';
import { fetchLiveSignals, fetchInferenceStatus, fetchModels, fetchRegime } from '../data/api';
import { regimeData, modelMetrics, featureImportance, featureConfig } from '../data/mockData';

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

const modelIcons = { wavelet: '🌊', hmm: '📊', lstm: '🧠', tft: '⚡', genetic: '🧬', nlp: '📰', ensemble: '🎯' };
const modelColors = { wavelet: '#3b82f6', hmm: '#a855f7', lstm: '#06b6d4', tft: '#f59e0b', genetic: '#22c55e', nlp: '#ec4899', ensemble: '#ef4444' };
const signalColor = (s) => s === 'LONG' ? 'var(--green)' : s === 'SHORT' ? 'var(--red)' : 'var(--text-muted)';
const signalBg = (s) => s === 'LONG' ? 'var(--green-dim)' : s === 'SHORT' ? 'var(--red-dim)' : 'var(--bg-input)';

export default function Models() {
  const [live, setLive] = useState(false);
  const [liveSignals, setLiveSignals] = useState(null);
  const [inferenceStatus, setInferenceStatus] = useState(null);
  const [liveRegime, setLiveRegime] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [signals, infStatus] = await Promise.all([
        fetchLiveSignals(),
        fetchInferenceStatus(),
      ]);
      setLiveSignals(signals);
      setInferenceStatus(infStatus);
      setLive(true);
    } catch {
      setLive(false);
    }

    try { setLiveRegime(await fetchRegime()); } catch { /* offline */ }
  }, []);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 10000); // every 10s
    return () => clearInterval(timer);
  }, [refresh]);

  // Build model data
  const models = liveSignals?.models || null;
  const goldPrice = liveSignals?.current_price || 0;
  const inferenceRunning = liveSignals?.inference_running || false;
  const iteration = liveSignals?.iteration || 0;

  // Radar chart data
  const radarData = models
    ? Object.entries(models).map(([name, d]) => ({ model: name, confidence: (d.confidence || 0) * 100 }))
    : Object.entries(modelMetrics).map(([name, d]) => ({
      model: name, confidence: name === 'ensemble' ? (d.winRate || 0) * 100 : (d.accuracy || d.winRate || 0.6) * 100,
    }));

  // Signal log — from live signals or mock
  const signalLog = models
    ? Object.entries(models).map(([name, d], i) => ({
      id: i + 1,
      time: d.last_updated ? new Date(d.last_updated).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '--:--:--',
      type: d.signal || 'HOLD',
      source: name.charAt(0).toUpperCase() + name.slice(1),
      confidence: d.confidence || 0,
      status: d.signal && d.signal !== 'HOLD' ? 'active' : 'idle',
    }))
    : [];

  return (
    <>
      <div className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2>Models & Signals</h2>
            <p>Phase 3 Complete — HMM, Wavelet, Genetic, LSTM, TFT & Ensemble • {live ? 'Live Inference Active' : 'Offline (Static Data)'}</p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {inferenceRunning && (
              <div style={{
                display: 'flex', alignItems: 'center', gap: 6, padding: '5px 12px',
                borderRadius: 'var(--radius-sm)', fontSize: 11, fontWeight: 600,
                background: 'var(--green-dim)', color: 'var(--green)',
                border: '1px solid rgba(0,196,140,0.3)', animation: 'pulse 2s infinite',
              }}>
                <Radio size={12} /> LIVE — iter #{iteration}
              </div>
            )}
            <div style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '5px 12px',
              borderRadius: 'var(--radius-sm)', fontSize: 11, fontWeight: 600,
              background: live ? 'var(--green-dim)' : 'var(--red-dim)',
              color: live ? 'var(--green)' : 'var(--red)',
              border: `1px solid ${live ? 'rgba(0,196,140,0.3)' : 'rgba(255,77,106,0.3)'}`,
            }}>
              {live ? <Wifi size={12} /> : <WifiOff size={12} />}
              {live ? 'CONNECTED' : 'OFFLINE'}
            </div>
          </div>
        </div>
      </div>
      <div className="page-body">
        {/* Model Stats */}
        <div className="kpi-grid" style={{ marginBottom: 20 }}>
          {[
            { label: 'HMM Accuracy', value: `${(modelMetrics.hmm.accuracy * 100).toFixed(1)}%`, sub: liveRegime ? `Regime: ${liveRegime.regime}` : `${modelMetrics.hmm.regimeChanges} regime changes` },
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

        {/* Live Model Signal Cards */}
        {models && (
          <div className="card animate-in" style={{ marginBottom: 16 }}>
            <div className="card-header">
              <span className="card-title">Live Model Signals</span>
              <div style={{ display: 'flex', gap: 8 }}>
                {goldPrice > 0 && <span className="card-badge badge-gold">Gold ${goldPrice.toFixed(2)}</span>}
                <span className={`card-badge ${inferenceRunning ? 'badge-green' : 'badge-orange'}`}>
                  {inferenceRunning ? '● LIVE' : '○ IDLE'}
                </span>
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 12 }}>
              {Object.entries(models).map(([name, data]) => {
                const sig = data.signal || 'IDLE';
                const conf = ((data.confidence || 0) * 100).toFixed(0);
                const updatedAgo = data.last_updated
                  ? `${Math.max(0, Math.floor((Date.now() - new Date(data.last_updated).getTime()) / 1000))}s ago`
                  : 'never';
                const reasoning = (data.reasoning || '').slice(0, 100) || 'Awaiting inference...';
                return (
                  <div key={name} style={{
                    padding: 16, borderRadius: 'var(--radius-sm)',
                    background: 'var(--bg-secondary)',
                    border: `1px solid ${sig !== 'HOLD' && sig !== 'IDLE' ? (sig === 'LONG' ? 'rgba(0,196,140,0.4)' : 'rgba(255,77,106,0.4)') : 'var(--border-color)'}`,
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{
                          width: 28, height: 28, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center',
                          fontSize: 14, background: `${modelColors[name]}20`, color: modelColors[name],
                        }}>{modelIcons[name]}</span>
                        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-bright)', textTransform: 'capitalize' }}>{name}</span>
                      </div>
                      <span style={{
                        fontSize: 10, fontWeight: 700, padding: '4px 10px', borderRadius: 12,
                        background: signalBg(sig), color: signalColor(sig),
                        display: 'flex', alignItems: 'center', gap: 4,
                      }}>
                        {sig === 'LONG' ? <ArrowUpRight size={10} /> : sig === 'SHORT' ? <ArrowDownRight size={10} /> : <Minus size={10} />}
                        {sig}
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>
                      <span>Confidence: <span style={{ color: signalColor(sig), fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{conf}%</span></span>
                      <span>Regime: <span style={{ fontWeight: 600 }}>{data.regime || '—'}</span></span>
                      <span>{updatedAgo}</span>
                    </div>
                    <div className="progress-bar">
                      <div className="progress-fill" style={{
                        width: `${conf}%`,
                        background: signalColor(sig),
                        transition: 'width 0.6s ease',
                      }} />
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 8, fontStyle: 'italic', lineHeight: 1.3 }}>{reasoning}</div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Regime + Wavelet Charts */}
        <div className="grid-2" style={{ marginBottom: 16 }}>
          <div className="card animate-in">
            <div className="card-header">
              <span className="card-title">Regime Probabilities (30D)</span>
              <span className="card-badge badge-green">Current: {liveRegime?.regime || regimeData.current}</span>
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
              <span className="card-title">Model Confidence Radar</span>
              <span className={`card-badge ${live ? 'badge-green' : 'badge-purple'}`}>{live ? 'LIVE' : 'STATIC'}</span>
            </div>
            <ResponsiveContainer width="100%" height={240}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="rgba(42,53,80,.5)" />
                <PolarAngleAxis dataKey="model" tick={{ fontSize: 11, fill: '#9ca3af', fontWeight: 600 }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 9, fill: '#6b7280' }} />
                <Radar name="Confidence" dataKey="confidence" stroke="#a855f7" fill="rgba(168,85,247,.2)" strokeWidth={2} dot={{ r: 4, fill: '#a855f7' }} />
              </RadarChart>
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
            <div className="card-header"><span className="card-title">Signal Log</span><span className="card-badge badge-gold">{signalLog.length} signals</span></div>
            <table className="data-table">
              <thead><tr><th>Time</th><th>Type</th><th>Source</th><th>Conf</th><th>Status</th></tr></thead>
              <tbody>
                {signalLog.map(s => (
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

            {/* Inference Status */}
            {inferenceStatus && (
              <div style={{ marginTop: 16, borderTop: '1px solid var(--border-color)', paddingTop: 12 }}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>Inference Loop</div>
                {[
                  ['Status', inferenceStatus.running ? '● Running' : '○ Stopped'],
                  ['Iteration', `#${inferenceStatus.iteration}`],
                  ['Interval', `${inferenceStatus.interval_seconds}s`],
                  ['Last Run', inferenceStatus.last_run ? new Date(inferenceStatus.last_run).toLocaleTimeString() : '—'],
                  ['Last Error', inferenceStatus.last_error || 'None ✓'],
                ].map(([k, v], i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', fontSize: 11 }}>
                    <span style={{ color: 'var(--text-muted)' }}>{k}</span>
                    <span className="mono" style={{ fontSize: 11, color: k === 'Status' && inferenceStatus.running ? 'var(--green)' : k === 'Last Error' && inferenceStatus.last_error ? 'var(--red)' : 'var(--text-bright)' }}>{v}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
