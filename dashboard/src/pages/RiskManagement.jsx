import { useState, useEffect, useCallback } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Wifi, WifiOff } from 'lucide-react';
import { fetchRiskReport, fetchPaperTradingStatus, fetchPaperTradingPerformance } from '../data/api';

const TT = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (<div className="custom-tooltip"><div className="label">{label}</div>
    {payload.map((p, i) => <div key={i} className="value" style={{ color: p.color }}>{p.name}: {p.value}</div>)}
  </div>);
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
      <div className="progress-bar" style={{ height: 8 }}><div className="progress-fill" style={{ width: `${pct}%`, background: color }} /></div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
        <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>Current: {value}{unit}</span>
        <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>Limit: {limit}{unit}</span>
      </div>
    </div>
  );
}

export default function RiskManagement() {
  const [live, setLive] = useState(false);
  const [risk, setRisk] = useState(null);
  const [perf, setPerf] = useState(null);
  const [status, setStatus] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [r, p, s] = await Promise.all([fetchRiskReport(), fetchPaperTradingPerformance(), fetchPaperTradingStatus()]);
      setRisk(r); setPerf(p); setStatus(s); setLive(true);
    } catch { setLive(false); }
  }, []);

  useEffect(() => { refresh(); const t = setInterval(refresh, 5000); return () => clearInterval(t); }, [refresh]);

  if (!live) return (
    <><div className="page-header"><h2>Risk Management</h2><p>⚠ Backend offline — start the API and paper trading engine</p></div>
    <div className="page-body"><div className="card" style={{padding:40,textAlign:'center',color:'var(--text-muted)'}}>
      <WifiOff size={48} style={{margin:'0 auto 16px',opacity:0.3}}/><div style={{fontSize:16,fontWeight:600}}>No Connection</div>
    </div></div></>
  );

  const rr = risk?.risk_report || {};
  const cfg = status?.config || {};
  const pf = status?.portfolio || {};
  const dd = rr.drawdown_pct || perf?.max_drawdown || 0;
  const dailyPnl = rr.daily_pnl || perf?.pnl_daily || 0;
  const consLoss = rr.consecutive_losses || 0;
  const violations = rr.violations || [];

  // Circuit breaker data from risk report
  const cbData = [
    { name: 'Daily P&L → Halt', status: Math.abs(dailyPnl) > (cfg.max_daily_loss_pct || 0.02) * (pf.total_value || 100000) ? 'triggered' : 'ok', value: dailyPnl.toFixed(2), limit: ((cfg.max_daily_loss_pct || 0.02) * (pf.total_value || 100000)).toFixed(0), unit: '$' },
    { name: 'Max Drawdown → Stop', status: Math.abs(dd) > ((cfg.max_drawdown_pct || 0.15) * 100) ? 'triggered' : 'ok', value: dd.toFixed(2), limit: ((cfg.max_drawdown_pct || 0.15) * 100).toFixed(0), unit: '%' },
    { name: 'Consecutive Losses', status: consLoss >= 5 ? 'warning' : 'ok', value: consLoss, limit: 10, unit: '' },
    { name: 'Risk Violations', status: violations.length > 0 ? 'triggered' : 'ok', value: violations.length, limit: 3, unit: '' },
  ];

  return (<>
    <div className="page-header">
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
        <div><h2>Risk Management</h2><p>Live risk metrics from paper trading engine — Circuit breakers, Kelly sizing & position management</p></div>
        <div style={{display:'flex',alignItems:'center',gap:6,padding:'5px 12px',borderRadius:'var(--radius-sm)',fontSize:11,fontWeight:600,background:'var(--green-dim)',color:'var(--green)',border:'1px solid rgba(0,196,140,0.3)'}}>
          <Wifi size={12}/> LIVE
        </div>
      </div>
    </div>
    <div className="page-body">
      <div className="kpi-grid" style={{marginBottom:20}}>
        {[
          {label:'Portfolio Value',value:`$${(pf.total_value||0).toLocaleString(undefined,{maximumFractionDigits:0})}`,sub:`Return: ${(pf.return_pct||0).toFixed(2)}%`},
          {label:'Drawdown',value:`${dd.toFixed(2)}%`,sub:`Limit: ${((cfg.max_drawdown_pct||0.15)*100).toFixed(0)}%`},
          {label:'Daily P&L',value:`$${dailyPnl.toFixed(2)}`,sub:`Limit: ${((cfg.max_daily_loss_pct||0.02)*100).toFixed(1)}%`},
          {label:'Win Rate',value:`${((perf?.win_rate||0)*100).toFixed(1)}%`,sub:`${perf?.num_trades||0} trades`},
          {label:'Sharpe',value:(perf?.sharpe_ratio||0).toFixed(2),sub:'Annualized'},
          {label:'Violations',value:violations.length,sub:violations.length===0?'All clear ✓':'Action required'},
        ].map((m,i)=>(<div key={i} className="kpi-card animate-in">
          <div className="kpi-label">{m.label}</div><div className="kpi-value" style={{fontSize:22}}>{m.value}</div>
          <div style={{fontSize:11,color:'var(--text-muted)',marginTop:4}}>{m.sub}</div>
        </div>))}
      </div>

      <div className="grid-2" style={{marginBottom:16}}>
        <div className="card animate-in">
          <div className="card-header"><span className="card-title">Circuit Breakers</span>
            <span className={`card-badge ${violations.length===0?'badge-green':'badge-red'}`}>{violations.length===0?'ALL CLEAR':'ALERT'}</span>
          </div>
          {cbData.map((cb,i)=><CircuitBreaker key={i} name={cb.name} status={cb.status} value={cb.value} limit={cb.limit} unit={cb.unit}/>)}
          {violations.length>0 && (
            <div style={{marginTop:12,padding:10,borderRadius:'var(--radius-sm)',background:'var(--red-dim)',fontSize:11,color:'var(--red)'}}>
              ⚠ Violations: {violations.join(', ')}
            </div>
          )}
        </div>

        <div className="card animate-in">
          <div className="card-header"><span className="card-title">Risk Report Details</span><span className="card-badge badge-purple">REAL-TIME</span></div>
          <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12,marginTop:8}}>
            {[
              {label:'Current Equity',value:`$${(rr.current_equity||pf.total_value||0).toLocaleString(undefined,{maximumFractionDigits:0})}`,good:true},
              {label:'Peak Equity',value:`$${(rr.peak_equity||0).toLocaleString(undefined,{maximumFractionDigits:0})}`,good:true},
              {label:'Drawdown %',value:`${dd.toFixed(2)}%`,good:Math.abs(dd)<5},
              {label:'Consecutive Losses',value:consLoss,good:consLoss<3},
              {label:'Daily Trades',value:perf?.daily_trades||0,good:true},
              {label:'Position Value',value:`$${(pf.position_value||0).toLocaleString(undefined,{maximumFractionDigits:0})}`,good:true},
            ].map((m,i)=>(<div key={i} style={{display:'flex',justifyContent:'space-between',padding:'8px 0',borderBottom:'1px solid var(--border-color)'}}>
              <span style={{fontSize:12,color:'var(--text-muted)'}}>{m.label}</span>
              <div style={{display:'flex',alignItems:'center',gap:6}}>
                <span className="mono" style={{fontSize:13,fontWeight:600,color:'var(--text-bright)'}}>{m.value}</span>
                <span style={{fontSize:10,color:m.good?'var(--green)':'var(--orange)'}}>{m.good?'✓':'~'}</span>
              </div>
            </div>))}
          </div>
        </div>
      </div>

      <div className="card animate-in">
        <div className="card-header"><span className="card-title">Kelly Criterion — Regime-Aware Position Sizing</span></div>
        <div style={{padding:12,background:'var(--bg-secondary)',borderRadius:'var(--radius-sm)',fontFamily:'var(--font-mono)',fontSize:12,color:'var(--text-muted)',marginBottom:12}}>
          f* = (p × b − q) / b &nbsp;&nbsp;→&nbsp;&nbsp; Applied fraction: {cfg.kelly_fraction || 0.25}
        </div>
        <div style={{display:'grid',gridTemplateColumns:'repeat(5,1fr)',gap:20}}>
          {[
            {label:'Kelly Fraction',value:(cfg.kelly_fraction||0.25).toFixed(2)},
            {label:'Max Position',value:`${((cfg.max_position_pct||0.1)*100).toFixed(0)}%`},
            {label:'Position Value',value:`$${(pf.position_value||0).toLocaleString(undefined,{maximumFractionDigits:0})}`},
            {label:'Cash',value:`$${(pf.cash||0).toLocaleString(undefined,{maximumFractionDigits:0})}`},
            {label:'Min Confidence',value:`${((cfg.min_confidence||0.6)*100).toFixed(0)}%`},
          ].map((k,i)=>(<div key={i} style={{textAlign:'center'}}>
            <div style={{fontSize:11,color:'var(--text-muted)',marginBottom:4}}>{k.label}</div>
            <div className="mono" style={{fontSize:20,fontWeight:700,color:'var(--gold-primary)'}}>{k.value}</div>
          </div>))}
        </div>
      </div>
    </div>
  </>);
}
