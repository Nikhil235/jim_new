import { useState, useEffect, useCallback } from 'react';
import { TrendingUp, TrendingDown, DollarSign, BarChart3, Target, Activity, Wifi, WifiOff } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { fetchHealth, fetchRegime, fetchGoldPrice, fetchPaperTradingStatus, fetchPaperTradingPerformance, fetchLiveSignals } from '../data/api';
import { phaseProgress } from '../data/mockData';

const ChartTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (<div className="custom-tooltip"><div className="label">{label}</div>
    {payload.map((p, i) => (<div key={i} className="value" style={{ color: p.color }}>{p.name}: {typeof p.value === 'number' ? p.value.toLocaleString() : p.value}</div>))}
  </div>);
};

export default function Overview() {
  const [live, setLive] = useState(false);
  const [health, setHealth] = useState(null);
  const [ptStatus, setPtStatus] = useState(null);
  const [ptPerf, setPtPerf] = useState(null);
  const [regime, setRegime] = useState(null);
  const [liveSignals, setLiveSignals] = useState(null);
  const [goldData, setGoldData] = useState(null);
  const [eqHistory, setEqHistory] = useState([]);

  const refresh = useCallback(async () => {
    try { const h = await fetchHealth(); setHealth(h); setLive(true); } catch { setLive(false); }
    try {
      const s = await fetchPaperTradingStatus(); setPtStatus(s);
      if (s?.portfolio?.total_value) {
        setEqHistory(prev => {
          const n = [...prev, { date: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), equity: s.portfolio.total_value }];
          return n.length > 200 ? n.slice(-200) : n;
        });
      }
    } catch {}
    try { setPtPerf(await fetchPaperTradingPerformance()); } catch {}
    try { setRegime(await fetchRegime()); } catch {}
    try { setLiveSignals(await fetchLiveSignals()); } catch {}
    try { setGoldData(await fetchGoldPrice('1d', '3mo')); } catch {}
  }, []);

  useEffect(() => { refresh(); const t = setInterval(refresh, 5000); return () => clearInterval(t); }, [refresh]);

  const pv = ptStatus?.portfolio;
  const kpis = [
    { label: 'Portfolio Value', value: pv ? `$${(pv.total_value||0).toLocaleString(undefined,{maximumFractionDigits:0})}` : '—', change: pv ? `${(pv.return_pct||0)>=0?'+':''}${(pv.return_pct||0).toFixed(2)}%` : 'Awaiting data', positive: (pv?.return_pct||0)>=0, icon: <DollarSign size={18}/>, bg: 'var(--gold-glow)', color: 'var(--gold-primary)' },
    { label: 'Daily P&L', value: pv ? `${(pv.pnl_daily||0)>=0?'+':''}$${Math.abs(pv.pnl_daily||0).toFixed(2)}` : '—', change: pv ? `Total: $${(pv.pnl_total||0).toFixed(2)}` : 'Awaiting data', positive: (pv?.pnl_daily||0)>=0, icon: <TrendingUp size={18}/>, bg: 'var(--green-dim)', color: 'var(--green)' },
    { label: 'Sharpe Ratio', value: ptPerf ? (ptPerf.sharpe_ratio||0).toFixed(2) : '—', change: ptPerf ? ((ptPerf.sharpe_ratio||0)>=2.0?'DSR Validated ✓':'Below target') : 'Awaiting data', positive: (ptPerf?.sharpe_ratio||0)>=1.5, icon: <BarChart3 size={18}/>, bg: 'var(--blue-dim)', color: 'var(--blue)' },
    { label: 'Win Rate', value: ptPerf ? `${((ptPerf.win_rate||0)*100).toFixed(1)}%` : '—', change: ptPerf ? `${ptPerf.num_trades||0} trades` : 'Awaiting data', positive: (ptPerf?.win_rate||0)>=0.5, icon: <Target size={18}/>, bg: 'var(--purple-dim)', color: 'var(--purple)' },
    { label: 'Gold (XAU/USD)', value: goldData?.current_price ? `$${goldData.current_price.toLocaleString(undefined,{maximumFractionDigits:2})}` : '—', change: goldData ? `${(goldData.change||0)>=0?'+':''}${(goldData.change||0).toFixed(2)}` : 'Awaiting data', positive: (goldData?.change||0)>=0, icon: <Activity size={18}/>, bg: 'var(--orange-dim)', color: 'var(--orange)' },
    { label: 'Max Drawdown', value: ptPerf ? `${(ptPerf.max_drawdown||0).toFixed(2)}%` : '—', change: 'Limit: -15%', positive: false, icon: <TrendingDown size={18}/>, bg: 'var(--red-dim)', color: 'var(--red)' },
  ];

  const regimeDisplay = regime ? { current: regime.regime||'UNKNOWN', confidence: regime.confidence||0, probabilities: regime.regime_probabilities||{} }
    : { current: 'UNKNOWN', confidence: 0, probabilities: {} };

  const signalItems = liveSignals?.models
    ? Object.entries(liveSignals.models).slice(0,4).map(([name,s],i) => ({ id:i, type:s.signal||'HOLD', source:name.charAt(0).toUpperCase()+name.slice(1), confidence:s.confidence||0, status:s.signal?'active':'idle' }))
    : [];

  return (<>
    <div className="page-header">
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
        <div>
          <h2>Dashboard Overview</h2>
          <p>Mini-Medallion Gold Trading Engine — {live?'Connected to Backend':'Offline'} • System {health?.status||'unknown'}</p>
        </div>
        <div style={{display:'flex',alignItems:'center',gap:8,padding:'6px 14px',borderRadius:'var(--radius-sm)',fontSize:12,fontWeight:600,
          background:live?'var(--green-dim)':'var(--red-dim)',color:live?'var(--green)':'var(--red)',
          border:`1px solid ${live?'rgba(0,196,140,0.3)':'rgba(255,77,106,0.3)'}`}}>
          {live?<Wifi size={14}/>:<WifiOff size={14}/>} {live?'LIVE':'OFFLINE'}
        </div>
      </div>
    </div>
    <div className="page-body">
      <div className="kpi-grid">
        {kpis.map((k,i) => (<div key={i} className="kpi-card animate-in">
          <div className="kpi-icon" style={{background:k.bg,color:k.color}}>{k.icon}</div>
          <div className="kpi-label">{k.label}</div>
          <div className="kpi-value">{k.value}</div>
          <div className={`kpi-change ${k.positive?'positive':'negative'}`}>{k.change}</div>
        </div>))}
      </div>

      {!live && (
        <div className="card animate-in" style={{marginBottom:16,padding:30,textAlign:'center'}}>
          <WifiOff size={40} style={{margin:'0 auto 12px',opacity:0.3,color:'var(--text-muted)'}}/>
          <div style={{fontSize:15,fontWeight:600,color:'var(--text-secondary)',marginBottom:8}}>Backend API Not Connected</div>
          <div style={{fontSize:12,color:'var(--text-muted)'}}>Start the API server: <code style={{background:'var(--bg-input)',padding:'2px 8px',borderRadius:4}}>python -m uvicorn src.api.app:app --port 8000</code></div>
        </div>
      )}

      <div className="grid-2-1" style={{marginBottom:16}}>
        <div className="card animate-in">
          <div className="card-header"><span className="card-title">Equity Curve</span><span className={`card-badge ${live&&eqHistory.length>0?'badge-green':'badge-orange'}`}>{live&&eqHistory.length>0?'LIVE':'WAITING'}</span></div>
          {eqHistory.length > 2 ? (
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={eqHistory}>
                <defs><linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#f0b90b" stopOpacity={0.3}/><stop offset="100%" stopColor="#f0b90b" stopOpacity={0}/></linearGradient></defs>
                <XAxis dataKey="date" tick={{fontSize:10,fill:'#6b7280'}} interval={Math.max(1,Math.floor(eqHistory.length/8))}/>
                <YAxis tick={{fontSize:10,fill:'#6b7280'}} domain={['auto','auto']} tickFormatter={v=>`$${(v/1000).toFixed(0)}k`}/>
                <Tooltip content={<ChartTooltip/>}/><Area type="monotone" dataKey="equity" stroke="#f0b90b" strokeWidth={2} fill="url(#eqGrad)" name="Portfolio"/>
              </AreaChart>
            </ResponsiveContainer>
          ) : (<div style={{height:280,display:'flex',alignItems:'center',justifyContent:'center',color:'var(--text-muted)',fontSize:13}}>Awaiting equity data...</div>)}
        </div>

        <div style={{display:'flex',flexDirection:'column',gap:16}}>
          <div className="card animate-in">
            <div className="card-header"><span className="card-title">Market Regime</span>
              <span className={`card-badge ${regimeDisplay.current==='GROWTH'?'badge-green':regimeDisplay.current==='CRISIS'?'badge-red':'badge-orange'}`}>
                {regimeDisplay.current} {(regimeDisplay.confidence*100).toFixed(0)}%
              </span>
            </div>
            {Object.keys(regimeDisplay.probabilities).length > 0 ? (
              <div className="regime-bar">
                {Object.entries(regimeDisplay.probabilities).map(([r,p]) => (
                  <div key={r} className={`regime-segment regime-${r.toLowerCase()} ${r===regimeDisplay.current?'active':''}`}>{r} {(p*100).toFixed(0)}%</div>
                ))}
              </div>
            ) : (<div style={{padding:12,color:'var(--text-muted)',fontSize:12}}>Awaiting regime data...</div>)}
          </div>

          <div className="card animate-in" style={{flex:1}}>
            <div className="card-header"><span className="card-title">Latest Signals</span><span className="card-badge badge-gold">{signalItems.filter(s=>s.type!=='HOLD'&&s.type!=='IDLE').length} Active</span></div>
            {signalItems.length > 0 ? signalItems.map(s => (
              <div key={s.id} className="signal-item">
                <div>
                  <span style={{background:s.type==='LONG'?'var(--green-dim)':s.type==='SHORT'?'var(--red-dim)':'var(--blue-dim)',padding:'2px 8px',borderRadius:12,fontSize:11,fontWeight:600,color:s.type==='LONG'?'var(--green)':s.type==='SHORT'?'var(--red)':'var(--blue)'}}>{s.type}</span>
                  <span style={{marginLeft:10,fontSize:12}}>{s.source}</span>
                </div>
                <div><span className="mono" style={{color:'var(--text-secondary)'}}>{(s.confidence*100).toFixed(0)}%</span></div>
              </div>
            )) : (<div style={{padding:12,color:'var(--text-muted)',fontSize:12}}>Awaiting signals...</div>)}
          </div>
        </div>
      </div>

      {health && (
        <div className="card animate-in" style={{marginBottom:16}}>
          <div className="card-header"><span className="card-title">System Health</span><span className={`card-badge ${health.status==='ok'?'badge-green':'badge-orange'}`}>{(health.status||'—').toUpperCase()}</span></div>
          <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(150px,1fr))',gap:10}}>
            {[
              {name:'API Server',ok:true},{name:'GPU',ok:health.gpu_available},{name:'Database',ok:health.database_connected},
              {name:'Redis',ok:health.redis_connected},{name:'Models',ok:health.models_loaded},{name:'SLA',ok:health.sla_compliant??true},
            ].map((s,i)=>(<div key={i} style={{padding:'10px 14px',borderRadius:'var(--radius-sm)',background:'var(--bg-secondary)',border:'1px solid var(--border-color)',display:'flex',alignItems:'center',gap:10}}>
              <div style={{width:8,height:8,borderRadius:'50%',background:s.ok?'var(--green)':'var(--red)',boxShadow:s.ok?'0 0 8px var(--green)':'none'}}/>
              <span style={{fontSize:12,color:'var(--text-secondary)'}}>{s.name}</span>
            </div>))}
          </div>
        </div>
      )}

      <div className="card animate-in">
        <div className="card-header"><span className="card-title">Development Roadmap</span><span className="card-badge badge-green">100% Complete</span></div>
        <div className="phase-timeline">
          {phaseProgress.map(p => (<div key={p.phase} className="phase-row">
            <div className="phase-label"><span className={`phase-num ${p.status}`}>P{p.phase}</span><span className="phase-name">{p.name}</span></div>
            <div className="phase-bar-wrap">
              <div className="progress-bar" style={{height:8,flex:1}}><div className="progress-fill" style={{width:`${p.progress}%`,background:p.status==='complete'?'var(--green)':p.status==='in-progress'?'var(--gold-primary)':'var(--bg-input)'}}/></div>
              <span className="mono" style={{fontSize:11,minWidth:36,textAlign:'right'}}>{p.progress}%</span>
            </div>
          </div>))}
        </div>
      </div>
    </div>
  </>);
}
