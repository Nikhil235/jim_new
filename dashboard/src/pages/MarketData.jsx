import { useState, useEffect, useRef } from 'react';
import { XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, ComposedChart, Line, Area } from 'recharts';
import { Wifi, WifiOff, RefreshCw } from 'lucide-react';
import { fetchGoldPrice, fetchPaperTradingTrades } from '../data/api';

const Candlestick = (props) => {
  const { x, y, width, height, payload } = props;
  if (!payload || payload.high === undefined) return null;
  const { open, close, high, low, pattern } = payload;
  const isGrowing = close >= open;
  const color = isGrowing ? 'var(--green)' : 'var(--red)';
  const ratio = height === 0 || high === low ? 0 : Math.abs(height / (high - low));
  const yOpen = y + (high - open) * ratio;
  const yClose = y + (high - close) * ratio;
  const bodyTop = Math.min(yOpen, yClose);
  const bodyHeight = Math.max(Math.abs(yOpen - yClose), 1);
  
  let icon = null;
  if (pattern) {
    if (pattern.includes('Doji')) icon = '⚖️';
    else if (pattern.includes('Hammer')) icon = '🔨';
    else if (pattern.includes('Shooting')) icon = '☄️';
    else if (pattern.includes('Engulfing')) icon = isGrowing ? '📈' : '📉';
    else if (pattern.includes('Marubozu')) icon = isGrowing ? '🟩' : '🟥';
  }

  const trades = payload.trades || [];

  return (
    <g stroke={color} fill={color} strokeWidth="1.5">
      <line x1={x + width / 2} y1={y} x2={x + width / 2} y2={y + height} />
      <rect x={x + width * 0.2} y={bodyTop} width={width * 0.6} height={bodyHeight} />
      {icon && <text x={x + width / 2} y={y - 8} fontSize="12" textAnchor="middle">{icon}</text>}
      {trades.map((t, idx) => {
        const ty = high === low ? y : y + (high - t.entry_price) * ratio;
        const tColor = t.signal_type === 'LONG' ? '#00e676' : '#ff1744';
        return (
          <g key={idx} 
             onClick={() => { if(props.onTradeClick) props.onTradeClick(t); }}
             style={{ cursor: 'pointer' }}
             className="trade-marker">
            <circle cx={x + width / 2} cy={ty} r="6" fill={tColor} stroke="var(--bg-card)" strokeWidth="1.5" />
            <text x={x + width / 2 + 10} y={ty + 3} fontSize="10" fill={tColor} fontWeight="bold">{t.signal_type}</text>
          </g>
        );
      })}
    </g>
  );
};

const TT = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  const p = payload[0]?.payload;
  const isCandle = p && 'open' in p && 'close' in p && 'high' in p;
  
  return (<div className="custom-tooltip"><div className="label">{label}</div>
    {isCandle && payload.some(x => x.name === 'Price') && (
      <>
        <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:'2px 8px', marginBottom:6, fontSize:11}}>
          <div style={{color:'var(--text-bright)'}}>O: {p.open?.toFixed(2)}</div>
          <div style={{color:'var(--green)'}}>H: {p.high?.toFixed(2)}</div>
          <div style={{color:'var(--red)'}}>L: {p.low?.toFixed(2)}</div>
          <div style={{color:'var(--text-bright)'}}>C: {p.close?.toFixed(2)}</div>
        </div>
        {p.pattern && <div style={{color:'var(--gold-primary)', fontSize:11, marginBottom:4, fontWeight:600}}>✨ {p.pattern}</div>}
        {p.trades && p.trades.length > 0 && (
          <div style={{marginTop: 4, paddingTop: 4, borderTop: '1px solid var(--border-color)'}}>
            {p.trades.map((t, i) => (
              <div key={i} style={{fontSize: 11, color: t.signal_type === 'LONG' ? 'var(--green)' : 'var(--red)', fontWeight: 600}}>
                {t.signal_type} @ {t.entry_price.toFixed(2)} ({t.model_name})
              </div>
            ))}
          </div>
        )}
      </>
    )}
    {payload.filter(x => x.name !== 'Price').map((p, i) => <div key={i} className="value" style={{ color: p.color }}>{p.name}: {p.value?.toLocaleString?.() ?? p.value}</div>)}
  </div>);
};

