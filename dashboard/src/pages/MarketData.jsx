import { useState, useEffect, useCallback } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, ComposedChart, Line } from 'recharts';
import { Wifi, WifiOff, RefreshCw } from 'lucide-react';
import { fetchGoldPrice, fetchFeatures } from '../data/api';

const TT = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (<div className="custom-tooltip"><div className="label">{label}</div>
    {payload.map((p, i) => <div key={i} className="value" style={{ color: p.color }}>{p.name}: {p.value?.toLocaleString?.() ?? p.value}</div>)}
  </div>);
};

export default function MarketData() {
  const [live, setLive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [goldData, setGoldData] = useState(null);
  const [period, setPeriod] = useState('3mo');
  const [interval, setInterval_] = useState('1d');

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchGoldPrice(interval, period);
      setGoldData(data);
      setLive(true);
    } catch { setLive(false); }
    setLoading(false);
  }, [interval, period]);

  useEffect(() => { refresh(); const t = setInterval(refresh, 30000); return () => clearInterval(t); }, [refresh]);

  const candles = goldData?.candles || [];
  const chartData = candles.map(c => ({
    date: new Date(c.time).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    open: c.open, high: c.high, low: c.low, close: c.close,
    volume: c.volume || 0,
    sma20: c.close, // compute simple SMA inline
  }));

  // Compute RSI from closes
  const closes = chartData.map(d => d.close);
  const rsiData = chartData.map((d, i) => {
    if (i < 14) return { ...d, rsi: 50, ob: 70, os: 30 };
    const gains = [], losses = [];
    for (let j = i - 13; j <= i; j++) {
      const diff = closes[j] - closes[j - 1];
      if (diff > 0) { gains.push(diff); losses.push(0); }
      else { gains.push(0); losses.push(Math.abs(diff)); }
    }
    const avgGain = gains.reduce((a, b) => a + b, 0) / 14;
    const avgLoss = losses.reduce((a, b) => a + b, 0) / 14;
    const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
    return { ...d, rsi: +(100 - 100 / (1 + rs)).toFixed(1), ob: 70, os: 30 };
  });

  const latest = chartData[chartData.length - 1] || {};
  const latestRsi = rsiData[rsiData.length - 1]?.rsi || 50;

  if (!live && !loading) return (
    <><div className="page-header"><h2>Market Data</h2><p>⚠ Backend offline — start the API server to see live gold prices</p></div>
    <div className="page-body"><div className="card" style={{padding:40,textAlign:'center',color:'var(--text-muted)'}}>
      <WifiOff size={48} style={{margin:'0 auto 16px',opacity:0.3}}/><div style={{fontSize:16,fontWeight:600}}>No Connection</div>
      <div style={{fontSize:12,marginTop:8}}>Run <code style={{background:'var(--bg-input)',padding:'2px 8px',borderRadius:4}}>python -m uvicorn src.api.app:app --port 8000</code> to start</div>
      <button onClick={refresh} style={{marginTop:16,padding:'8px 20px',borderRadius:6,border:'1px solid var(--border-color)',background:'var(--bg-secondary)',color:'var(--text-secondary)',cursor:'pointer',fontSize:12}}><RefreshCw size={12} style={{marginRight:4,verticalAlign:'middle'}}/> Retry</button>
    </div></div></>
  );

  return (<>
    <div className="page-header">
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
        <div><h2>Market Data</h2><p>Gold (XAU/USD) — Live price action, indicators & volume from API</p></div>
        <div style={{display:'flex',alignItems:'center',gap:8}}>
          <select value={period} onChange={e=>setPeriod(e.target.value)} style={{padding:'5px 10px',borderRadius:6,border:'1px solid var(--border-color)',background:'var(--bg-input)',color:'var(--text-bright)',fontSize:11}}>
            {['1d','5d','1mo','3mo','6mo','1y','2y'].map(p=><option key={p} value={p}>{p}</option>)}
          </select>
          <select value={interval} onChange={e=>setInterval_(e.target.value)} style={{padding:'5px 10px',borderRadius:6,border:'1px solid var(--border-color)',background:'var(--bg-input)',color:'var(--text-bright)',fontSize:11}}>
            {['1m','5m','15m','1h','1d','1wk'].map(i=><option key={i} value={i}>{i}</option>)}
          </select>
          <div style={{display:'flex',alignItems:'center',gap:6,padding:'5px 12px',borderRadius:'var(--radius-sm)',fontSize:11,fontWeight:600,background:'var(--green-dim)',color:'var(--green)',border:'1px solid rgba(0,196,140,0.3)'}}>
            <Wifi size={12}/> LIVE
          </div>
        </div>
      </div>
    </div>
    <div className="page-body">
      <div className="kpi-grid" style={{gridTemplateColumns:'repeat(5,1fr)',marginBottom:20}}>
        {[['Close',`$${latest.close?.toFixed(2)||'—'}`],['High',`$${latest.high?.toFixed(2)||'—'}`],['Low',`$${latest.low?.toFixed(2)||'—'}`],['Volume',(latest.volume||0).toLocaleString()],['RSI(14)',`${latestRsi}`]].map(([l,v],i)=>(
          <div key={i} className="kpi-card animate-in"><div className="kpi-label">{l}</div><div className="kpi-value" style={{fontSize:20}}>{v}</div></div>
        ))}
      </div>

      <div className="card animate-in" style={{marginBottom:16}}>
        <div className="card-header"><span className="card-title">Price Chart</span><span className="card-badge badge-gold">{period.toUpperCase()} / {interval}</span></div>
        <ResponsiveContainer width="100%" height={320}>
          <ComposedChart data={chartData}>
            <defs><linearGradient id="pg2" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#f0b90b" stopOpacity={0.2}/><stop offset="100%" stopColor="#f0b90b" stopOpacity={0}/></linearGradient></defs>
            <XAxis dataKey="date" tick={{fontSize:10,fill:'#6b7280'}} tickFormatter={v=>v} interval={Math.max(1,Math.floor(chartData.length/10))}/>
            <YAxis tick={{fontSize:10,fill:'#6b7280'}} domain={['auto','auto']}/>
            <Tooltip content={<TT/>}/>
            <Area type="monotone" dataKey="close" stroke="#f0b90b" strokeWidth={2} fill="url(#pg2)" name="Close"/>
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="grid-2">
        <div className="card animate-in">
          <div className="card-header"><span className="card-title">Volume</span></div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData.slice(-30)}>
              <XAxis dataKey="date" tick={{fontSize:9,fill:'#6b7280'}}/>
              <YAxis tick={{fontSize:10,fill:'#6b7280'}} tickFormatter={v=>`${(v/1000).toFixed(0)}k`}/>
              <Tooltip content={<TT/>}/>
              <Bar dataKey="volume" name="Volume" fill="rgba(240,185,11,0.4)" radius={[3,3,0,0]}/>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card animate-in">
          <div className="card-header"><span className="card-title">RSI (14)</span><span className="card-badge badge-blue">{latestRsi>70?'OVERBOUGHT':latestRsi<30?'OVERSOLD':'NEUTRAL'} — {latestRsi}</span></div>
          <ResponsiveContainer width="100%" height={200}>
            <ComposedChart data={rsiData.slice(-30)}>
              <XAxis dataKey="date" tick={{fontSize:9,fill:'#6b7280'}}/>
              <YAxis tick={{fontSize:10,fill:'#6b7280'}} domain={[0,100]}/>
              <Tooltip content={<TT/>}/>
              <Area type="monotone" dataKey="rsi" stroke="#f0b90b" strokeWidth={2} fill="rgba(240,185,11,0.1)" name="RSI"/>
              <Line type="monotone" dataKey="ob" stroke="rgba(255,77,106,0.4)" strokeDasharray="4 4" dot={false} name="Overbought"/>
              <Line type="monotone" dataKey="os" stroke="rgba(0,196,140,0.4)" strokeDasharray="4 4" dot={false} name="Oversold"/>
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  </>);
}
