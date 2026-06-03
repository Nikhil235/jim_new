import React, { useState, useEffect, useRef } from 'react';
import { Info, CheckCircle2, RefreshCw, AlertTriangle } from 'lucide-react';
import { fetchCorrelationMatrix } from '../data/api';

const modelIcons = { wavelet: '🌊', hmm: '📊', lstm: '🧠', tft: '⚡', genetic: '🧬', ensemble: '🎯' };
const modelColors = { wavelet: '#3b82f6', hmm: '#a855f7', lstm: '#06b6d4', tft: '#f59e0b', genetic: '#22c55e', ensemble: '#ef4444' };
const modelNames = ['wavelet', 'hmm', 'lstm', 'tft', 'genetic', 'ensemble'];

// Default mock data structure as fallback
const defaultCorrelationMatrix = {
  wavelet: { wavelet: 100, hmm: 58, lstm: 48, tft: 42, genetic: 36, ensemble: 50 },
  hmm: { wavelet: 58, hmm: 100, lstm: 52, tft: 41, genetic: 62, ensemble: 40 },
  lstm: { wavelet: 48, hmm: 52, lstm: 100, tft: 61, genetic: 71, ensemble: 53 },
  tft: { wavelet: 42, hmm: 41, lstm: 61, tft: 100, genetic: 65, ensemble: 60 },
  genetic: { wavelet: 36, hmm: 62, lstm: 71, tft: 65, genetic: 100, ensemble: 32 },
  ensemble: { wavelet: 50, hmm: 40, lstm: 53, tft: 60, genetic: 32, ensemble: 100 },
};

const defaultAvgPairwise = {
  wavelet: 46, hmm: 53, lstm: 58, tft: 52, genetic: 59
};

const defaultConsensus = [
  { model: 'wavelet', name: 'Wavelet', agreement: 50 },
  { model: 'hmm', name: 'HMM', agreement: 40 },
  { model: 'lstm', name: 'LSTM', agreement: 53 },
  { model: 'tft', name: 'TFT', agreement: 60 },
  { model: 'genetic', name: 'Genetic', agreement: 32 },
];

function getCellColor(val) {
  if (val >= 70) return '#00c48c'; // Strong Agree (Green)
  if (val >= 50) return '#008560'; // Agree (Dark Green)
  if (val >= 40) return '#a68214'; // Neutral (Yellow/Brown)
  if (val >= 30) return '#7a5a04'; // Weak Conflict (Brown)
  return '#3b2f15'; // Strong Conflict (Dark Brown/Grey)
}

function getCellTextColor(val) {
  if (val >= 70) return '#0a0e1a'; // Dark text for bright green
  return '#e2e8f0'; // Light text for dark backgrounds
}

