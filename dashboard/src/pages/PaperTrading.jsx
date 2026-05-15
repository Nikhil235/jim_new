import { useState, useEffect, useCallback } from 'react';
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Play, Pause, Square, DollarSign, TrendingUp, Activity, Target, ArrowUpRight, ArrowDownRight, Minus, Wifi, WifiOff, RefreshCw } from 'lucide-react';
import { startPaperTrading, stopPaperTrading, fetchPaperTradingStatus, fetchPaperTradingPerformance, fetchPaperTradingTrades, fetchLiveSignals, fetchRiskReport, resetDailyCounters, injectSignal } from '../data/api';
import { paperTrading as mockPT, stressTestData, dynamicRisk, featureDrift } from '../data/mockData';

const signalColor = (s) => s === 'LONG' ? 'var(--green)' : s === 'SHORT' ? 'var(--red)' : 'var(--text-muted)';
const signalBg = (s) => s === 'LONG' ? 'var(--green-dim)' : s === 'SHORT' ? 'var(--red-dim)' : 'var(--bg-input)';
const signalIcon = (s) => s === 'LONG' ? <ArrowUpRight size={12}/> : s === 'SHORT' ? <ArrowDownRight size={12}/> : <Minus size={12}/>;
const CTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (<div className="custom-tooltip"><div className="label">{label}</div>
    {payload.map((p, i) => (<div key={i} className="value" style={{ color: p.color }}>{p.name}: {typeof p.value === 'number' ? p.value.toLocaleString(undefined,{maximumFractionDigits:2}) : p.value}</div>))}
  </div>);
};

