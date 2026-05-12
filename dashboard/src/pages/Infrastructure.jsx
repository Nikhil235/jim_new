import { infraServices, gpuInfo } from '../data/mockData';

export default function Infrastructure() {
  return (
    <>
      <div className="page-header">
        <h2>Infrastructure</h2>
        <p>Docker services, GPU status & system health</p>
      </div>
      <div className="page-body">
        {/* GPU Card */}
        <div className="card animate-in" style={{ marginBottom: 20 }}>
          <div className="card-header">
            <span className="card-title">GPU Status</span>
            <span className="card-badge badge-green">{gpuInfo.pytorch ? 'PyTorch CUDA ✓' : 'CPU Only'}</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6,1fr)', gap: 16, marginTop: 8 }}>
            {[
              ['GPU', gpuInfo.name],
              ['VRAM', gpuInfo.vram],
              ['CUDA', gpuInfo.cudaVersion],
              ['Driver', gpuInfo.driver],
              ['Utilization', `${gpuInfo.utilization}%`],
              ['Temperature', `${gpuInfo.temperature}°C`],
            ].map(([l, v], i) => (
              <div key={i}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>{l}</div>
                <div className="mono" style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-bright)', marginTop: 4 }}>{v}</div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>GPU Utilization</span>
              <span className="mono" style={{ fontSize: 11 }}>{gpuInfo.utilization}%</span>
            </div>
            <div className="progress-bar" style={{ height: 8 }}>
              <div className="progress-fill" style={{ width: `${gpuInfo.utilization}%`, background: 'linear-gradient(90deg, var(--green), var(--gold-primary))' }} />
            </div>
          </div>
          <div style={{ marginTop: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Temperature</span>
              <span className="mono" style={{ fontSize: 11 }}>{gpuInfo.temperature}°C</span>
            </div>
            <div className="progress-bar" style={{ height: 8 }}>
              <div className="progress-fill" style={{ width: `${(gpuInfo.temperature / 100) * 100}%`, background: gpuInfo.temperature > 80 ? 'var(--red)' : gpuInfo.temperature > 60 ? 'var(--orange)' : 'var(--green)' }} />
            </div>
          </div>
        </div>

        {/* Docker Services */}
        <div className="card animate-in">
          <div className="card-header">
            <span className="card-title">Docker Services</span>
            <span className="card-badge badge-green">{infraServices.filter(s => s.status === 'online').length}/{infraServices.length} Online</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginTop: 8 }}>
            {infraServices.map((s, i) => (
              <div key={i} className="service-card animate-in">
                <div className="service-icon" style={{ background: s.bg, fontSize: 20 }}>{s.icon}</div>
                <div className="service-info">
                  <div className="service-name">{s.name}</div>
                  <div className="service-detail">:{s.port} • {s.detail}</div>
                  <div className="service-detail">Memory: {s.memory} • Uptime: {s.uptime}</div>
                </div>
                <div className="service-status" style={{ color: s.status === 'online' ? 'var(--green)' : 'var(--red)' }}>
                  <span className="status-dot" style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: s.status === 'online' ? 'var(--green)' : 'var(--red)', marginRight: 6, boxShadow: s.status === 'online' ? '0 0 6px var(--green)' : 'none' }} />
                  {s.status === 'online' ? 'Online' : 'Offline'}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Config Summary */}
        <div className="card animate-in" style={{ marginTop: 16 }}>
          <div className="card-header"><span className="card-title">Configuration</span><span className="card-badge badge-blue">base.yaml</span></div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 8 }}>
            {[
              ['Asset', 'XAU/USD (Gold)'],
              ['Mode', 'Paper Trading'],
              ['Broker', 'Interactive Brokers'],
              ['Order Type', 'Limit Only'],
              ['Algo', 'TWAP'],
              ['Max Slippage', '3.0 bps'],
              ['Data Source', 'Yahoo Finance (GC=F)'],
              ['Retrain Freq', 'Daily'],
            ].map(([k, v], i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{k}</span>
                <span className="mono" style={{ fontSize: 12, color: 'var(--text-bright)' }}>{v}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
