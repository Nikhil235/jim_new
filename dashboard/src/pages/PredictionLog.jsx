import React, { useState, useEffect } from 'react';
import { Database, Download, RefreshCw, AlertCircle } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

export default function PredictionLog() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/paper-trading/prediction-log?limit=200`);
      if (!response.ok) throw new Error('Failed to fetch prediction logs');
      const data = await response.json();
      setLogs(data.logs || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 15000); // refresh every 15s
    return () => clearInterval(interval);
  }, []);

  const downloadCSV = () => {
    if (logs.length === 0) return;
    
    const headers = Object.keys(logs[0]);
    const csvContent = [
      headers.join(','),
      ...logs.map(row => headers.map(header => row[header] || '').join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `prediction_log_${new Date().toISOString().slice(0,10)}.csv`;
    link.click();
  };

  const getSignalColor = (signal) => {
    if (signal === 'LONG') return 'var(--green)';
    if (signal === 'SHORT') return 'var(--red)';
    return 'var(--text-muted)';
  };

  const getPnlColor = (pnl) => {
    const val = parseFloat(pnl);
    if (isNaN(val)) return 'var(--text-muted)';
    return val > 0 ? 'var(--green)' : val < 0 ? 'var(--red)' : 'var(--text-primary)';
  };

  return (
    <div className="page-container animate-in">
      <header className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div className="header-icon">
            <Database size={24} />
          </div>
          <div>
            <h1 className="page-title">Prediction Log</h1>
            <p className="page-subtitle">Raw model outputs and ensemble consensus per cycle</p>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn" onClick={fetchLogs} disabled={loading}>
            <RefreshCw size={16} className={loading ? 'spin-icon' : ''} />
            Refresh
          </button>
          <button className="btn btn-primary" onClick={downloadCSV} disabled={logs.length === 0}>
            <Download size={16} />
            Export CSV
          </button>
        </div>
      </header>

      {error && (
        <div className="alert-box error" style={{ marginBottom: '24px' }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      <div className="glass-panel" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)', background: 'rgba(0,0,0,0.2)' }}>
          <h3 className="panel-title" style={{ margin: 0, fontSize: '14px' }}>Cycle Log ({logs.length} records)</h3>
        </div>
        
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table" style={{ width: '100%', minWidth: '1600px' }}>
            <thead>
              <tr>
                <th style={{ minWidth: '160px' }}>Timestamp</th>
                <th>Price</th>
                <th>Regime</th>
                <th>Wavelet</th>
                <th>HMM</th>
                <th>LSTM</th>
                <th>TFT</th>
                <th>Genetic</th>
                <th>Ensemble</th>
                <th>Kelly</th>
                <th>Trade</th>
                <th>P&L</th>
              </tr>
            </thead>
            <tbody>
              {logs.length === 0 && !loading ? (
                <tr>
                  <td colSpan="12" style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                    No prediction logs found. Wait for the live inference loop to run.
                  </td>
                </tr>
              ) : (
                [...logs].reverse().map((log, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      {log.timestamp.replace('T', ' ')}
                    </td>
                    <td style={{ fontFamily: 'monospace', fontSize: '13px' }}>
                      ${parseFloat(log.price).toFixed(2)}
                    </td>
                    <td>
                      <span className={`badge regime-${log.regime?.toLowerCase() || 'normal'}`}>
                        {log.regime}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                        <span style={{ fontWeight: 600, color: getSignalColor(log.wavelet_signal), fontSize: '12px' }}>{log.wavelet_signal}</span>
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{(log.wavelet_conf * 100).toFixed(0)}%</span>
                      </div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                        <span style={{ fontWeight: 600, color: getSignalColor(log.hmm_signal), fontSize: '12px' }}>{log.hmm_signal}</span>
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{(log.hmm_conf * 100).toFixed(0)}%</span>
                      </div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                        <span style={{ fontWeight: 600, color: getSignalColor(log.lstm_signal), fontSize: '12px' }}>{log.lstm_signal}</span>
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{(log.lstm_conf * 100).toFixed(0)}%</span>
                      </div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                        <span style={{ fontWeight: 600, color: getSignalColor(log.tft_signal), fontSize: '12px' }}>{log.tft_signal}</span>
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{(log.tft_conf * 100).toFixed(0)}%</span>
                      </div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                        <span style={{ fontWeight: 600, color: getSignalColor(log.genetic_signal), fontSize: '12px' }}>{log.genetic_signal}</span>
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{(log.genetic_conf * 100).toFixed(0)}%</span>
                      </div>
                    </td>
                    <td style={{ background: 'rgba(255,184,0,0.05)' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                        <span style={{ fontWeight: 700, color: getSignalColor(log.ensemble_signal), fontSize: '13px' }}>{log.ensemble_signal}</span>
                        <span style={{ fontSize: '11px', color: 'var(--gold-primary)' }}>{(log.ensemble_conf * 100).toFixed(0)}%</span>
                      </div>
                    </td>
                    <td style={{ fontSize: '12px' }}>
                      {log.kelly_fraction ? `${(log.kelly_fraction * 100).toFixed(1)}%` : '-'}
                    </td>
                    <td>
                      {log.trade_taken === 'YES' ? (
                        <span className="badge" style={{ background: 'rgba(255,255,255,0.1)', color: '#fff' }}>EXEC</span>
                      ) : (
                        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>PASS</span>
                      )}
                    </td>
                    <td style={{ fontWeight: 600, color: getPnlColor(log.pnl), fontSize: '13px', fontFamily: 'monospace' }}>
                      {log.pnl ? (parseFloat(log.pnl) > 0 ? `+$${parseFloat(log.pnl).toFixed(2)}` : `-$${Math.abs(parseFloat(log.pnl)).toFixed(2)}`) : '-'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
