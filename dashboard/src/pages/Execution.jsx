import { useState, useEffect, useCallback } from 'react';
import { Wifi, WifiOff } from 'lucide-react';
import { fetchPaperTradingStatus, fetchPaperTradingTrades } from '../data/api';

export default function Execution() {
  const [live, setLive] = useState(false);
  const [status, setStatus] = useState(null);
  const [trades, setTrades] = useState([]);

  const refresh = useCallback(async () => {
    try {
      const [s, t] = await Promise.all([fetchPaperTradingStatus(), fetchPaperTradingTrades(20)]);
      setStatus(s); setTrades(Array.isArray(t) ? t : []); setLive(true);
    } catch { setLive(false); }
  }, []);

  useEffect(() => { refresh(); const t = setInterval(refresh, 5000); return () => clearInterval(t); }, [refresh]);

  if (!live) return (
    <><div className="page-header"><h2>Execution Engine</h2><p>⚠ Backend offline</p></div>
    <div className="page-body"><div className="card" style={{padding:40,textAlign:'center',color:'var(--text-muted)'}}>
      <WifiOff size={48} style={{margin:'0 auto 16px',opacity:0.3}}/><div style={{fontSize:16,fontWeight:600}}>No Connection</div>
    </div></div></>
  );

  const cfg = status?.config || {};
  const pf = status?.portfolio || {};
  const engineStatus = status?.status || 'NOT STARTED';
  const isRunning = engineStatus === 'RUNNING';

  return (<>
    <div className="page-header">
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
        <div><h2>Execution Engine</h2><p>Live order execution via paper trading engine — {isRunning ? 'Engine Running' : 'Engine Stopped'}</p></div>
        <div style={{display:'flex',alignItems:'center',gap:6,padding:'5px 12px',borderRadius:'var(--radius-sm)',fontSize:11,fontWeight:600,background:'var(--green-dim)',color:'var(--green)',border:'1px solid rgba(0,196,140,0.3)'}}>
          <Wifi size={12}/> LIVE
        </div>
      </div>
    </div>
    <div className="page-body">
      <div className="kpi-grid" style={{marginBottom:20}}>
        {[
          {label:'Status',value:engineStatus,sub:`Started: ${status?.started_at?new Date(status.started_at).toLocaleString():'—'}`},
          {label:'Mode',value:'PAPER',sub:'Simulated execution'},
          {label:'Symbol',value:cfg.symbol||'XAUUSD',sub:`Min conf: ${((cfg.min_confidence||0.6)*100).toFixed(0)}%`},
          {label:'Max Slippage',value:`${((cfg.slippage_pct||0.3)).toFixed(1)}%`,sub:`Model: ${cfg.slippage_model||'spread'}`},
        ].map((m,i)=>(<div key={i} className="kpi-card animate-in">
          <div className="kpi-label">{m.label}</div><div className="kpi-value" style={{fontSize:22}}>{m.value}</div>
          <div style={{fontSize:11,color:'var(--text-muted)',marginTop:4}}>{m.sub}</div>
        </div>))}
      </div>

      <div className="grid-2" style={{marginBottom:16}}>
        <div className="card animate-in">
          <div className="card-header"><span className="card-title">Engine Configuration</span><span className={`card-badge ${isRunning?'badge-green':'badge-red'}`}>{isRunning?'RUNNING':'STOPPED'}</span></div>
          {[
            ['Initial Capital',`$${(cfg.initial_capital||100000).toLocaleString()}`],
            ['Kelly Fraction',cfg.kelly_fraction||'—'],
            ['Max Position %',`${((cfg.max_position_pct||0.1)*100).toFixed(0)}%`],
            ['Max Daily Loss',`${((cfg.max_daily_loss_pct||0.02)*100).toFixed(1)}%`],
            ['Max Drawdown',`${((cfg.max_drawdown_pct||0.15)*100).toFixed(0)}%`],
            ['Commission',`$${(cfg.commission_per_trade||5.0).toFixed(2)}/trade`],
            ['Slippage Model',cfg.slippage_model||'spread'],
            ['Min Confidence',`${((cfg.min_confidence||0.6)*100).toFixed(0)}%`],
          ].map(([k,v],i)=>(<div key={i} style={{display:'flex',justifyContent:'space-between',padding:'8px 0',borderBottom:'1px solid var(--border-color)'}}>
            <span style={{fontSize:12,color:'var(--text-muted)'}}>{k}</span>
            <span className="mono" style={{fontSize:12,color:'var(--text-bright)'}}>{v}</span>
          </div>))}
        </div>

        <div className="card animate-in">
          <div className="card-header"><span className="card-title">Portfolio State</span><span className="card-badge badge-gold">REAL-TIME</span></div>
          <div style={{display:'grid',gridTemplateColumns:'1fr 1fr 1fr',gap:16,marginTop:8}}>
            {[
              {label:'Total Value',value:`$${(pf.total_value||0).toLocaleString(undefined,{maximumFractionDigits:0})}`,color:'var(--gold-primary)'},
              {label:'Cash',value:`$${(pf.cash||0).toLocaleString(undefined,{maximumFractionDigits:0})}`,color:'var(--green)'},
              {label:'Position Value',value:`$${(pf.position_value||0).toLocaleString(undefined,{maximumFractionDigits:0})}`,color:'var(--blue)'},
            ].map((l,i)=>(<div key={i} style={{textAlign:'center',padding:16,background:'var(--bg-secondary)',borderRadius:'var(--radius-sm)'}}>
              <div style={{fontSize:10,color:'var(--text-muted)',textTransform:'uppercase',letterSpacing:1}}>{l.label}</div>
              <div className="mono" style={{fontSize:20,fontWeight:700,color:l.color,marginTop:4}}>{l.value}</div>
            </div>))}
          </div>
          <div style={{marginTop:16}}>
            {[
              ['Realized P&L',`$${(pf.pnl_realized||0).toFixed(2)}`],
              ['Unrealized P&L',`$${(pf.pnl_unrealized||0).toFixed(2)}`],
              ['Total P&L',`$${(pf.pnl_total||0).toFixed(2)}`],
              ['Return',`${(pf.return_pct||0).toFixed(2)}%`],
            ].map(([k,v],i)=>(<div key={i} style={{display:'flex',justifyContent:'space-between',padding:'6px 0',borderBottom:'1px solid var(--border-color)'}}>
              <span style={{fontSize:12,color:'var(--text-muted)'}}>{k}</span>
              <span className="mono" style={{fontSize:12,color:'var(--text-bright)'}}>{v}</span>
            </div>))}
          </div>
        </div>
      </div>

      <div className="card animate-in">
        <div className="card-header"><span className="card-title">Recent Orders</span><span className="card-badge badge-gold">{trades.length} orders</span></div>
        <table className="data-table">
          <thead><tr><th>ID</th><th>Time</th><th>Model</th><th>Side</th><th>Entry</th><th>Exit</th><th>P&L</th><th>Status</th></tr></thead>
          <tbody>
            {trades.map((t,i)=>(<tr key={i}>
              <td className="mono" style={{fontSize:11}}>{(t.trade_id||'').toString().slice(0,10)}</td>
              <td className="mono" style={{fontSize:12}}>{t.created_at?new Date(t.created_at).toLocaleTimeString():'—'}</td>
              <td style={{fontSize:12}}>{t.model_name||'—'}</td>
              <td><span style={{color:t.signal_type==='LONG'?'var(--green)':'var(--red)',fontWeight:600,fontSize:12}}>{t.signal_type||'—'}</span></td>
              <td className="mono">${Number(t.entry_price||0).toFixed(2)}</td>
              <td className="mono">{t.exit_price?`$${Number(t.exit_price).toFixed(2)}`:'—'}</td>
              <td className="mono" style={{color:(t.pnl||0)>=0?'var(--green)':'var(--red)',fontWeight:600}}>{(t.pnl||0)>=0?'+':''}${(t.pnl||0).toFixed(2)}</td>
              <td><span className={`card-badge ${t.status==='CLOSED'?'badge-green':'badge-blue'}`}>{t.status||'OPEN'}</span></td>
            </tr>))}
          </tbody>
        </table>
      </div>
    </div>
  </>);
}
