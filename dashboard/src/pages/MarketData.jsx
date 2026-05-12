import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, ComposedChart, Line } from 'recharts';
import { recentPrices, latestPrice } from '../data/mockData';

const TT = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="custom-tooltip">
      <div className="label">{label}</div>
      {payload.map((p, i) => <div key={i} className="value" style={{ color: p.color }}>{p.name}: {p.value?.toLocaleString?.() ?? p.value}</div>)}
    </div>
  );
};

export default function MarketData() {
  const last30 = recentPrices.slice(-30);
  const rsiData = recentPrices.map(d => ({ date: d.date, rsi: +d.rsi, ob: 70, os: 30 }));

  return (
    <>
      <div className="page-header">
        <h2>Market Data</h2>
        <p>Gold (XAU/USD) — Price action, indicators & volume</p>
      </div>
      <div className="page-body">
        <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(5,1fr)', marginBottom: 20 }}>
          {[['Close', `$${latestPrice.close}`], ['High', `$${latestPrice.high}`], ['Low', `$${latestPrice.low}`], ['Volume', latestPrice.volume.toLocaleString()], ['Volatility', `${latestPrice.volatility}%`]].map(([l, v], i) => (
            <div key={i} className="kpi-card animate-in"><div className="kpi-label">{l}</div><div className="kpi-value" style={{ fontSize: 20 }}>{v}</div></div>
          ))}
        </div>

        <div className="card animate-in" style={{ marginBottom: 16 }}>
          <div className="card-header"><span className="card-title">Price & Moving Averages</span><span className="card-badge badge-gold">90D</span></div>
          <ResponsiveContainer width="100%" height={320}>
            <ComposedChart data={recentPrices}>
              <defs><linearGradient id="pg2" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#f0b90b" stopOpacity={0.2} /><stop offset="100%" stopColor="#f0b90b" stopOpacity={0} /></linearGradient></defs>
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#6b7280' }} tickFormatter={v => v.slice(5)} interval={14} />
              <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} domain={['auto', 'auto']} />
              <Tooltip content={<TT />} />
              <Area type="monotone" dataKey="close" stroke="#f0b90b" strokeWidth={2} fill="url(#pg2)" name="Close" />
              <Line type="monotone" dataKey="sma20" stroke="#4da6ff" strokeWidth={1.5} dot={false} name="SMA 20" />
              <Line type="monotone" dataKey="sma50" stroke="#a855f7" strokeWidth={1.5} dot={false} name="SMA 50" strokeDasharray="5 5" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        <div className="grid-2">
          <div className="card animate-in">
            <div className="card-header"><span className="card-title">Volume</span></div>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={last30}>
                <XAxis dataKey="date" tick={{ fontSize: 9, fill: '#6b7280' }} tickFormatter={v => v.slice(8)} />
                <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} tickFormatter={v => `${(v/1000).toFixed(0)}k`} />
                <Tooltip content={<TT />} />
                <Bar dataKey="volume" name="Volume" fill="rgba(240,185,11,0.4)" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="card animate-in">
            <div className="card-header"><span className="card-title">RSI (14)</span><span className="card-badge badge-blue">NEUTRAL — {latestPrice.rsi}</span></div>
            <ResponsiveContainer width="100%" height={200}>
              <ComposedChart data={rsiData.slice(-30)}>
                <XAxis dataKey="date" tick={{ fontSize: 9, fill: '#6b7280' }} tickFormatter={v => v.slice(8)} />
                <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} domain={[0, 100]} />
                <Tooltip content={<TT />} />
                <Area type="monotone" dataKey="rsi" stroke="#f0b90b" strokeWidth={2} fill="rgba(240,185,11,0.1)" name="RSI" />
                <Line type="monotone" dataKey="ob" stroke="rgba(255,77,106,0.4)" strokeDasharray="4 4" dot={false} name="Overbought" />
                <Line type="monotone" dataKey="os" stroke="rgba(0,196,140,0.4)" strokeDasharray="4 4" dot={false} name="Oversold" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </>
  );
}