export default function PaperTrading() {
  const [live, setLive] = useState(false);
  const [status, setStatus] = useState(null);
  const [perf, setPerf] = useState(null);
  const [trades, setTrades] = useState([]);
  const [signals, setSignals] = useState(null);
  const [risk, setRisk] = useState(null);
  const [eqHistory, setEqHistory] = useState([]);
  const [pnlHistory, setPnlHistory] = useState([]);
  const [starting, setStarting] = useState(false);
  const [config, setConfig] = useState({ initial_capital:100000, kelly_fraction:0.25, max_position_pct:0.10, max_daily_loss_pct:0.02, max_drawdown_pct:0.15, min_confidence:0.60 });

  const refresh = useCallback(async () => {
    try {
      const s = await fetchPaperTradingStatus();
      setStatus(s); setLive(true);
      if (s?.portfolio?.total_value) {
        setEqHistory(prev => {
          const n = [...prev, { date: new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'}), equity: s.portfolio.total_value }];
          return n.length > 300 ? n.slice(-300) : n;
        });
      }
    } catch { setLive(false); setStatus(null); }
    try { setPerf(await fetchPaperTradingPerformance()); } catch {}
    try { setTrades(await fetchPaperTradingTrades(20)); } catch {}
    try { setSignals(await fetchLiveSignals()); } catch {}
    try { setRisk(await fetchRiskReport()); } catch {}
  }, []);

  useEffect(() => { refresh(); const t = setInterval(refresh, 5000); return () => clearInterval(t); }, [refresh]);

  const handleStart = async () => {
    setStarting(true);
    try { await startPaperTrading(config); refresh(); } catch(e) { alert('Start failed: ' + e.message); }
    setStarting(false);
  };
  const handleStop = async () => { if(!confirm('Stop engine?')) return; try { await stopPaperTrading(); refresh(); } catch(e) { alert(e.message); } };
  const handleReset = async () => { try { await resetDailyCounters(); refresh(); } catch(e) { alert(e.message); } };

  const pt = status ? null : mockPT;
  const engineStatus = status?.status || pt?.status || 'NOT STARTED';
  const isRunning = engineStatus === 'RUNNING';
  const pf = status?.portfolio || pt?.portfolio || {};
  const totalValue = pf.total_value ?? pf.totalValue ?? 100000;
  const pnlTotal = pf.pnl_total ?? pf.pnlTotal ?? 0;
  const dailyPnl = pf.pnl_daily ?? pf.dailyPnl ?? 0;
  const returnPct = pf.return_pct ?? pf.returnPct ?? 0;
  const winRate = perf?.win_rate ?? pf.winRate ?? 0;
  const sharpe = perf?.sharpe_ratio ?? pf.sharpeRatio ?? 0;
  const maxDD = perf?.max_drawdown ?? pf.maxDrawdown ?? 0;
  const numTrades = perf?.num_trades ?? pf.numTrades ?? pf.num_trades ?? 0;

  const modelSigs = signals?.models || (pt ? pt.modelSignals : {});
  const equityData = eqHistory.length > 3 ? eqHistory : (pt?.equityCurve || []);
  const dailyPnlData = pt?.dailyPnLHistory || [];
  const tradeList = trades.length > 0 ? trades : (pt?.recentTrades || []);

  return (<>
    <div className="page-header">
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
        <div>
          <h2>📄 Paper Trading Engine</h2>
          <p>Phase 6B — Live simulated trading with 6-model signal generation, Kelly sizing & circuit breakers</p>
        </div>
        <div style={{display:'flex',alignItems:'center',gap:10}}>
          <div style={{display:'flex',alignItems:'center',gap:6,padding:'5px 12px',borderRadius:'var(--radius-sm)',fontSize:12,fontWeight:600,
            background:live?'var(--green-dim)':'var(--red-dim)',color:live?'var(--green)':'var(--red)',
            border:`1px solid ${live?'rgba(0,196,140,0.3)':'rgba(255,77,106,0.3)'}`}}>
            {live?<Wifi size={12}/>:<WifiOff size={12}/>} {live?'LIVE':'OFFLINE'}
          </div>
          <div style={{display:'flex',alignItems:'center',gap:6,padding:'6px 14px',borderRadius:'var(--radius-sm)',fontSize:12,fontWeight:600,
            background:isRunning?'var(--green-dim)':'var(--red-dim)',color:isRunning?'var(--green)':'var(--red)',
            border:`1px solid ${isRunning?'rgba(0,196,140,0.3)':'rgba(255,77,106,0.3)'}`}}>
            {isRunning?<Play size={12}/>:<Pause size={12}/>} {engineStatus}
          </div>
        </div>
      </div>
    </div>
    <div className="page-body">
      {/* Engine Controls */}
      {live && (
        <div className="card animate-in" style={{marginBottom:16}}>
          <div className="card-header"><span className="card-title">Engine Controls</span><span className="card-badge badge-gold">LIVE API</span></div>
          <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(140px,1fr))',gap:10,marginBottom:12}}>
            {[['Capital ($)',config.initial_capital,'initial_capital'],['Kelly Frac',config.kelly_fraction,'kelly_fraction'],['Max Pos %',config.max_position_pct,'max_position_pct'],
              ['Max Daily Loss %',config.max_daily_loss_pct,'max_daily_loss_pct'],['Max DD %',config.max_drawdown_pct,'max_drawdown_pct'],['Min Confidence',config.min_confidence,'min_confidence']
            ].map(([label,val,key])=>(
              <div key={key}>
                <div style={{fontSize:10,color:'var(--text-muted)',marginBottom:4}}>{label}</div>
                <input type="number" step="any" value={val} onChange={e=>setConfig(p=>({...p,[key]:parseFloat(e.target.value)||0}))}
                  style={{width:'100%',padding:'6px 10px',borderRadius:6,border:'1px solid var(--border-color)',background:'var(--bg-input)',color:'var(--text-bright)',fontFamily:'var(--font-mono)',fontSize:12}} />
              </div>
            ))}
          </div>
          <div style={{display:'flex',gap:10}}>
            <button onClick={handleStart} disabled={starting||isRunning} style={{padding:'8px 20px',borderRadius:6,border:'none',background:isRunning?'var(--bg-input)':'var(--green)',color:isRunning?'var(--text-muted)':'#000',fontWeight:600,cursor:isRunning?'not-allowed':'pointer',fontSize:12}}>
              <Play size={12} style={{marginRight:4,verticalAlign:'middle'}}/> {starting?'Starting...':'Start Engine'}
            </button>
            <button onClick={handleStop} disabled={!isRunning} style={{padding:'8px 20px',borderRadius:6,border:'none',background:isRunning?'var(--red)':'var(--bg-input)',color:isRunning?'#fff':'var(--text-muted)',fontWeight:600,cursor:isRunning?'pointer':'not-allowed',fontSize:12}}>
              <Square size={12} style={{marginRight:4,verticalAlign:'middle'}}/> Stop
            </button>
            <button onClick={handleReset} disabled={!isRunning} style={{padding:'8px 20px',borderRadius:6,border:'1px solid var(--border-color)',background:'var(--bg-secondary)',color:'var(--text-secondary)',fontWeight:600,cursor:isRunning?'pointer':'not-allowed',fontSize:12}}>
              <RefreshCw size={12} style={{marginRight:4,verticalAlign:'middle'}}/> Reset Daily
            </button>
          </div>
        </div>
      )}

      {/* KPIs */}
      <div className="kpi-grid" style={{gridTemplateColumns:'repeat(5,1fr)'}}>
        {[
          {label:'Portfolio Value',value:`$${totalValue.toLocaleString(undefined,{maximumFractionDigits:0})}`,change:`${returnPct>=0?'+':''}${returnPct.toFixed(2)}%`,positive:returnPct>=0,icon:<DollarSign size={16}/>},
          {label:'Total P&L',value:`${pnlTotal>=0?'+':''}$${Math.abs(pnlTotal).toLocaleString(undefined,{maximumFractionDigits:2})}`,change:`$${dailyPnl.toFixed(2)} today`,positive:pnlTotal>=0,icon:<TrendingUp size={16}/>},
          {label:'Win Rate',value:`${(winRate*100).toFixed(1)}%`,change:`${numTrades} trades`,positive:winRate>0.5,icon:<Target size={16}/>},
          {label:'Sharpe Ratio',value:sharpe.toFixed(2),change:'Annualized',positive:sharpe>1.5,icon:<Activity size={16}/>},
          {label:'Max Drawdown',value:`${maxDD.toFixed(2)}%`,change:'Peak-to-trough',positive:Math.abs(maxDD)<5,icon:<ArrowDownRight size={16}/>},
        ].map((kpi,i)=>(<div key={i} className="kpi-card animate-in">
          <div className="kpi-label"><span style={{width:28,height:28,borderRadius:8,display:'flex',alignItems:'center',justifyContent:'center',background:'var(--gold-glow)',color:'var(--gold-primary)'}}>{kpi.icon}</span> {kpi.label}</div>
          <div className="kpi-value">{kpi.value}</div>
          <div className={`kpi-change ${kpi.positive?'positive':'negative'}`}>{kpi.change}</div>
        </div>))}
      </div>

      {/* Equity + Daily PnL */}
      <div className="grid-2" style={{marginBottom:20}}>
        <div className="card animate-in">
          <div className="card-header"><span className="card-title">Equity Curve</span><span className={`card-badge ${live?'badge-green':'badge-orange'}`}>{live?'LIVE':'MOCK'}</span></div>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={equityData}>
              <defs><linearGradient id="eqG2" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#f0b90b" stopOpacity={0.3}/><stop offset="100%" stopColor="#f0b90b" stopOpacity={0}/></linearGradient></defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)"/>
              <XAxis dataKey="date" tick={{fill:'#6b7280',fontSize:10}} tickFormatter={v=>typeof v==='string'&&v.length>5?v.slice(5):v}/>
              <YAxis tick={{fill:'#6b7280',fontSize:10}} tickFormatter={v=>`$${(v/1000).toFixed(0)}k`} domain={['dataMin-500','dataMax+500']}/>
              <Tooltip content={<CTooltip/>}/><Area type="monotone" dataKey="equity" stroke="#f0b90b" fill="url(#eqG2)" strokeWidth={2} name="Equity"/>
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="card animate-in">
          <div className="card-header"><span className="card-title">Daily P&L</span><span className="card-badge badge-blue">HISTORY</span></div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={dailyPnlData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)"/>
              <XAxis dataKey="date" tick={{fill:'#6b7280',fontSize:10}} tickFormatter={v=>v.slice(5)}/>
              <YAxis tick={{fill:'#6b7280',fontSize:10}} tickFormatter={v=>`$${v}`}/>
              <Tooltip content={<CTooltip/>}/>
              <Bar dataKey="pnl" radius={[4,4,0,0]} name="P&L">{dailyPnlData.map((d,i)=>(<Cell key={i} fill={d.pnl>=0?'#00c48c':'#ff4d6a'}/>))}</Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Model Signals + Trade History */}
      <div className="grid-2" style={{marginBottom:20}}>
        <div className="card animate-in">
          <div className="card-header"><span className="card-title">Model Signal Status</span><span className="card-badge badge-gold">6 MODELS</span></div>
          <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:10}}>
            {Object.entries(modelSigs).map(([model,sig])=>{
              const s = sig.signal || sig.lastSignal || 'HOLD';
              const c = sig.confidence ?? 0;
              return (<div key={model} style={{padding:14,borderRadius:'var(--radius-sm)',background:'var(--bg-secondary)',border:'1px solid var(--border-color)'}}>
                <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:8}}>
                  <span style={{fontSize:13,fontWeight:600,color:'var(--text-bright)',textTransform:'capitalize'}}>{model}</span>
                  <span style={{fontSize:10,fontWeight:700,padding:'3px 8px',borderRadius:12,background:signalBg(s),color:signalColor(s),display:'flex',alignItems:'center',gap:4}}>
                    {signalIcon(s)} {s}
                  </span>
                </div>
                <div style={{display:'flex',justifyContent:'space-between',fontSize:11,color:'var(--text-muted)'}}>
                  <span>Conf: <span style={{color:c>=0.7?'var(--green)':c>=0.6?'var(--orange)':'var(--red)',fontWeight:600,fontFamily:'var(--font-mono)'}}>{(c*100).toFixed(0)}%</span></span>
                  <span>{sig.signalCount||sig.regime||'—'}</span>
                </div>
                <div style={{marginTop:6}}><div className="progress-bar"><div className="progress-fill" style={{width:`${c*100}%`,background:c>=0.7?'var(--green)':c>=0.6?'var(--orange)':'var(--red)'}}/></div></div>
                {sig.reasoning && <div style={{fontSize:9,color:'var(--text-muted)',marginTop:4,fontStyle:'italic'}}>{sig.reasoning.slice(0,80)}</div>}
              </div>);
            })}
          </div>
        </div>
        <div className="card animate-in">
          <div className="card-header"><span className="card-title">Recent Trades</span><span className="card-badge badge-purple">{tradeList.length} TRADES</span></div>
          <table className="data-table"><thead><tr><th>ID</th><th>Model</th><th>Signal</th><th>Entry</th><th>Exit</th><th>P&L</th><th>Status</th></tr></thead>
            <tbody>{tradeList.map((t,i)=>{
              const id = t.trade_id||t.tradeId||`#${i}`;
              const model = t.model_name||t.model||'—';
              const sig = t.signal_type||t.signal||'—';
              const entry = t.entry_price||t.entry||0;
              const exit = t.exit_price||t.exit||null;
              const pnl = t.pnl||0;
              const st = t.status||'OPEN';
              return (<tr key={i}>
                <td className="mono">{typeof id==='string'?id.slice(0,8):id}</td>
                <td style={{fontWeight:600}}>{model}</td>
                <td><span style={{color:signalColor(sig),fontWeight:600,fontSize:11}}>{sig}</span></td>
                <td className="mono">${Number(entry).toFixed(2)}</td>
                <td className="mono">{exit?`$${Number(exit).toFixed(2)}`:'—'}</td>
                <td className="mono" style={{color:pnl>=0?'var(--green)':'var(--red)',fontWeight:600}}>{pnl>=0?'+':''}${Number(pnl).toFixed(2)}</td>
                <td><span className={`card-badge ${st==='CLOSED'?'badge-green':'badge-blue'}`}>{st}</span></td>
              </tr>);
            })}</tbody>
          </table>
        </div>
      </div>

      {/* Risk Report (live) */}
      {risk?.risk_report && (
        <div className="card animate-in" style={{marginBottom:20}}>
          <div className="card-header"><span className="card-title">Live Risk Report</span><span className="card-badge badge-red">REAL-TIME</span></div>
          <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(200px,1fr))',gap:16}}>
            {[
              {label:'Current Equity',value:`$${risk.risk_report.current_equity?.toLocaleString(undefined,{maximumFractionDigits:0})}`},
              {label:'Peak Equity',value:`$${risk.risk_report.peak_equity?.toLocaleString(undefined,{maximumFractionDigits:0})}`},
              {label:'Drawdown',value:`${risk.risk_report.drawdown_pct?.toFixed(2)}%`},
              {label:'Daily P&L',value:`$${risk.risk_report.daily_pnl?.toFixed(2)}`},
              {label:'Consecutive Losses',value:risk.risk_report.consecutive_losses},
              {label:'Violations',value:risk.risk_report.violations?.length?risk.risk_report.violations.join(', '):'None ✓'},
            ].map((r,i)=>(<div key={i} style={{padding:'10px 14px',borderRadius:'var(--radius-sm)',background:'var(--bg-secondary)',border:'1px solid var(--border-color)'}}>
              <div style={{fontSize:10,color:'var(--text-muted)',textTransform:'uppercase',letterSpacing:0.5}}>{r.label}</div>
              <div style={{fontSize:15,fontWeight:600,fontFamily:'var(--font-mono)',color:'var(--text-bright)',marginTop:4}}>{r.value}</div>
            </div>))}
          </div>
        </div>
      )}

      {/* Config Summary */}
      <div className="card animate-in">
        <div className="card-header"><span className="card-title">Paper Trading Configuration</span><span className="card-badge badge-gold">XAUUSD</span></div>
        <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(200px,1fr))',gap:16}}>
          {[
            {label:'Initial Capital',value:`$${config.initial_capital.toLocaleString()}`},
            {label:'Kelly Fraction',value:config.kelly_fraction.toFixed(2)},
            {label:'Max Position %',value:`${(config.max_position_pct*100).toFixed(0)}%`},
            {label:'Max Daily Loss',value:`${(config.max_daily_loss_pct*100).toFixed(1)}%`},
            {label:'Max Drawdown',value:`${(config.max_drawdown_pct*100).toFixed(0)}%`},
            {label:'Min Confidence',value:`${(config.min_confidence*100).toFixed(0)}%`},
          ].map((c,i)=>(<div key={i} style={{padding:'10px 14px',borderRadius:'var(--radius-sm)',background:'var(--bg-secondary)',border:'1px solid var(--border-color)'}}>
            <div style={{fontSize:10,color:'var(--text-muted)',textTransform:'uppercase',letterSpacing:0.5}}>{c.label}</div>
            <div style={{fontSize:15,fontWeight:600,fontFamily:'var(--font-mono)',color:'var(--text-bright)',marginTop:4}}>{c.value}</div>
          </div>))}
        </div>
      </div>
    </div>
  </>);
}
