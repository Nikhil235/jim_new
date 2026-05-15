import { useState, useCallback } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts';
import { Play, Loader } from 'lucide-react';
import { runBacktest } from '../data/api';

const TT = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (<div className="custom-tooltip"><div className="label">{label}</div>
    {payload.map((p, i) => <div key={i} className="value" style={{ color: p.color }}>{p.name}: {p.value}</div>)}
  </div>);
};

export default function Backtesting() {
  const [results, setResults] = useState(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [strategy, setStrategy] = useState('ensemble');
  const [config, setConfig] = useState({ initial_capital: 100000, commission: 2.5, slippage_bps: 1.0, train_years: 3, test_years: 1 });

  const handleRun = useCallback(async () => {
    setRunning(true); setError(null);
    try {
      const res = await runBacktest(strategy, config);
      setResults(res);
    } catch (e) { setError(e.message); }
    setRunning(false);
  }, [strategy, config]);

  const models = results?.models || [];
  const radarData = models.map(m => ({ name: m.name, sharpe: m.sharpe || 0, winRate: (m.win_rate || 0) * 100, profitFactor: m.profit_factor || 0 }));
  const sharpeData = models.map(m => ({ name: m.name, sharpe: m.sharpe || 0, fill: (m.dsr_pass ?? true) ? 'rgba(0,196,140,0.6)' : 'rgba(255,77,106,0.6)' }));

  return (<>
    <div className="page-header"><h2>Backtesting & Validation</h2><p>Run backtests via API — Event-driven engine with anti-overfitting validation</p></div>
    <div className="page-body">
      {/* Run Controls */}
      <div className="card animate-in" style={{ marginBottom: 16 }}>
        <div className="card-header"><span className="card-title">Run Backtest</span><span className="card-badge badge-purple">API</span></div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(140px,1fr))', gap: 10, marginBottom: 12 }}>
          <div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 4 }}>Strategy</div>
            <select value={strategy} onChange={e => setStrategy(e.target.value)} style={{ width: '100%', padding: '6px 10px', borderRadius: 6, border: '1px solid var(--border-color)', background: 'var(--bg-input)', color: 'var(--text-bright)', fontSize: 12 }}>
              {['ensemble', 'wavelet', 'hmm', 'lstm', 'tft', 'genetic'].map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          {[['Capital ($)', config.initial_capital, 'initial_capital'], ['Commission ($)', config.commission, 'commission'], ['Slippage (bps)', config.slippage_bps, 'slippage_bps'], ['Train (yr)', config.train_years, 'train_years'], ['Test (yr)', config.test_years, 'test_years']].map(([label, val, key]) => (
            <div key={key}>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 4 }}>{label}</div>
              <input type="number" step="any" value={val} onChange={e => setConfig(p => ({ ...p, [key]: parseFloat(e.target.value) || 0 }))}
                style={{ width: '100%', padding: '6px 10px', borderRadius: 6, border: '1px solid var(--border-color)', background: 'var(--bg-input)', color: 'var(--text-bright)', fontFamily: 'var(--font-mono)', fontSize: 12 }} />
            </div>
          ))}
        </div>
        <button onClick={handleRun} disabled={running} style={{ padding: '8px 24px', borderRadius: 6, border: 'none', background: running ? 'var(--bg-input)' : 'var(--gold-primary)', color: running ? 'var(--text-muted)' : '#000', fontWeight: 600, cursor: running ? 'not-allowed' : 'pointer', fontSize: 12 }}>
          {running ? <><Loader size={12} style={{ marginRight: 4, verticalAlign: 'middle', animation: 'spin 1s linear infinite' }} /> Running...</> : <><Play size={12} style={{ marginRight: 4, verticalAlign: 'middle' }} /> Run Backtest</>}
        </button>
        {error && <div style={{ marginTop: 10, padding: 10, borderRadius: 'var(--radius-sm)', background: 'var(--red-dim)', color: 'var(--red)', fontSize: 12 }}>⚠ {error}</div>}
      </div>

      {/* Results */}
      {results && (<>
        <div className="kpi-grid" style={{ marginBottom: 20 }}>
          {[
            { label: 'Strategy', value: results.strategy || strategy, sub: `${models.length} models` },
            { label: 'Total Return', value: `${(results.total_return || 0).toFixed(1)}%`, sub: `$${(results.final_equity || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}` },
            { label: 'Sharpe', value: (results.sharpe_ratio || 0).toFixed(2), sub: 'Annualized' },
            { label: 'Max Drawdown', value: `${(results.max_drawdown || 0).toFixed(1)}%`, sub: 'Peak-to-trough' },
            { label: 'Trades', value: results.num_trades || 0, sub: `Win: ${((results.win_rate || 0) * 100).toFixed(1)}%` },
          ].map((m, i) => (<div key={i} className="kpi-card animate-in">
            <div className="kpi-label">{m.label}</div><div className="kpi-value" style={{ fontSize: 22 }}>{m.value}</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>{m.sub}</div>
          </div>))}
        </div>

        {models.length > 0 && (
          <div className="card animate-in" style={{ marginBottom: 16 }}>
            <div className="card-header"><span className="card-title">Model Results</span><span className="card-badge badge-green">COMPLETE</span></div>
            <table className="data-table">
              <thead><tr><th>Model</th><th>Sharpe</th><th>Sortino</th><th>Win Rate</th><th>P.Factor</th><th>Max DD</th><th>Return</th><th>DSR</th></tr></thead>
              <tbody>
                {models.map((m, i) => (<tr key={i}>
                  <td style={{ fontWeight: 600, color: 'var(--text-bright)' }}>{m.name}</td>
                  <td className="mono" style={{ color: (m.sharpe || 0) >= 2 ? 'var(--green)' : 'var(--orange)' }}>{(m.sharpe || 0).toFixed(2)}</td>
                  <td className="mono">{(m.sortino || 0).toFixed(2)}</td>
                  <td className="mono">{((m.win_rate || 0) * 100).toFixed(1)}%</td>
                  <td className="mono">{(m.profit_factor || 0).toFixed(2)}</td>
                  <td className="mono" style={{ color: 'var(--red)' }}>{(m.max_dd || 0).toFixed(1)}%</td>
                  <td className="mono" style={{ color: 'var(--green)' }}>+{(m.total_return || 0).toFixed(1)}%</td>
                  <td><span className={`card-badge ${(m.dsr_pass ?? true) ? 'badge-green' : 'badge-red'}`}>{(m.dsr_pass ?? true) ? '✓' : '✗'}</span></td>
                </tr>))}
              </tbody>
            </table>
          </div>
        )}

        {sharpeData.length > 0 && (
          <div className="grid-2">
            <div className="card animate-in">
              <div className="card-header"><span className="card-title">Sharpe by Model</span></div>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={sharpeData}><XAxis dataKey="name" tick={{ fontSize: 11, fill: '#9ca3af' }} /><YAxis tick={{ fontSize: 10, fill: '#6b7280' }} domain={[0, 3]} /><Tooltip content={<TT />} />
                  <Bar dataKey="sharpe" name="Sharpe" radius={[4, 4, 0, 0]}>{sharpeData.map((d, i) => <Cell key={i} fill={d.fill} />)}</Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="card animate-in">
              <div className="card-header"><span className="card-title">Model Radar</span></div>
              <ResponsiveContainer width="100%" height={260}>
                <RadarChart data={radarData}><PolarGrid stroke="rgba(42,53,80,.5)" /><PolarAngleAxis dataKey="name" tick={{ fontSize: 11, fill: '#9ca3af' }} /><PolarRadiusAxis angle={30} domain={[0, 3]} tick={{ fontSize: 9, fill: '#6b7280' }} />
                  <Radar name="Sharpe" dataKey="sharpe" stroke="#a855f7" fill="rgba(168,85,247,.2)" strokeWidth={2} dot={{ r: 4, fill: '#a855f7' }} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </>)}

      {!results && !running && (
        <div className="card" style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>📊</div>
          <div style={{ fontSize: 16, fontWeight: 600 }}>No Results Yet</div>
          <div style={{ fontSize: 12, marginTop: 8 }}>Configure parameters above and click "Run Backtest" to execute via API</div>
        </div>
      )}
    </div>
  </>);
}