export default function CorrelationMatrix() {
  const [data, setData] = useState({
    correlationMatrix: defaultCorrelationMatrix,
    avgPairwiseAgreement: defaultAvgPairwise,
    consensusAnalysis: defaultConsensus,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const latestReq = useRef(0);

  const loadData = async () => {
    const reqId = ++latestReq.current;
    try {
      setLoading(true);
      setError(null);
      const res = await fetchCorrelationMatrix(1000);
      if (reqId !== latestReq.current) return;
      if (res && Object.keys(res.correlationMatrix || {}).length > 0) {
        setData(res);
      }
    } catch (err) {
      if (reqId !== latestReq.current) return;
      setError(err.message || "Failed to load data");
    } finally {
      if (reqId === latestReq.current) {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    const mountReq = latestReq.current;
    loadData();
    const timer = setInterval(loadData, 10000);
    return () => {
      clearInterval(timer);
      latestReq.current = mountReq + 1;
    };
  }, []);

  const { correlationMatrix, avgPairwiseAgreement, consensusAnalysis } = data;
  
  const totalAvgAgreement = Object.values(avgPairwiseAgreement).length > 0 
    ? Math.round(Object.values(avgPairwiseAgreement).reduce((a, b) => a + b, 0) / Object.values(avgPairwiseAgreement).length) 
    : 0;
  const consensusStatus = totalAvgAgreement >= 40 ? 'HEALTHY' : 'DIVERSE';
  const consensusColor = totalAvgAgreement >= 40 ? '#00c48c' : '#f59e0b';
  const consensusBg = totalAvgAgreement >= 40 ? '#00c48c20' : '#f59e0b20';
  const consensusBorder = totalAvgAgreement >= 40 ? '#00c48c40' : '#f59e0b40';

  return (
    <>
      <div className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2>Model Correlation Matrix</h2>
            <p>Signal agreement heatmap — ensemble diversity & consensus strength</p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <button 
              onClick={loadData}
              disabled={loading}
              style={{ 
                background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', 
                color: 'var(--text-muted)', width: 36, height: 36, borderRadius: 'var(--radius-sm)', 
                display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
                opacity: loading ? 0.5 : 1
              }}>
              <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
            </button>
          </div>
        </div>
      </div>
      
      <div className="page-body">
        
        {error && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '12px 16px', background: '#3b1a1a', border: '1px solid #ef444460', borderRadius: 'var(--radius-sm)', color: '#fca5a5', fontSize: '13px', marginBottom: '20px' }}>
            <AlertTriangle size={16} />
            <span>{error}</span>
          </div>
        )}
        
        {/* Top Grid: Matrix + Consensus */}
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px', marginBottom: '20px' }}>
          
          {/* Signal Correlation Heatmap */}
          <div className="card animate-in" style={{ padding: '24px' }}>
            <div className="card-header" style={{ marginBottom: '20px' }}>
              <span className="card-title" style={{ fontSize: '13px', letterSpacing: '0.5px' }}>SIGNAL CORRELATION</span>
              <span className="card-badge" style={{ background: '#00856030', color: '#00c48c', border: '1px solid #00c48c50' }}>AVG AGREEMENT: {totalAvgAgreement}%</span>
            </div>
            
            {/* Heatmap Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(80px, 100px) repeat(6, 1fr)', gap: '8px' }}>
              
              {/* Header Row */}
              <div />
              {modelNames.map(model => (
                <div key={`header-${model}`} style={{ textAlign: 'center', paddingBottom: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '12px' }}>{modelIcons[model]}</span>
                  <span style={{ fontSize: '12px', fontWeight: 600, color: modelColors[model], textTransform: 'capitalize' }}>{model}</span>
                </div>
              ))}

              {/* Matrix Rows */}
              {modelNames.map(rowModel => (
                <React.Fragment key={`row-${rowModel}`}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '14px' }}>{modelIcons[rowModel]}</span>
                    <span style={{ fontSize: '13px', fontWeight: 600, color: modelColors[rowModel], textTransform: 'capitalize' }}>{rowModel}</span>
                  </div>
                  
                  {modelNames.map(colModel => {
                    const val = correlationMatrix[rowModel]?.[colModel] ?? 0;
                    const bg = getCellColor(val);
                    const color = getCellTextColor(val);
                    
                    return (
                      <div key={`cell-${rowModel}-${colModel}`} style={{
                        background: bg,
                        color: color,
                        borderRadius: '6px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        height: '42px',
                        fontSize: '13px',
                        fontWeight: 600,
                        fontFamily: 'var(--font-mono)'
                      }}>
                        {val}%
                      </div>
                    );
                  })}
                </React.Fragment>
              ))}
            </div>

            {/* Legend */}
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '16px', marginTop: '24px', fontSize: '11px', color: 'var(--text-muted)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><div style={{ width: 12, height: 12, borderRadius: 3, background: getCellColor(80) }} /> Strong Agree</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><div style={{ width: 12, height: 12, borderRadius: 3, background: getCellColor(60) }} /> Weak Agree</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><div style={{ width: 12, height: 12, borderRadius: 3, background: getCellColor(45) }} /> Neutral</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><div style={{ width: 12, height: 12, borderRadius: 3, background: getCellColor(35) }} /> Weak Conflict</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><div style={{ width: 12, height: 12, borderRadius: 3, background: getCellColor(20) }} /> Strong Conflict</div>
            </div>
          </div>

          {/* Consensus Analysis */}
          <div className="card animate-in" style={{ padding: '24px', display: 'flex', flexDirection: 'column' }}>
            <div className="card-header" style={{ marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Info size={16} style={{ color: 'var(--text-muted)' }} />
                <span className="card-title" style={{ fontSize: '13px', letterSpacing: '0.5px' }}>CONSENSUS ANALYSIS</span>
              </div>
              <span className="card-badge" style={{ background: consensusBg, color: consensusColor, border: `1px solid ${consensusBorder}`, display: 'flex', alignItems: 'center', gap: '4px' }}>
                <CheckCircle2 size={12} /> {consensusStatus}
              </span>
            </div>
            
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.5, marginBottom: '32px' }}>
              How each model's signal aligns with the final ensemble decision. Higher values = more agreement. Low agreement signals model diversity (good for robustness).
            </p>

            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {consensusAnalysis.map(item => (
                <div key={item.name} style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  <div style={{ width: '80px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '14px' }}>{modelIcons[item.model]}</span>
                    <span style={{ fontSize: '13px', color: 'var(--text-bright)' }}>{item.name}</span>
                  </div>
                  <div style={{ flex: 1, height: '6px', background: 'var(--bg-input)', borderRadius: '3px', position: 'relative' }}>
                    <div style={{ 
                      position: 'absolute', top: 0, left: 0, height: '100%', 
                      width: `${item.agreement}%`, 
                      background: '#00c48c', borderRadius: '3px' 
                    }} />
                  </div>
                  <span style={{ width: '30px', textAlign: 'right', fontSize: '13px', color: '#00c48c', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
                    {item.agreement}%
                  </span>
                </div>
              ))}
            </div>

            <div style={{ marginTop: '32px', fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.5, fontStyle: 'italic', borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
              <strong style={{ color: 'var(--text-secondary)' }}>Interpretation:</strong> Model disagreement is a feature, not a bug. When models disagree, the ensemble weights each vote by its conviction + regime-conditional trust, creating a robust consensus.
            </div>
          </div>
        </div>

        {/* Bottom Cards: Avg Pairwise Agreement */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '20px' }}>
          {['wavelet', 'hmm', 'lstm', 'tft', 'genetic'].map(model => (
            <div key={model} className="card animate-in" style={{ padding: '24px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                <span style={{ fontSize: '14px' }}>{modelIcons[model]}</span>
                <span style={{ fontSize: '13px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>{model}</span>
              </div>
              <div style={{ fontSize: '32px', fontWeight: 700, color: '#00c48c', fontFamily: 'var(--font-mono)', marginBottom: '8px' }}>
                {avgPairwiseAgreement[model] ?? 0}%
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Avg Pairwise Agreement</div>
            </div>
          ))}
        </div>

      </div>
    </>
  );
}
