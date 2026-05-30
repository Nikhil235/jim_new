import { useState, useEffect, useRef } from 'react';
import { TrendingUp, TrendingDown, DollarSign, BarChart3, Target, Activity, Wifi, WifiOff } from 'lucide-react';
import { fetchHealth, fetchPaperTradingStatus, fetchPaperTradingPerformance, fetchLiveSignals } from '../data/api';
import MarketData from './MarketData';



export default function Overview() {
  const [live, setLive] = useState(false);
  const [health, setHealth] = useState(null);
  const [ptStatus, setPtStatus] = useState(null);
  const [ptPerf, setPtPerf] = useState(null);
  const [liveSignals, setLiveSignals] = useState(null);

  const refreshRef = useRef(null);
  refreshRef.current = async () => {
    try { const h = await fetchHealth(); setHealth(h); setLive(true); } catch { setLive(false); }
    try { setPtStatus(await fetchPaperTradingStatus()); } catch { /* offline */ }
    try { setPtPerf(await fetchPaperTradingPerformance()); } catch { /* offline */ }
    try { setLiveSignals(await fetchLiveSignals()); } catch { /* offline */ }
  };

  useEffect(() => { refreshRef.current?.(); const t = setInterval(() => refreshRef.current?.(), 30000); return () => clearInterval(t); }, []);

  const pv = ptStatus?.portfolio;
  const goldPrice = liveSignals?.current_price || 0;
  const goldChange = liveSignals?.price_change || 0;
  const kpis = [
    { label: 'Portfolio Value', value: pv ? `$${(pv.total_value||0).toLocaleString(undefined,{maximumFractionDigits:0})}` : '—', change: pv ? `${(pv.return_pct||0)>=0?'+':''}${(pv.return_pct||0).toFixed(2)}%` : 'Awaiting data', positive: (pv?.return_pct||0)>=0, icon: <DollarSign size={18}/>, bg: 'var(--gold-glow)', color: 'var(--gold-primary)' },
    { label: 'Daily P&L', value: pv ? `${(pv.pnl_daily||0)>=0?'+':''}$${Math.abs(pv.pnl_daily||0).toFixed(2)}` : '—', change: pv ? `Total: $${(pv.pnl_total||0).toFixed(2)}` : 'Awaiting data', positive: (pv?.pnl_daily||0)>=0, icon: <TrendingUp size={18}/>, bg: 'var(--green-dim)', color: 'var(--green)' },
    { label: 'Sharpe Ratio', value: ptPerf ? (ptPerf.sharpe_ratio||0).toFixed(2) : '—', change: ptPerf ? ((ptPerf.sharpe_ratio||0)>=2.0?'DSR Validated ✓':'Below target') : 'Awaiting data', positive: (ptPerf?.sharpe_ratio||0)>=1.5, icon: <BarChart3 size={18}/>, bg: 'var(--blue-dim)', color: 'var(--blue)' },
    { label: 'Win Rate', value: ptPerf ? `${((ptPerf.win_rate||0)*100).toFixed(1)}%` : '—', change: ptPerf ? `${ptPerf.num_trades||0} trades` : 'Awaiting data', positive: (ptPerf?.win_rate||0)>=0.5, icon: <Target size={18}/>, bg: 'var(--purple-dim)', color: 'var(--purple)' },
    { label: 'Gold (XAU/USD)', value: goldPrice > 0 ? `$${goldPrice.toLocaleString(undefined,{maximumFractionDigits:2})}` : '—', change: goldChange !== 0 ? `${goldChange>=0?'+':''}${goldChange.toFixed(2)}` : 'Awaiting data', positive: goldChange>=0, icon: <Activity size={18}/>, bg: 'var(--orange-dim)', color: 'var(--orange)' },
    { label: 'Max Drawdown', value: ptPerf ? `${(ptPerf.max_drawdown||0).toFixed(2)}%` : '—', change: 'Limit: -15%', positive: false, icon: <TrendingDown size={18}/>, bg: 'var(--red-dim)', color: 'var(--red)' },
  ];



  return (<>
    <div className="page-header">
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start', flexWrap:'wrap', gap: 16}}>
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

      <div style={{ marginTop: '32px', marginBottom: '16px' }}>
        <MarketData embedded={true} />
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
    </div>
  </>);
}