export default function MarketData() {
  const [live, setLive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [goldData, setGoldData] = useState(null);
  const [trades, setTrades] = useState([]);
  const [period, setPeriod] = useState('3mo');
  const [interval, setInterval_] = useState('1d');
  const [selectedTrade, setSelectedTrade] = useState(null);
  const [activeIndicator, setActiveIndicator] = useState('RSI');
  const [showBollinger, setShowBollinger] = useState(false);

  const refreshRef = useRef(null);
  refreshRef.current = async () => {
    setLoading(true);
    try {
      const data = await fetchGoldPrice(interval, period);
      setGoldData(data);
      try {
        const t = await fetchPaperTradingTrades(100);
        setTrades(t || []);
      } catch (err) { console.warn("Could not fetch trades", err); }
      setLive(true);
    } catch { /* offline */ }
    setLoading(false);
  };

  useEffect(() => { refreshRef.current?.(); const t = setInterval(() => refreshRef.current?.(), 30000); return () => clearInterval(t); }, [interval, period]);

  const candles = goldData?.candles || [];
  const chartData = candles.map((c, i) => {
    const now = Date.now();
    const nextTime = i < candles.length - 1 ? candles[i + 1].time : now;
    const cTrades = trades.filter(t => {
      const time = new Date(t.entry_time).getTime();
      return time >= c.time && time < nextTime;
    });
    return {
      date: new Date(c.time).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
      open: c.open, high: c.high, low: c.low, close: c.close,
      range: [c.low, c.high],
      volume: c.volume || 0,
      sma20: c.close,
      pattern: c.pattern || null,
      trades: cTrades,
    };
  });

  // Compute RSI from closes
  const closes = chartData.map(d => d.close);
  
  // Calculate EMA
  const calcEma = (data, period) => {
    const k = 2 / (period + 1);
    let emaData = [];
    let ema = data[0];
    for (let i = 0; i < data.length; i++) {
      ema = data[i] * k + ema * (1 - k);
      emaData.push(ema);
    }
    return emaData;
  };

  const ema12 = calcEma(closes, 12);
  const ema26 = calcEma(closes, 26);
  const macdLine = ema12.map((val, i) => val - ema26[i]);
  const signalLine = calcEma(macdLine, 9);
  const macdHist = macdLine.map((val, i) => val - signalLine[i]);

  const indicatorsData = chartData.map((d, i) => {
    // RSI
    let rsi = 50;
    if (i >= 14) {
      const gains = [], losses = [];
      for (let j = i - 13; j <= i; j++) {
        const diff = closes[j] - closes[j - 1];
        if (diff > 0) { gains.push(diff); losses.push(0); }
        else { gains.push(0); losses.push(Math.abs(diff)); }
      }
      const avgGain = gains.reduce((a, b) => a + b, 0) / 14;
      const avgLoss = losses.reduce((a, b) => a + b, 0) / 14;
      const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
      rsi = +(100 - 100 / (1 + rs)).toFixed(1);
    }

    // Bollinger Bands (20, 2)
    let sma20 = d.close;
    let upperBb = d.close;
    let lowerBb = d.close;
    if (i >= 19) {
      const slice = closes.slice(i - 19, i + 1);
      sma20 = slice.reduce((a, b) => a + b, 0) / 20;
      const variance = slice.reduce((a, b) => a + Math.pow(b - sma20, 2), 0) / 20;
      const stdDev = Math.sqrt(variance);
      upperBb = sma20 + stdDev * 2;
      lowerBb = sma20 - stdDev * 2;
    }

    // ATR (14)
    let atr = 0;
    if (i >= 14) {
      let trSum = 0;
      for (let j = i - 13; j <= i; j++) {
        const h = chartData[j].high;
        const l = chartData[j].low;
        const pc = chartData[j - 1].close;
        const tr = Math.max(h - l, Math.abs(h - pc), Math.abs(l - pc));
        trSum += tr;
      }
      atr = +(trSum / 14).toFixed(2);
    }

    return { 
      ...d, 
      rsi, ob: 70, os: 30,
      macd: +macdLine[i].toFixed(2), 
      macdSignal: +signalLine[i].toFixed(2), 
      macdHist: +macdHist[i].toFixed(2),
      sma20: +sma20.toFixed(2),
      upperBb: +upperBb.toFixed(2),
      lowerBb: +lowerBb.toFixed(2),
      atr
    };
  });

  const latest = chartData[chartData.length - 1] || {};
  const latestInd = indicatorsData[indicatorsData.length - 1] || {};
  const latestRsi = latestInd.rsi || 50;

  if (!live && !loading) return (
    <><div className="page-header"><h2>Market Data</h2><p>⚠ Backend offline — start the API server to see live gold prices</p></div>
    <div className="page-body"><div className="card" style={{padding:40,textAlign:'center',color:'var(--text-muted)'}}>
      <WifiOff size={48} style={{margin:'0 auto 16px',opacity:0.3}}/><div style={{fontSize:16,fontWeight:600}}>No Connection</div>
      <div style={{fontSize:12,marginTop:8}}>Run <code style={{background:'var(--bg-input)',padding:'2px 8px',borderRadius:4}}>python -m uvicorn src.api.app:app --port 8000</code> to start</div>
      <button onClick={() => refreshRef.current?.()} style={{marginTop:16,padding:'8px 20px',borderRadius:6,border:'1px solid var(--border-color)',background:'var(--bg-secondary)',color:'var(--text-secondary)',cursor:'pointer',fontSize:12}}><RefreshCw size={12} style={{marginRight:4,verticalAlign:'middle'}}/> Retry</button>
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
        <div className="card-header">
          <span className="card-title">Price Chart</span>
          <div style={{display:'flex',gap:8,alignItems:'center'}}>
            <label style={{fontSize:11,color:'var(--text-muted)',display:'flex',alignItems:'center',gap:4,cursor:'pointer'}}>
              <input type="checkbox" checked={showBollinger} onChange={e=>setShowBollinger(e.target.checked)} />
              Bollinger Bands
            </label>
            <span className="card-badge badge-gold">{period.toUpperCase()} / {interval}</span>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={320}>
          <ComposedChart data={indicatorsData}>
            <XAxis dataKey="date" tick={{fontSize:10,fill:'#6b7280'}} tickFormatter={v=>v} interval={Math.max(1,Math.floor(chartData.length/10))}/>
            <YAxis tick={{fontSize:10,fill:'#6b7280'}} domain={['auto','auto']}/>
            <Tooltip content={<TT/>}/>
            {showBollinger && <Area type="monotone" dataKey="upperBb" stroke="none" fill="rgba(0,196,140,0.05)" />}
            {showBollinger && <Area type="monotone" dataKey="lowerBb" stroke="none" fill="rgba(0,196,140,0.05)" />}
            {showBollinger && <Line type="monotone" dataKey="upperBb" stroke="rgba(0,196,140,0.4)" strokeDasharray="3 3" dot={false} name="Upper BB" />}
            {showBollinger && <Line type="monotone" dataKey="lowerBb" stroke="rgba(0,196,140,0.4)" strokeDasharray="3 3" dot={false} name="Lower BB" />}
            {showBollinger && <Line type="monotone" dataKey="sma20" stroke="rgba(240,185,11,0.4)" dot={false} name="SMA 20" />}
            <Bar dataKey="range" shape={<Candlestick onTradeClick={setSelectedTrade} />} name="Price" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {selectedTrade && (
        <div className="card animate-in" style={{marginBottom: 16, border: `1px solid ${selectedTrade.signal_type === 'LONG' ? 'rgba(0,230,118,0.3)' : 'rgba(255,23,68,0.3)'}`}}>
          <div className="card-header" style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
            <span className="card-title">
              <span style={{color: selectedTrade.signal_type === 'LONG' ? 'var(--green)' : 'var(--red)', marginRight: 8}}>
                {selectedTrade.signal_type}
              </span>
              Trade Details
            </span>
            <button onClick={() => setSelectedTrade(null)} className="btn btn-sm" style={{background:'transparent', border:'1px solid var(--border-color)', color:'var(--text-muted)'}}>Close</button>
          </div>
          <div style={{display:'grid', gridTemplateColumns:'repeat(4, 1fr)', gap: 16, padding: 16}}>
            <div>
              <div style={{fontSize: 11, color: 'var(--text-muted)'}}>Model</div>
              <div className="mono" style={{fontWeight: 600}}>{selectedTrade.model_name}</div>
            </div>
            <div>
              <div style={{fontSize: 11, color: 'var(--text-muted)'}}>Confidence</div>
              <div className="mono" style={{fontWeight: 600}}>{(selectedTrade.confidence * 100).toFixed(1)}%</div>
            </div>
            <div>
              <div style={{fontSize: 11, color: 'var(--text-muted)'}}>Entry Price</div>
              <div className="mono" style={{fontWeight: 600}}>${selectedTrade.entry_price?.toFixed(2)}</div>
            </div>
            <div>
              <div style={{fontSize: 11, color: 'var(--text-muted)'}}>Market Regime</div>
              <div className="mono" style={{fontWeight: 600}}>{selectedTrade.regime}</div>
            </div>
          </div>
        </div>
      )}

      <div className="grid-2">
        <div className="card animate-in">
          <div className="card-header"><span className="card-title">Volume</span></div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={indicatorsData.slice(-30)}>
              <XAxis dataKey="date" tick={{fontSize:9,fill:'#6b7280'}}/>
              <YAxis tick={{fontSize:10,fill:'#6b7280'}} tickFormatter={v=>`${(v/1000).toFixed(0)}k`}/>
              <Tooltip content={<TT/>}/>
              <Bar dataKey="volume" name="Volume" fill="rgba(240,185,11,0.4)" radius={[3,3,0,0]}/>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card animate-in">
          <div className="card-header">
            <span className="card-title">Technical Indicators</span>
            <div style={{display:'flex', gap:4}}>
              {['RSI', 'MACD', 'ATR'].map(ind => (
                <button 
                  key={ind} 
                  onClick={() => setActiveIndicator(ind)}
                  className={`badge-${activeIndicator === ind ? 'blue' : 'gray'}`}
                  style={{border:'none', cursor:'pointer', padding:'2px 8px', borderRadius:4, fontSize:10, fontWeight:600}}
                >
                  {ind}
                </button>
              ))}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            {activeIndicator === 'RSI' ? (
              <ComposedChart data={indicatorsData.slice(-30)}>
                <XAxis dataKey="date" tick={{fontSize:9,fill:'#6b7280'}}/>
                <YAxis tick={{fontSize:10,fill:'#6b7280'}} domain={[0,100]}/>
                <Tooltip content={<TT/>}/>
                <Area type="monotone" dataKey="rsi" stroke="#f0b90b" strokeWidth={2} fill="rgba(240,185,11,0.1)" name="RSI"/>
                <Line type="monotone" dataKey="ob" stroke="rgba(255,77,106,0.4)" strokeDasharray="4 4" dot={false} name="Overbought"/>
                <Line type="monotone" dataKey="os" stroke="rgba(0,196,140,0.4)" strokeDasharray="4 4" dot={false} name="Oversold"/>
              </ComposedChart>
            ) : activeIndicator === 'MACD' ? (
              <ComposedChart data={indicatorsData.slice(-30)}>
                <XAxis dataKey="date" tick={{fontSize:9,fill:'#6b7280'}}/>
                <YAxis tick={{fontSize:10,fill:'#6b7280'}} domain={['auto','auto']}/>
                <Tooltip content={<TT/>}/>
                <Bar dataKey="macdHist" name="Histogram" fill="rgba(240,185,11,0.4)" />
                <Line type="monotone" dataKey="macd" stroke="#00c48c" strokeWidth={2} dot={false} name="MACD" />
                <Line type="monotone" dataKey="macdSignal" stroke="#ff4d6a" strokeWidth={2} dot={false} name="Signal" />
              </ComposedChart>
            ) : (
              <ComposedChart data={indicatorsData.slice(-30)}>
                <XAxis dataKey="date" tick={{fontSize:9,fill:'#6b7280'}}/>
                <YAxis tick={{fontSize:10,fill:'#6b7280'}} domain={['auto','auto']}/>
                <Tooltip content={<TT/>}/>
                <Area type="monotone" dataKey="atr" stroke="#3b82f6" strokeWidth={2} fill="rgba(59,130,246,0.1)" name="ATR (14)"/>
              </ComposedChart>
            )}
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  </>);
}
